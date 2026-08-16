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
import re
from typing import NamedTuple

from loupe.models.span import Span

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

# ---------------------------------------------------------------- references

# Phrases that introduce a named document the corpus asserts exists. Each
# pattern captures the document description and, where present, its date.
#
# The date matters more than it looks. A document referred to generically --
# "as set out in the shareholders agreement" -- may be a loose cross-reference
# to something the drafter never intended to attach. A document referred to
# with a specific execution date is being asserted as a discrete instrument
# that was signed on a particular day, and its absence is a real gap.
_REFERENCE_PATTERNS = (
    re.compile(
        r"(?:approved|authorised|authorized|adopted|executed|ratified)\s+by\s+"
        r"(written consent(?:\s+of\s+the\s+Board(?:\s+of\s+Directors)?)?)\s+"
        r"dated\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:pursuant\s+to|under|set\s+out\s+in|governed\s+by)\s+the\s+"
        r"([A-Z][A-Za-z ]{4,60}?(?:Agreement|Plan|Policy|Deed|Consent|Resolution))"
        r"\s+dated\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(Amendment\s+No\.?\s*\d+)\s+dated\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        re.IGNORECASE,
    ),
)

# A referenced document is considered present if enough of its distinctive
# words appear in some filename or document type in the corpus.
_STOPWORDS = frozenset(
    {"the", "of", "a", "an", "and", "or", "by", "to", "in", "for", "no", "dated"}
)
MIN_TOKEN_OVERLAP = 0.6


class DocumentReference(NamedTuple):
    """A document that the corpus asserts exists.

    Attributes:
        description: How the referencing document names it.
        date_text: The execution date as written, which makes the reference
            specific rather than generic.
        source_document: Which document made the assertion.
        quote: The sentence containing the reference, for citation.
        span: Where that sentence sits in the source.
    """

    description: str
    date_text: str
    source_document: str
    quote: str
    span: Span


def _tokens(text: str) -> set[str]:
    """Distinctive lowercase words, for loose filename matching."""
    words = re.findall(r"[a-z]+", _normalise(text))
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def find_references(documents: tuple[Document, ...]) -> list[DocumentReference]:
    """Find documents that the corpus asserts exist, by name and date.

    Operates on block text rather than extracted claims, because a reference
    is a property of how a sentence is phrased and does not depend on whether
    the extractor happened to emit it as a claim.
    """
    references: list[DocumentReference] = []

    for doc in documents:
        if not doc.is_readable:
            continue
        for block in doc.blocks:
            for pattern in _REFERENCE_PATTERNS:
                for match in pattern.finditer(block.text):
                    description = match.group(1).strip()
                    date_text = match.group(2).strip()
                    references.append(
                        DocumentReference(
                            description=description,
                            date_text=date_text,
                            source_document=doc.document_id,
                            quote=match.group(0).strip(),
                            span=block.span,
                        )
                    )

    return references


def reference_is_satisfied(
    reference: DocumentReference, documents: tuple[Document, ...]
) -> bool:
    """True if some document in the corpus plausibly is the one referenced.

    Matching is on token overlap against filenames and document types rather
    than exact strings, because a corpus names a file `board_minutes_2024_09`
    for something a contract calls "written consent of the Board of
    Directors". Requiring an exact match would report every reference as
    missing; requiring none would report none.
    """
    wanted = _tokens(reference.description)
    if not wanted:
        return True

    for doc in documents:
        available = _tokens(doc.filename) | _tokens(doc.document_type.value)
        if not available:
            continue
        overlap = len(wanted & available) / len(wanted)
        if overlap >= MIN_TOKEN_OVERLAP:
            return True

    return False


def detect_missing_references(store: EvidenceStore) -> list[Finding]:
    """Report documents the corpus asserts exist but does not contain.

    This is negative space the request list cannot anticipate. A checklist
    knows to ask for a shareholders agreement; it cannot know that this
    particular company's CFO employment agreement cites a board consent of a
    specific date, and that no such consent was provided.

    Deterministic: whether a document is present is a matter of fact.
    """
    documents = store.documents
    findings: list[Finding] = []
    seen: set[str] = set()

    for index, reference in enumerate(find_references(documents)):
        if reference_is_satisfied(reference, documents):
            continue

        key = _normalise(f"{reference.description} {reference.date_text}")
        if key in seen:
            continue
        seen.add(key)

        findings.append(
            Finding(
                finding_id=f"gap-ref-{index:03d}",
                finding_type=FindingType.MISSING_DOCUMENT,
                severity=Severity.HIGH,
                title=f"Referenced but absent: {reference.description}",
                description=(
                    f"{reference.source_document} states that a "
                    f"{reference.description} dated {reference.date_text} "
                    f'exists: "{reference.quote}". No such document appears '
                    f"in the data room. A document cited by name and date is "
                    f"being asserted as a discrete executed instrument, so "
                    f"its absence means the action it records cannot be "
                    f"verified as properly authorised."
                ),
                evidence=(reference.span,),
                confidence=0.85,
                raised_by=DETECTOR_NAME,
            )
        )

    log.info("reference audit complete", missing=len(findings))
    return findings

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

    
    findings.extend(detect_missing_references(store))

    log.info("gap audit complete", requested=len(REQUEST_LIST), gaps=len(findings))
    return findings
    return findings