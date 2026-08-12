"""Documents and the blocks extracted from them."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from loupe.models.span import Span


class DocumentType(StrEnum):
    """Coarse classification driving which extractors run on a document."""

    CONTRACT = "contract"
    FINANCIAL_STATEMENT = "financial_statement"
    CAP_TABLE = "cap_table"
    BOARD_MINUTES = "board_minutes"
    EMPLOYMENT_AGREEMENT = "employment_agreement"
    CORPORATE_CHARTER = "corporate_charter"
    COMPLIANCE_FILING = "compliance_filing"
    OTHER = "other"
    UNKNOWN = "unknown"


class ParseStatus(StrEnum):
    """Outcome of ingestion.

    Failures are values, not exceptions. FR-5 requires a specific reason
    rather than a silent skip -- an unreadable document becomes an entry in
    the gap report rather than a hole nobody notices.
    """

    OK = "ok"
    NO_TEXT_LAYER = "no_text_layer"
    ENCRYPTED = "encrypted"
    CORRUPT = "corrupt"
    UNSUPPORTED_FORMAT = "unsupported_format"
    WRONG_LANGUAGE = "wrong_language"


class BlockType(StrEnum):
    """Structural role of a block within its document."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE_ROW = "table_row"
    LIST_ITEM = "list_item"
    SIGNATURE = "signature"
    FOOTNOTE = "footnote"


class Block(BaseModel):
    """A structural unit of a document, carrying its own span.

    Blocks are what extraction agents read. Keeping the span on the block
    means a claim derived from it inherits real provenance rather than
    having offsets reconstructed after the fact.
    """

    model_config = {"frozen": True}

    block_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    block_type: BlockType
    text: str = Field(min_length=1)
    span: Span
    section_path: tuple[str, ...] = ()

    @property
    def page(self) -> int:
        return self.span.page


class Document(BaseModel):
    """A source document and its extraction result."""

    document_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    document_type: DocumentType = DocumentType.UNKNOWN
    parse_status: ParseStatus = ParseStatus.OK
    parse_error: str | None = None
    page_count: int = Field(default=0, ge=0)
    content_hash: str = ""
    text: str = ""
    blocks: tuple[Block, ...] = ()
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_readable(self) -> bool:
        """True if this document produced usable text."""
        return self.parse_status is ParseStatus.OK and bool(self.text)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def block_by_id(self, block_id: str) -> Block | None:
        """Look up a block, or None if absent."""
        return next((b for b in self.blocks if b.block_id == block_id), None)

    @staticmethod
    def compute_hash(raw_bytes: bytes) -> str:
        """Content hash for deduplication.

        Two uploads of the same file under different names must not produce
        duplicate findings or duplicate extraction cost.
        """
        return hashlib.sha256(raw_bytes).hexdigest()[:16]