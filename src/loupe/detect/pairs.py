"""Candidate pair generation for targeted contradiction detection.

Entity-grouped detection asks a model to find conflicting pairs inside a bag
of claims about one company. That works when the group is small and the two
halves happen to sit near each other, and fails when the group is large or
the two halves belong to different entities -- which is the case for most
real contradictions. A total lives under the company; its components live
under individual people or customers.

This module inverts the approach. Python finds pairs that are SUSPICIOUS by
construction, using rules that need no judgement:

    numeric mismatch      the same measure stated with different values
    total vs components   a stated total that does not equal the sum
    shared address        one address appearing in two documents
    trigger and magnitude a right or condition beside a large amount

Only those pairs reach the model, and they arrive as a pair rather than
buried in a list of thirty claims. Two consequences: recall improves because
the model is asked a narrow question, and cost falls because most claims are
never sent at all.

Generation is deterministic and free, so candidates can be inspected before
any model call is made.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, NamedTuple

from loupe.models.claim import Claim, ClaimType
from loupe.observability.logging import get_logger
from loupe.store.entities import normalise_entity
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)


class CandidatePair(NamedTuple):
    """Two claims a deterministic rule considers worth comparing.

    Attributes:
        claim_a: First claim.
        claim_b: Second claim.
        strategy: Which generator produced the pair, for reporting.
        reason: Why the rule fired, shown to the model as context.
    """

    claim_a: Claim
    claim_b: Claim
    strategy: str
    reason: str

    @property
    def key(self) -> tuple[str, str]:
        """Order-independent identity, for deduplication."""
        return tuple(sorted((self.claim_a.claim_id, self.claim_b.claim_id)))  # type: ignore[return-value]


# --------------------------------------------------------------- vocabulary

# Measures specific enough that two claims sharing one are describing the
# same fact, whoever they are filed under. A board minute approving a salary
# and an employment agreement stating one are about the same salary even
# though their subjects differ.
SPECIFIC_MEASURES = (
    "base salary",
    "annual salary",
    "deferred revenue",
    "total revenue",
    "subscription fee",
    "annual fee",
    "aggregate limit",
    "outstanding shares",
    "issued and outstanding",
    "loan principal",
    "principal amount",
)

# Measures too generic to pair on alone. Two claims sharing only one of
# these must also concern the same entity, otherwise every shareholding gets
# compared against every other shareholding.
GENERIC_MEASURES = (
    "revenue",
    "salary",
    "shares",
    "options",
    "cash",
    "principal",
    "receivable",
    "fee",
    "coverage",
)

MEASURE_TERMS = SPECIFIC_MEASURES + GENERIC_MEASURES

# Matches a year even inside a token such as "FY2024", where a word
# boundary would not fire.
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")

# Domains where a stated total should reconcile against its components.
# Order matters: a claim mentioning "options" also mentions "shares" when it
# reads "options over 120,000 shares", so the narrower domain is tested
# first and a claim is assigned to exactly one domain.
TOTAL_DOMAINS = {
    "options": ("options", "warrants"),
    "deferred": ("deferred revenue",),
    "receivables": ("receivable", "overdue"),
    "revenue": ("revenue",),
    "shares": ("shares", "common stock", "preferred stock"),
}

# A claim expressing a proportion is never a component of a total.
PROPORTION_MARKERS = ("%", "percent", "share of", "proportion")

TOTAL_MARKERS = ("total", "aggregate", "outstanding", "in aggregate")

# Claims describing a right, trigger or obligation whose exercise could hurt.
TRIGGER_TERMS = (
    "change of control",
    "terminate",
    "termination",
    "accelerat",
    "immediately due",
    "exclusive",
    "liquidated damages",
    "without penalty",
    "consent",
)

# Triggers severe enough to be worth pairing even when filed under the
# company itself. A routine notice period is not one of these.
SEVERE_TRIGGERS = (
    "change of control",
    "accelerat",
    "immediately due",
    "liquidated damages",
    "exclusive",
    "without penalty",
)

# Words that make a magnitude claim worth pairing with a trigger.
MAGNITUDE_TERMS = (
    "revenue",
    "cash",
    "principal",
    "outstanding",
    "% of total",
    "percent",
    "concentration",
)

_ADDRESS = re.compile(
    r"\b\d{1,5}\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+"
    r"(?:Street|St|Drive|Dr|Avenue|Ave|Road|Rd|Way|Lane|Ln|Plaza|Boulevard|Blvd)\b"
)

# Claims that describe a ceiling or an authorisation rather than a fact
# about what exists. Authorised capital is not comparable to issued capital.
CEILING_TERMS = ("authoris", "authoriz", "reserved", "maximum", "not exceeding",
                "up to", "aggregate limit")

NUMERIC_TYPES = (ClaimType.MONETARY, ClaimType.QUANTITY)

# A ratio bound keeps comparisons sensible: 240k against 260k is the same
# measure stated twice, 240k against 8.4M is two different facts.
MIN_RATIO = Decimal("0.4")
MAX_RATIO = Decimal("2.5")
EXACT_TOLERANCE = Decimal("0.01")

# A component smaller than this is almost always a stray number picked up
# by extraction, such as a section reference, not a real holding.
MIN_COMPONENT = Decimal("1000")

MAX_PAIRS_PER_STRATEGY = 25


def _text(claim: Claim) -> str:
    """Lowercased predicate and quote, for keyword matching."""
    return f"{claim.predicate} {claim.raw_text}".lower()


def _shared_measure(a: Claim, b: Claim) -> str | None:
    """The most specific measure term both claims mention, if any.

    Longer terms are checked first so that "deferred revenue" wins over
    "revenue", which keeps unrelated revenue figures from being paired.
    """
    text_a, text_b = _text(a), _text(b)
    for term in sorted(MEASURE_TERMS, key=len, reverse=True):
        if term in text_a and term in text_b:
            return term
    return None


def _years(claim: Claim) -> set[str]:
    """Four-digit years appearing in a claim's quoted text."""
    return {m.group(0) for m in _YEAR.finditer(claim.raw_text)}


