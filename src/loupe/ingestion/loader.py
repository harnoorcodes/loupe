"""Document loading: file on disk to a typed Document with Blocks."""

from __future__ import annotations

import re
from pathlib import Path

from loupe.ingestion.parsers import (
    ParsedText,
    page_for_offset,
    parse_docx,
    parse_pdf,
)
from loupe.models.document import (
    Block,
    BlockType,
    Document,
    DocumentType,
    ParseStatus,
)
from loupe.models.span import Span
from loupe.observability.logging import get_logger

log = get_logger(__name__)

MIN_BLOCK_CHARS = 15
MAX_BLOCK_CHARS = 2000
HEADING_MAX_CHARS = 120

_TYPE_HINTS: tuple[tuple[str, DocumentType], ...] = (
    ("cap_table", DocumentType.CAP_TABLE),
    ("capitalisation", DocumentType.CAP_TABLE),
    ("financial", DocumentType.FINANCIAL_STATEMENT),
    ("contract", DocumentType.CONTRACT),
    ("agreement", DocumentType.CONTRACT),
    ("minutes", DocumentType.BOARD_MINUTES),
    ("employment", DocumentType.EMPLOYMENT_AGREEMENT),
    ("articles", DocumentType.CORPORATE_CHARTER),
    ("incorporation", DocumentType.CORPORATE_CHARTER),
    ("insurance", DocumentType.COMPLIANCE_FILING),
)


def classify(filename: str) -> DocumentType:
    """Infer document type from filename.

    Deliberately a heuristic. An LLM classifier is added in a later
    milestone; this keeps ingestion free and deterministic.
    """
    lowered = filename.lower()
    for hint, doc_type in _TYPE_HINTS:
        if hint in lowered:
            return doc_type
    return DocumentType.OTHER


def _block_type(text: str, index: int) -> BlockType:
    """Classify a block by shape."""
    stripped = text.strip()
    if index == 0 and len(stripped) <= HEADING_MAX_CHARS:
        return BlockType.HEADING
    if "|" in stripped:
        return BlockType.TABLE_ROW
    if re.match(r"^(Section\s+\d+|Resolution\s+\d+|\d+\.)\s", stripped):
        return BlockType.HEADING
    return BlockType.PARAGRAPH


def _split_candidates(text: str) -> list[str]:
    """Split text into candidate blocks, tolerating PDF line wrapping.

    PDF extraction emits single newlines both between paragraphs and within
    a wrapped line, so a newline alone is not a reliable paragraph boundary.
    Strategy: split on every newline, then rejoin fragments that are clearly
    continuations -- lines that do not start a new sentence, or that follow
    a line which did not end one.
    """
    merged: list[str] = []

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if not merged:
            merged.append(line)
            continue

        previous = merged[-1]
        starts_new = bool(re.match(r"^[A-Z0-9\u2022\-]", line))
        previous_ended = previous.endswith((".", ":", ";", "?", "!"))

        if previous_ended and starts_new:
            merged.append(line)
        else:
            merged[-1] = f"{previous} {line}"

    return merged


def segment_blocks(document_id: str, parsed: ParsedText) -> tuple[Block, ...]:
    """Split extracted text into blocks with accurate spans.

    Offsets are located by scanning the extracted text directly, never
    reconstructed from source content. This is what keeps spans valid.

    Note that merging rejoins wrapped lines with a single space, so the
    merged string does not appear verbatim in the source. Offsets are
    therefore anchored on the first and last word of each block, and the
    span's text is taken from the source slice rather than from the merged
    string. Block.text is the readable version for the LLM; Span.text is
    the exact source text so validate_span always succeeds.
    """
    blocks: list[Block] = []
    cursor = 0
    index = 0

    for chunk in _split_candidates(parsed.text):
        if len(chunk) < MIN_BLOCK_CHARS:
            continue

        head = chunk.split(" ", 1)[0]
        tail = chunk.rsplit(" ", 1)[-1]

        start = parsed.text.find(head, cursor)
        if start == -1:
            continue
        tail_at = parsed.text.find(tail, start)
        if tail_at == -1:
            continue
        end = tail_at + len(tail)

        source_text = parsed.text[start:end]
        if not source_text.strip():
            continue

        span = Span(
            document_id=document_id,
            page=page_for_offset(start, parsed.page_offsets),
            char_start=start,
            char_end=end,
            text=source_text[:MAX_BLOCK_CHARS],
        )
        blocks.append(
            Block(
                block_id=f"{document_id}-b{index:04d}",
                document_id=document_id,
                block_type=_block_type(chunk, index),
                text=chunk[:MAX_BLOCK_CHARS],
                span=span,
            )
        )
        cursor = end
        index += 1

    return tuple(blocks)


def load_document(path: Path, document_id: str | None = None) -> Document:
    """Load one file into a typed Document.

    Never raises on a bad file. Parse failures become ParseStatus values so
    that one unreadable document cannot terminate a run.
    """
    doc_id = document_id or path.stem
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        parsed = parse_pdf(path)
    elif suffix == ".docx":
        parsed = parse_docx(path)
    else:
        parsed = ParsedText(
            "", (), 0, ParseStatus.UNSUPPORTED_FORMAT, f"unsupported: {suffix}"
        )

    content_hash = ""
    try:
        content_hash = Document.compute_hash(path.read_bytes())
    except OSError as exc:
        log.warning("hash failed", document_id=doc_id, error=str(exc))

    if parsed.status is not ParseStatus.OK:
        log.warning(
            "document unreadable",
            document_id=doc_id,
            status=parsed.status.value,
            reason=parsed.error,
        )
        return Document(
            document_id=doc_id,
            filename=path.name,
            document_type=classify(path.name),
            parse_status=parsed.status,
            parse_error=parsed.error,
            content_hash=content_hash,
        )

    blocks = segment_blocks(doc_id, parsed)
    log.info(
        "document loaded",
        document_id=doc_id,
        pages=parsed.page_count,
        blocks=len(blocks),
        chars=len(parsed.text),
    )

    return Document(
        document_id=doc_id,
        filename=path.name,
        document_type=classify(path.name),
        parse_status=ParseStatus.OK,
        page_count=parsed.page_count,
        content_hash=content_hash,
        text=parsed.text,
        blocks=blocks,
    )


def load_directory(directory: Path) -> tuple[Document, ...]:
    """Load every supported file in a directory, deduplicating by content.

    Returns documents in filename order for deterministic runs.
    """
    seen: dict[str, str] = {}
    documents: list[Document] = []

    for path in sorted(directory.iterdir()):
        if path.suffix.lower() not in {".pdf", ".docx"}:
            continue
        doc = load_document(path)
        if doc.content_hash and doc.content_hash in seen:
            log.info(
                "duplicate skipped",
                document_id=doc.document_id,
                same_as=seen[doc.content_hash],
            )
            continue
        if doc.content_hash:
            seen[doc.content_hash] = doc.document_id
        documents.append(doc)

    readable = sum(1 for d in documents if d.is_readable)
    log.info(
        "directory loaded",
        total=len(documents),
        readable=readable,
        unreadable=len(documents) - readable,
    )
    return tuple(documents)