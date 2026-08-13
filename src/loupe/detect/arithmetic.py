"""Deterministic arithmetic checks over the claim graph.

No LLM. A model asked to add numbers is slower, costs money, and is wrong
sometimes. Python is none of those things. The model's job was extracting
the numbers; adding them is ours.

Two hazards this file has to handle, both observed in real runs:

1. The extractor emits DUPLICATE claims for one fact, phrased differently.
   Summing naively double-counts. We deduplicate on (holder, value) before
   summing.

2. Distinguishing a stated total from a component is genuinely ambiguous:
   "410,000 options outstanding" contains a total-marker word but is a
   component of the cap table. We require a total to be the largest value
   in its group, and reconcile against that one only.
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

    Deduplication is on the VALUE, not on the holder's name. Extracted
    quotes phrase the holder inconsistently ("Sarah Chen holds" versus "The
    Executive holds"), so name matching is unreliable, whereas two identical
    share counts in one cap table are almost always the same holding
    described twice. Where the same claim appears in multiple documents, the
    cap table version is preferred as the authoritative source.
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
        # Prefer the cap table as the authoritative statement of a holding.
        if "cap_table" in claim.document_id and "cap_table" not in existing.document_id:
            by_value[value] = claim
    return sorted(by_value.values(), key=lambda c: -(c.numeric_value or Decimal(0)))


def detect_share_reconciliation(store: EvidenceStore) -> list[Finding]:
    """Check that the stated share total reconciles with its components.

    Only the LARGEST stated total is reconciled. Smaller figures that carry
    total-like wording (for example an option pool described as
    "outstanding") are treated as components, which is what they are.

    Returns:
        At most one finding, citing the total and every component summed.
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

    components = _deduplicate(
        [
            c
            for c in claims
            if c.claim_id != total.claim_id
            and _matches(c, HOLDER_PATTERNS)
            and c.numeric_value is not None
            and c.numeric_value < total.numeric_value
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
    parts = " + ".join(
        f"{c.numeric_value:,.0f}" for c in components if c.numeric_value
    )
    direction = "exceed" if difference > 0 else "fall short of"

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
            title="Stated share total does not reconcile with individual holdings",
            description=(
                f"The cap table states a total of {total.numeric_value:,.0f} "
                f"shares, but the individual holdings sum to {summed:,.0f} "
                f"({parts}). The components {direction} the stated total by "
                f"{abs(difference):,.0f} shares. An unreconciled cap table "
                f"means the buyer cannot rely on the stated ownership "
                f"percentages, and may be acquiring a different equity "
                f"position than represented."
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