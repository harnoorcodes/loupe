"""Gap auditing: reporting what the data room does not contain.

Most of this is deterministic keyword matching, which is deliberate. Whether
a document is present is a matter of fact, not judgement, so it needs no
model.

The critical distinction this file makes is between a document being PRESENT
and a document being MENTIONED. The cap table says options were granted
"under the company equity incentive plan" -- but no plan document exists in
the corpus. Searching body text for keywords would treat that mention as
proof of presence and hide the exact defect the audit is looking for.

Presence is therefore matched against FILENAMES only. Body text is used for
a different purpose: deciding whether an item applies to this deal at all.
An equity incentive plan is only required because the corpus shows options
were granted. That conditional logic is what makes the finding meaningful
rather than a generic checklist entry.
"""

from __future__ import annotations

from loupe.corpus.request_list import REQUEST_LIST, RequestItem
from loupe.models.document import Document
from loupe.models.finding import Finding, FindingType, Severity
from loupe.observability.logging import get_logger
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)

DETECTOR_NAME = "gap_auditor"


def _normalise(text: str) -> str:
    """Lowercase and treat separators as spaces.

    Filenames use separators that keyword phrases do not: the keyword
    "cap table" must match the filename "cap_table.pdf".
    """
    lowered = text.lower()
    for char in ("_", "-", ".", "/"):
        lowered = lowered.replace(char, " ")
    return lowered


def _presence_haystack(documents: tuple[Document, ...]) -> str:
    """Filenames and document types only.

    Deliberately EXCLUDES body text. A document is present when it exists as
    a file, not when another document happens to refer to it.
    """
    parts: list[str] = []
    for doc in documents:
        parts.append(_normalise(doc.filename))
        parts.append(_normalise(doc.document_type.value))
    return "\n".join(parts)


def _content_haystack(documents: tuple[Document, ...]) -> str:
    """Full body text, used only to decide whether an item APPLIES."""
    return "\n".join(_normalise(doc.text) for doc in documents if doc.is_readable)


def is_satisfied(item: RequestItem, presence_haystack: str) -> bool:
    """True if a document answering this request is present in the corpus.

    Matched against filenames and document types only.
    """
    return any(_normalise(keyword) in presence_haystack for keyword in item.keywords)


def is_required(item: RequestItem, content_haystack: str) -> bool:
    """True if this item applies to this particular deal.

    Unconditional items always apply. Conditional items apply only when
    their trigger appears in the corpus text, so the report is not padded
    with documents that were never relevant to this transaction.
    """
    if not item.conditional_on:
        return True
    return any(
        _normalise(trigger) in content_haystack for trigger in item.conditional_on
    )


def find_trigger_evidence(
    item: RequestItem, store: EvidenceStore
) -> tuple[str, str] | None:
    """Locate the claim that makes a conditional item required.

    Returns:
        (claim_id, quoted text) of the triggering claim, or None.
    """
    if not item.conditional_on:
        return None
    for claim in store.claims:
        text = _normalise(f"{claim.predicate} {claim.raw_text}")
        if any(_normalise(trigger) in text for trigger in item.conditional_on):
            return claim.claim_id, claim.raw_text
    return None


def detect(store: EvidenceStore) -> list[Finding]:
    """Report every expected document that is absent from the corpus.

    Also reports documents that were provided but could not be parsed, so
    that a parse failure becomes a visible output rather than a silent
    blind spot.
    """
    documents = store.documents
    presence = _presence_haystack(documents)
    content = _content_haystack(documents)
    findings: list[Finding] = []

    for item in REQUEST_LIST:
        if not is_required(item, content):
            log.debug("request not applicable to this deal", item=item.item_id)
            continue
        if is_satisfied(item, presence):
            continue

        trigger = find_trigger_evidence(item, store)
        if trigger is not None:
            claim_id, quote = trigger
            description = (
                f"No document satisfying this request was found in the data "
                f"room. This document is required because the corpus states: "
                f'"{quote[:200]}". {item.rationale}'
            )
            claim_ids: tuple[str, ...] = (claim_id,)
        else:
            description = (
                f"No document satisfying this request was found in the data "
                f"room. {item.rationale}"
            )
            claim_ids = ()

        findings.append(
            Finding(
                finding_id=f"gap-{item.item_id}",
                finding_type=FindingType.MISSING_DOCUMENT,
                severity=item.severity,
                title=f"Missing: {item.title}",
                description=description,
                evidence=(),
                claim_ids=claim_ids,
                confidence=0.95,
                raised_by=DETECTOR_NAME,
            )
        )

    for doc in documents:
        if doc.is_readable:
            continue
        findings.append(
            Finding(
                finding_id=f"unreadable-{doc.document_id}",
                finding_type=FindingType.UNREADABLE_DOCUMENT,
                severity=Severity.MEDIUM,
                title=f"Unreadable document: {doc.filename}",
                description=(
                    f"This document was provided but could not be processed "
                    f"({doc.parse_status.value}: {doc.parse_error}). Its "
                    f"contents have not been reviewed and it should be "
                    f"requested again in a readable format."
                ),
                evidence=(),
                confidence=1.0,
                raised_by=DETECTOR_NAME,
            )
        )

    log.info("gap audit complete", requested=len(REQUEST_LIST), gaps=len(findings))
    return findings