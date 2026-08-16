"""Deterministic temporal checks.

Catches dates that cannot be ordered as the documents imply: an event
predating the company's own incorporation, or an amendment dated before the
amendment it claims to modify.

Pure Python. Date comparison is not a judgement call, so it does not warrant
a model call.
"""

from __future__ import annotations

import re
from datetime import date

from loupe.models.claim import Claim
from loupe.models.document import Document
from loupe.models.finding import Finding, FindingType, Severity
from loupe.observability.logging import get_logger
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)

DETECTOR_NAME = "temporal_detector"

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

_DATE_PATTERN = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b|\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b"
)

# "Amendment No. 1", "Amendment No 2", "Amendment 1" all match.
_AMENDMENT_SELF = re.compile(r"Amendment\s+No\.?\s*(\d+)", re.IGNORECASE)

# A document saying it follows an earlier amendment. Deliberately loose about
# the words between, because the phrasing varies: "as previously amended by",
# "as amended by", "further amends ... as previously amended by".
_AMENDMENT_PRIOR = re.compile(
    r"amended\s+by\s+Amendment\s+No\.?\s*(\d+)", re.IGNORECASE
)

HEAD_CHARS = 1200


def extract_date(text: str) -> date | None:
    """Parse the first date found in free text.

    Handles "14 March 2024" and "March 14, 2024". Returns None rather than
    guessing when no unambiguous date is present.
    """
    match = _DATE_PATTERN.search(text)
    if not match:
        return None

    if match.group(1):
        day, month_name, year = match.group(1), match.group(2), match.group(3)
    else:
        month_name, day, year = match.group(4), match.group(5), match.group(6)

    month = _MONTHS.get(month_name.lower())
    if month is None:
        return None

    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def document_date(doc: Document) -> date | None:
    """The first date appearing in a document, taken as its execution date.

    Reads further into the document than the title alone, because the
    execution date usually sits in the first operative paragraph rather than
    the heading.
    """
    if not doc.is_readable:
        return None
    return extract_date(doc.text[:HEAD_CHARS])


def _dated_claims(store: EvidenceStore) -> list[tuple[Claim, date]]:
    """Claims whose text contains a parseable date."""
    out: list[tuple[Claim, date]] = []
    for claim in store.claims:
        parsed = extract_date(claim.raw_text)
        if parsed is not None:
            out.append((claim, parsed))
    return out


def detect_incorporation_ordering(store: EvidenceStore) -> list[Finding]:
    """Flag events dated before the company was incorporated.

    Nothing the company does can predate its own existence, so this is a
    hard impossibility rather than a heuristic.
    """
    dated = _dated_claims(store)

    incorporation: date | None = None
    incorporation_claim: Claim | None = None
    for claim, parsed in dated:
        if "incorporat" in f"{claim.predicate} {claim.raw_text}".lower():
            incorporation = parsed
            incorporation_claim = claim
            break

    if incorporation is None or incorporation_claim is None:
        return []

    findings: list[Finding] = []
    for index, (claim, parsed) in enumerate(dated):
        if claim.claim_id == incorporation_claim.claim_id:
            continue
        if parsed >= incorporation:
            continue

        findings.append(
            Finding(
                finding_id=f"temporal-inc-{index:03d}",
                finding_type=FindingType.TEMPORAL_IMPOSSIBILITY,
                severity=Severity.MEDIUM,
                title="Event dated before incorporation",
                description=(
                    f"An event dated {parsed.isoformat()} ({claim.predicate}) "
                    f"predates the company's incorporation on "
                    f"{incorporation.isoformat()}. Either a date is recorded "
                    f"incorrectly or the event relates to a predecessor "
                    f"entity."
                ),
                evidence=(claim.span, incorporation_claim.span),
                claim_ids=(claim.claim_id, incorporation_claim.claim_id),
                confidence=0.85,
                raised_by=DETECTOR_NAME,
            )
        )

    return findings


def _first_span(doc: Document, needle: str):
    """A span from the document containing the needle, or its first block."""
    for block in doc.blocks:
        if needle in block.text:
            return block.span
    return doc.blocks[0].span if doc.blocks else None


def detect_amendment_ordering(store: EvidenceStore) -> list[Finding]:
    """Flag an amendment dated before the amendment it claims to modify.

    An amendment cannot modify a document that did not yet exist. Detected
    by reading each document's own amendment number, the amendment it says
    it follows, and the execution dates of both.

    Operating on documents rather than claims is deliberate: the amendment
    number and the execution date sit in the opening paragraph, and whether
    the extractor happened to emit both as claims is not something this
    check should depend on.
    """
    numbered: dict[int, tuple[Document, date]] = {}
    references: list[tuple[Document, date, int]] = []

    for doc in store.documents:
        if not doc.is_readable:
            continue
        head = doc.text[:HEAD_CHARS]
        doc_date = document_date(doc)
        if doc_date is None:
            continue

        self_match = _AMENDMENT_SELF.search(head)
        if self_match:
            numbered[int(self_match.group(1))] = (doc, doc_date)

        prior_match = _AMENDMENT_PRIOR.search(head)
        if prior_match:
            references.append((doc, doc_date, int(prior_match.group(1))))

    log.debug(
        "amendment scan",
        numbered=sorted(numbered),
        references=[(d.document_id, n) for d, _, n in references],
    )

    findings: list[Finding] = []

    for index, (doc, doc_date, prior_number) in enumerate(references):
        prior = numbered.get(prior_number)
        if prior is None:
            continue
        prior_doc, prior_date = prior
        if prior_doc.document_id == doc.document_id:
            continue
        if doc_date >= prior_date:
            continue

        span = _first_span(doc, str(doc_date.year))
        prior_span = _first_span(prior_doc, str(prior_date.year))
        if span is None or prior_span is None:
            continue

        findings.append(
            Finding(
                finding_id=f"temporal-amend-{index:03d}",
                finding_type=FindingType.TEMPORAL_IMPOSSIBILITY,
                severity=Severity.HIGH,
                title="Amendment dated before the amendment it modifies",
                description=(
                    f"{doc.filename} is dated {doc_date.isoformat()} and "
                    f"states that it amends the agreement as previously "
                    f"amended by Amendment No. {prior_number}, which is "
                    f"dated {prior_date.isoformat()}. An amendment cannot "
                    f"modify a document that did not yet exist. Either a "
                    f"date is wrong or the amendments were executed out of "
                    f"sequence, which leaves the operative terms of the "
                    f"agreement in doubt."
                ),
                evidence=(span, prior_span),
                confidence=0.9,
                raised_by=DETECTOR_NAME,
            )
        )

    return findings


def detect(store: EvidenceStore) -> list[Finding]:
    """Run every temporal check."""
    findings = [
        *detect_incorporation_ordering(store),
        *detect_amendment_ordering(store),
    ]
    log.info("temporal detection complete", findings=len(findings))
    return findings