def _different_periods(a: Claim, b: Claim) -> bool:
    """True if the two claims explicitly concern different years.

    Revenue for 2025 and revenue for 2024 are both correct and are not a
    contradiction. Without this guard every prior-period comparative in the
    accounts pairs against the current one.
    """
    years_a, years_b = _years(a), _years(b)
    if not years_a or not years_b:
        return False
    return years_a.isdisjoint(years_b)


def _is_ceiling(claim: Claim) -> bool:
    """True if the claim states a limit rather than an actual amount."""
    return any(t in _text(claim) for t in CEILING_TERMS)


def _numeric(store: EvidenceStore) -> list[Claim]:
    """Claims carrying a usable number that describes an actual amount."""
    return [
        c
        for c in store.claims
        if c.claim_type in NUMERIC_TYPES
        and c.numeric_value is not None
        and not _is_ceiling(c)
    ]


def company_entity(store: EvidenceStore) -> str:
    """The entity the corpus is about, taken as the most-claimed subject.

    Needed because rules that pair on a shared subject would otherwise match
    every claim against every other claim: almost everything in a data room
    is about the target company.
    """
    subjects = store.subjects()
    return subjects[0] if subjects else ""


# ----------------------------------------------------------- generator 1

def numeric_mismatch_pairs(store: EvidenceStore) -> list[CandidatePair]:
    """Pair claims that measure the same thing with different values.

    Catches a figure reported one way in one document and another way in
    another: a salary approved at one amount and contracted at another, or
    deferred revenue stated twice.

    Requires a shared measure term, different source documents, different
    values, and values within a ratio bound so that unrelated magnitudes are
    not compared.
    """
    claims = _numeric(store)
    company = company_entity(store)
    pairs: list[CandidatePair] = []
    seen: set[tuple[str, str]] = set()

    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            if a.document_id == b.document_id:
                continue
            assert a.numeric_value is not None and b.numeric_value is not None
            if abs(a.numeric_value - b.numeric_value) <= EXACT_TOLERANCE:
                continue
            if a.numeric_value == 0 or b.numeric_value == 0:
                continue

            ratio = a.numeric_value / b.numeric_value
            if not (MIN_RATIO <= ratio <= MAX_RATIO):
                continue

            measure = _shared_measure(a, b)
            if measure is None:
                continue

            # Two claims must plausibly describe the same fact.
            #
            # Same subject always qualifies. Different subjects qualify only
            # when the measure is specific AND one side is the company: a
            # board minute approving a salary is filed under the company
            # while the employment agreement is filed under the person, and
            # "base salary" is precise enough that both describe one figure.
            #
            # A generic measure across different subjects never qualifies.
            # Otherwise every customer's revenue is compared against the
            # company's deferred revenue, and against every other customer's.
            subject_a = normalise_entity(a.subject)
            subject_b = normalise_entity(b.subject)
            if subject_a != subject_b:
                if measure not in SPECIFIC_MEASURES:
                    continue
                if company not in (subject_a, subject_b):
                    continue

            if _different_periods(a, b):
                continue

            pair = CandidatePair(
                a,
                b,
                "numeric_mismatch",
                f"Both claims state a value for {measure!r}, but the values "
                f"differ: {a.numeric_value:,} against {b.numeric_value:,}.",
            )
            if pair.key in seen:
                continue
            seen.add(pair.key)
            pairs.append(pair)

    return pairs[:MAX_PAIRS_PER_STRATEGY]


