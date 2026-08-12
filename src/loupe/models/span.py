"""Source spans: the atom of provenance.

Every claim and every finding in this system must resolve to a Span. A Span
identifies an exact character range in an exact document, together with the
text that was there when it was captured.

The design intent is that the system is architecturally incapable of making
an uncited assertion. Objective O-4 requires 100% of emitted spans to resolve
to real source text; validate_span() below is the mechanism that enforces it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

MAX_QUOTE_CHARS = 2000


class Span(BaseModel):
    """An exact character range within a source document.

    Attributes:
        document_id: Stable identifier of the source document.
        page: 1-indexed page number, for human navigation.
        char_start: Inclusive start offset into the document's extracted text.
        char_end: Exclusive end offset.
        text: The text captured at those offsets, for validation and display.
    """

    model_config = {"frozen": True}

    document_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=MAX_QUOTE_CHARS)

    @model_validator(mode="after")
    def _check_range(self) -> Span:
        """Reject ranges that cannot describe real text."""
        if self.char_end <= self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must exceed char_start "
                f"({self.char_start})"
            )
        return self

    @property
    def length(self) -> int:
        """Character length of the range."""
        return self.char_end - self.char_start

    def overlaps(self, other: Span) -> bool:
        """Return True if two spans cover any of the same characters.

        Used to deduplicate claims extracted from the same passage.
        """
        if self.document_id != other.document_id:
            return False
        return self.char_start < other.char_end and other.char_start < self.char_end
    
    def overlaps_offset(self, offset: int) -> bool:
        """True if a character offset falls inside this span."""
        return self.char_start <= offset < self.char_end

    def citation(self) -> str:
        """Return a short human-readable reference, e.g. 'doc-7 p.4'."""
        return f"{self.document_id} p.{self.page}"

    def __str__(self) -> str:
        preview = self.text if len(self.text) <= 60 else self.text[:57] + "..."
        return f"[{self.citation()}] {preview!r}"


class SpanValidationError(Exception):
    """Raised when a span does not match the source document."""


def validate_span(span: Span, source_text: str) -> None:
    """Verify a span's offsets and text against the real document.

    This is the provenance-or-abstain mechanism. A model can produce a
    plausible-looking Span for text that does not exist; this function is
    what catches that. Findings whose spans fail validation are retracted,
    never softened or caveated.

    Args:
        span: The span to check.
        source_text: Full extracted text of the document it claims to cite.

    Raises:
        SpanValidationError: If offsets are out of bounds or the text at
            those offsets differs from the span's recorded text.
    """
    if span.char_end > len(source_text):
        raise SpanValidationError(
            f"{span.citation()}: char_end {span.char_end} exceeds document "
            f"length {len(source_text)}"
        )

    actual = source_text[span.char_start : span.char_end]
    if actual != span.text:
        raise SpanValidationError(
            f"{span.citation()}: text mismatch at [{span.char_start}:"
            f"{span.char_end}]. Expected {span.text[:60]!r}, "
            f"found {actual[:60]!r}"
        )


def is_valid_span(span: Span, source_text: str) -> bool:
    """Non-raising form of validate_span, for filtering collections."""
    try:
        validate_span(span, source_text)
    except SpanValidationError:
        return False
    return True