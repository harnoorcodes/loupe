"""Typed substrate shared by every agent."""

from loupe.models.claim import Claim, ClaimType, Currency
from loupe.models.document import (
    Block,
    BlockType,
    Document,
    DocumentType,
    ParseStatus,
)
from loupe.models.finding import Finding, FindingStatus, FindingType, Severity
from loupe.models.span import (
    Span,
    SpanValidationError,
    is_valid_span,
    validate_span,
)

__all__ = [
    "Block",
    "BlockType",
    "Claim",
    "ClaimType",
    "Currency",
    "Document",
    "DocumentType",
    "Finding",
    "FindingStatus",
    "FindingType",
    "ParseStatus",
    "Severity",
    "Span",
    "SpanValidationError",
    "is_valid_span",
    "validate_span",
]