# ----------------------------------------------------------- generator 2

# Terms that disqualify a claim from being a component of a given total.
# Deferred revenue is money NOT yet recognised, so it is not a part of
# recognised revenue. Options are not issued shares.
EXCLUDED_TERMS_BY_DOMAIN: dict[str, tuple[str, ...]] = {
    "revenue": ("deferred", "not yet recognised", "invoiced but"),
    "shares": ("option", "warrant", "granted"),
    "options": (),
    "receivables": (),
    "deferred": ("total revenue", "recognised"),
}

# Which document types can supply components for a total, by domain.
DOMAIN_DOCUMENT_TYPES: dict[str, tuple[str, ...]] = {
    "shares": ("cap_table", "employment_agreement", "board_minutes"),
    "options": ("cap_table", "employment_agreement"),
    "revenue": ("financial_statement",),
    "receivables": ("financial_statement",),
    "deferred": ("financial_statement",),
}
# Documents whose figures belong to a different reporting period than the
# annual statements, and which therefore cannot supply components for an
# annual total even though their type matches. The period guard cannot catch
# these, because the individual claims do not state a year.
OFF_PERIOD_MARKERS = ("management_accounts", "_q1_", "_q2_", "_q3_", "_q4_")


def _same_document_kind(
    component: Claim, domain: str, documents: dict[str, Any]
) -> bool:
    """True if the component comes from a document that can hold such a part.

    A revenue total is reconciled against revenue schedules, not against a
    management accounts pack for a later quarter that happens to mention
    revenue. Without this, unrelated figures enter the sum and the resulting
    arithmetic is wrong, which the adjudicator then rejects.

    Falls back to the filename heuristic when the stored type is OTHER or
    UNKNOWN. Classification is an LLM step that not every entry point runs,
    and a document whose type was never set must not be silently excluded --
    that turned a working reconciliation into no finding at all.
    """
    from loupe.ingestion.loader import classify
    from loupe.models.document import DocumentType

    doc = documents.get(component.document_id)
    if doc is None:
        return True

    allowed = DOMAIN_DOCUMENT_TYPES.get(domain, ())
    if not allowed:
        return True

    doc_type = doc.document_type
    if doc_type in (DocumentType.OTHER, DocumentType.UNKNOWN):
        doc_type = classify(doc.filename)

    return doc_type.value in allowed


