"""Deterministic arithmetic checks over the claim graph.

No LLM. A model asked to add numbers is slower, costs money, and is wrong
sometimes. Python is none of those things. The model's job was extracting
the numbers; adding them is ours.

Three hazards this file handles, all observed in real runs:

1. The extractor emits DUPLICATE claims for one fact. The same founder
   holding appears in both the cap table and their employment agreement.
   Summing naively double-counts, so claims are deduplicated by value.

2. Total versus component is ambiguous. "410,000 options outstanding"
   contains a total-marker word but is a component. Only the LARGEST stated
   total is reconciled against.

3. Defined terms matter. "Issued and outstanding" EXCLUDES unexercised
   options; "fully diluted" includes them. Adding options to an issued count
   conflates two different figures and produces a finding that is wrong on
   definition rather than arithmetic. Options are therefore excluded.
"""

from __future__ import annotations

import re
from decimal import Decimal

from loupe.models.claim import Claim, ClaimType
from loupe.models.finding import Finding, FindingType, Severity
from loupe.models.span import Span
from loupe.observability.logging import get_logger
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)

DETECTOR_NAME = "arithmetic_detector"

TOTAL_PATTERNS = (
    r"\btotal\s+(issued|outstanding|shares)",
    r"\btotal\s+of\b",
    r"\baggregate\b",
)
HOLDER_PATTERNS = (
    r"\bholds\b",
    r"\bgranted\s+to\b",
    r"\bhave\s+been\s+granted\b",
    r"\bissued\s+to\b",
    r"\ballocated\s+to\b",
)
EXCLUDE_PATTERNS = (
    r"\bauthoris?zed\b",
    r"\breserved\b",
    r"\bmaximum\b",
    r"\bper\s+share\b",
)

TOLERANCE = Decimal("0.01")
_SHARE_WORD = re.compile(r"\b(share|option|unit|stock)", re.IGNORECASE)
_OPTION_WORD = re.compile(r"\b(option|warrant|rsu)", re.IGNORECASE)


def _matches(claim: Claim, patterns: tuple[str, ...]) -> bool:
    text = f"{claim.predicate} {claim.raw_text}".lower()
    return any(re.search(p, text) for p in patterns)


def _is_excluded(claim: Claim) -> bool:
    """Authorised capital is a ceiling, not a holding. Never sum it."""
    return _matches(claim, EXCLUDE_PATTERNS)


def _share_claims(store: EvidenceStore) -> list[Claim]:
    """Quantity claims concerning shares, options, or equity units."""
    return [
        c
        for c in store.claims
        if c.claim_type is ClaimType.QUANTITY
        and c.numeric_value is not None
        and _SHARE_WORD.search(f"{c.predicate} {c.raw_text}")
        and not _is_excluded(c)
    ]


def _deduplicate(claims: list[Claim]) -> list[Claim]:
    """Keep one claim per distinct share quantity.

    The same holding is frequently stated in several documents -- a founder's
    shareholding appears in both the cap table and their employment
    agreement. Summing both double-counts it and manufactures a phantom
    discrepancy.

    Deduplication is on the VALUE, not the holder's name. Extracted quotes
    phrase the holder inconsistently ("Sarah Chen holds" versus "The
    Executive holds"), so name matching is unreliable, whereas two identical
    share counts in one cap table are almost always the same holding
    described twice. Where a value appears in several documents, the cap
    table version is preferred as authoritative.
    """
    by_value: dict[Decimal, Claim] = {}
    for claim in claims:
        value = claim.numeric_value
        if value is None:
            continue
        existing = by_value.get(value)
        if existing is None:
            by_value[value] = claim
            continue
        if "cap_table" in claim.document_id and "cap_table" not in existing.document_id:
            by_value[value] = claim
    return sorted(by_value.values(), key=lambda c: -(c.numeric_value or Decimal(0)))


def detect_share_reconciliation(store: EvidenceStore) -> list[Finding]:
    """Check that the stated share total reconciles with identified holdings.

    Only the LARGEST stated total is reconciled. Unexercised options are
    excluded, since "issued and outstanding" is a defined term that does not
    include them.

    Returns:
        At most one finding, citing the total and every holding summed.
    """
    claims = _share_claims(store)
    if not claims:
        return []

    totals = [c for c in claims if _matches(c, TOTAL_PATTERNS)]
    if not totals:
        log.debug("no stated total found; skipping reconciliation")
        return []

    total = max(totals, key=lambda c: c.numeric_value or Decimal(0))
    assert total.numeric_value is not None

    # "Issued and outstanding" excludes unexercised options and warrants.
    # Including them conflates the issued count with the fully diluted count,
    # which is a definitional error rather than a discrepancy.
    components = _deduplicate(
        [
            c
            for c in claims
            if c.claim_id != total.claim_id
            and _matches(c, HOLDER_PATTERNS)
            and c.numeric_value is not None
            and c.numeric_value < total.numeric_value
            and not _OPTION_WORD.search(f"{c.predicate} {c.raw_text}")
        ]
    )

    if len(components) < 2:
        log.debug("too few components to reconcile", count=len(components))
        return []

    summed = sum(
        (c.numeric_value for c in components if c.numeric_value is not None),
        start=Decimal(0),
    )
    difference = summed - total.numeric_value
    if abs(difference) <= TOLERANCE:
        log.info("share total reconciles", total=str(total.numeric_value))
        return []

    evidence: tuple[Span, ...] = (total.span, *(c.span for c in components))
    parts = " + ".join(f"{c.numeric_value:,.0f}" for c in components if c.numeric_value)
    direction = "exceed" if difference > 0 else "are unaccounted for against"

    log.info(
        "share reconciliation mismatch",
        stated=str(total.numeric_value),
        summed=str(summed),
        difference=str(difference),
        components=len(components),
    )

    return [
        Finding(
            finding_id="arith-shares-001",
            finding_type=FindingType.ARITHMETIC,
            severity=Severity.HIGH,
            title="Stated share total does not reconcile with identified holdings",
            description=(
                f"The cap table states {total.numeric_value:,.0f} shares "
                f"issued and outstanding, but identified holdings account for "
                f"only {summed:,.0f} ({parts}). {abs(difference):,.0f} shares "
                f"{direction} the identified holdings. Either a holder is "
                f"undisclosed or the stated total is wrong; in either case the "
                f"buyer cannot rely on the stated ownership percentages. "
                f"Unexercised options are excluded from this reconciliation, "
                f"as they are not issued shares."
            ),
            evidence=evidence,
            claim_ids=(total.claim_id, *(c.claim_id for c in components)),
            confidence=0.9,
            raised_by=DETECTOR_NAME,
        )
    ]


def detect(store: EvidenceStore) -> list[Finding]:
    """Run every arithmetic check."""
    return detect_share_reconciliation(store)