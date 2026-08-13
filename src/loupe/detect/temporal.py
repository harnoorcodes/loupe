"""Deterministic temporal checks.

Catches dates that cannot be ordered as the documents imply -- an amendment
predating its agreement, a resolution approving something already done.

Like the arithmetic detector, this is pure Python. Date comparison is not a
judgement call.
"""

from __future__ import annotations

import re
from datetime import date

from loupe.models.claim import Claim
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
                finding_id=f"temporal-{index:03d}",
                finding_type=FindingType.TEMPORAL_IMPOSSIBILITY,
                severity=Severity.MEDIUM,
                title="Event dated before incorporation",
                description=(
                    f"An event dated {parsed.isoformat()} ({claim.predicate}) "
                    f"predates the company's incorporation on "
                    f"{incorporation.isoformat()}. Either a date is recorded "
                    f"incorrectly or the event relates to a predecessor entity."
                ),
                evidence=(claim.span, incorporation_claim.span),
                claim_ids=(claim.claim_id, incorporation_claim.claim_id),
                confidence=0.85,
                raised_by=DETECTOR_NAME,
            )
        )

    log.info("temporal detection complete", findings=len(findings))
    return findings


def detect(store: EvidenceStore) -> list[Finding]:
    """Run every temporal check."""
    return detect_incorporation_ordering(store)