def total_component_pairs(store: EvidenceStore) -> list[CandidatePair]:
    """Pair a stated total with its components when they do not reconcile.

    A total and its parts are usually filed under different entities -- the
    company states the total, individual people or customers hold the parts
    -- so entity grouping never brings them together. This rule does.

    Domain membership is not enough on its own. A first version summed
    deferred revenue lines and next-quarter management figures into a FY2025
    revenue total, producing arithmetic that was simply wrong, which the
    adjudicator then correctly rejected. Components must therefore come from
    a document whose TYPE matches the total's, so that a revenue total is
    reconciled against a revenue schedule rather than against every number
    in the corpus that mentions revenue.
    """
    claims = _numeric(store)
    documents = {d.document_id: d for d in store.documents}
    pairs: list[CandidatePair] = []

    claimed: set[str] = set()

    for domain, terms in TOTAL_DOMAINS.items():
        in_domain = [
            c
            for c in claims
            if c.claim_id not in claimed
            and any(t in _text(c) for t in terms)
            and not any(p in _text(c) for p in PROPORTION_MARKERS)
        ]
        if len(in_domain) < 3:
            continue
        claimed.update(c.claim_id for c in in_domain)

        totals = [c for c in in_domain if any(m in _text(c) for m in TOTAL_MARKERS)]
        if not totals:
            continue

        total = max(totals, key=lambda c: c.numeric_value or Decimal(0))
        assert total.numeric_value is not None

        excluded = EXCLUDED_TERMS_BY_DOMAIN.get(domain, ())

        components = [
            c
            for c in in_domain
            if c.claim_id != total.claim_id
            and c.document_id != total.document_id
            and c.numeric_value is not None
            and c.numeric_value < total.numeric_value
            and c.numeric_value >= MIN_COMPONENT
            and not any(m in _text(c) for m in TOTAL_MARKERS)
            and not any(x in _text(c) for x in excluded)
            and not _different_periods(c, total)
            and not any(m in c.document_id for m in OFF_PERIOD_MARKERS)
            and _same_document_kind(c, domain, documents)
        ]

        # Deduplicate by value: the same holding often appears in several
        # documents, and summing both copies invents a discrepancy.
        by_value: dict[Decimal, Claim] = {}
        for c in components:
            assert c.numeric_value is not None
            by_value.setdefault(c.numeric_value, c)
        unique = sorted(
            by_value.values(), key=lambda c: -(c.numeric_value or Decimal(0))
        )

        if len(unique) < 2:
            continue

        summed = sum(
            (c.numeric_value for c in unique if c.numeric_value is not None),
            start=Decimal(0),
        )
        if abs(summed - total.numeric_value) <= EXACT_TOLERANCE:
            continue

        parts = " + ".join(f"{c.numeric_value:,}" for c in unique)
        reason = (
            f"A stated {domain} total of {total.numeric_value:,} does not "
            f"equal the sum of the individual amounts found "
            f"({parts} = {summed:,}), a difference of "
            f"{abs(summed - total.numeric_value):,}. Check whether the "
            f"components listed are genuinely parts of that total before "
            f"treating the difference as a discrepancy."
        )

        for component in unique[:2]:
            pairs.append(
                CandidatePair(total, component, "total_vs_components", reason)
            )

    return pairs[:MAX_PAIRS_PER_STRATEGY]


# ----------------------------------------------------------- generator 3

def shared_address_pairs(store: EvidenceStore) -> list[CandidatePair]:
    """Pair claims that quote the same street address in different documents.

    A supplier registered at a founder's home address is a related party
    transaction. Neither claim is remarkable alone, and they belong to
    different entities, so only a literal string match brings them together.
    """
    by_address: dict[str, list[Claim]] = {}

    for claim in store.claims:
        for match in _ADDRESS.finditer(claim.raw_text):
            by_address.setdefault(match.group(0).lower(), []).append(claim)

    pairs: list[CandidatePair] = []
    seen: set[tuple[str, str]] = set()

    for address, claims in by_address.items():
        documents = {c.document_id for c in claims}
        if len(documents) < 2:
            continue

        for i, a in enumerate(claims):
            for b in claims[i + 1 :]:
                if a.document_id == b.document_id:
                    continue
                if normalise_entity(a.subject) == normalise_entity(b.subject):
                    continue

                pair = CandidatePair(
                    a,
                    b,
                    "shared_address",
                    f"The address {address!r} appears in both documents, for "
                    f"two different parties: {a.subject} and {b.subject}.",
                )
                if pair.key in seen:
                    continue
                seen.add(pair.key)
                pairs.append(pair)

    return pairs[:MAX_PAIRS_PER_STRATEGY]


# ----------------------------------------------------------- generator 4

def trigger_magnitude_pairs(store: EvidenceStore) -> list[CandidatePair]:
    """Pair a right or trigger with a magnitude that makes it dangerous.

    A termination right is unremarkable. A termination right held by a
    customer worth 43% of revenue is a deal issue. The two facts sit in
    different documents and often under different entities.
    """
    company = company_entity(store)
    triggers = [c for c in store.claims if any(t in _text(c) for t in TRIGGER_TERMS)]
    magnitudes = [
        c
        for c in store.claims
        if any(m in _text(c) for m in MAGNITUDE_TERMS)
        and (c.numeric_value is not None or "%" in c.raw_text)
    ]

    pairs: list[CandidatePair] = []
    seen: set[tuple[str, str]] = set()

    for trigger in triggers:
        trigger_subject = normalise_entity(trigger.subject)

        # Almost every obligation in a data room is filed under the company,
        # so a company-subject trigger would otherwise pair with every
        # financial figure in the corpus. Allow it only when the trigger is
        # one whose exercise is genuinely dangerous.
        if trigger_subject == company and not any(
            t in _text(trigger) for t in SEVERE_TRIGGERS
        ):
            continue

        for magnitude in magnitudes:
            if trigger.document_id == magnitude.document_id:
                continue

            same_party = trigger_subject == normalise_entity(magnitude.subject)
            mentioned = (
                trigger_subject
                and trigger_subject.split()[0] in magnitude.raw_text.lower()
            )
            if not (same_party or mentioned):
                continue

            pair = CandidatePair(
                trigger,
                magnitude,
                "trigger_and_magnitude",
                "One claim describes a right, trigger or obligation. The "
                "other states an amount or share concerning the same party. "
                "Consider whether exercising the first would be material "
                "given the second.",
            )
            if pair.key in seen:
                continue
            seen.add(pair.key)
            pairs.append(pair)

    return pairs[:MAX_PAIRS_PER_STRATEGY]


# ------------------------------------------------------------------ public

GENERATORS = (
    ("numeric_mismatch", numeric_mismatch_pairs),
    ("total_vs_components", total_component_pairs),
    ("shared_address", shared_address_pairs),
    ("trigger_and_magnitude", trigger_magnitude_pairs),
)


def generate(store: EvidenceStore) -> list[CandidatePair]:
    """Run every generator and return deduplicated candidate pairs.

    Deterministic and free. Inspect the result with the `pairs` command
    before spending anything on adjudication.
    """
    pairs: list[CandidatePair] = []
    seen: set[tuple[str, str]] = set()

    for name, generator in GENERATORS:
        produced = generator(store)
        kept = 0
        for pair in produced:
            if pair.key in seen:
                continue
            seen.add(pair.key)
            pairs.append(pair)
            kept += 1
        log.info("candidate pairs generated", strategy=name, pairs=kept)

    log.info("candidate generation complete", total=len(pairs))
    return pairs


def summarise(pairs: list[CandidatePair]) -> dict[str, int]:
    """Count pairs per strategy."""
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair.strategy] = counts.get(pair.strategy, 0) + 1
    return counts