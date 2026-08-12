"""Document ingestion."""

from loupe.ingestion.loader import (
    classify,
    load_directory,
    load_document,
    segment_blocks,
)
from loupe.ingestion.parsers import ParsedText, page_for_offset

__all__ = [
    "ParsedText",
    "classify",
    "load_directory",
    "load_document",
    "page_for_offset",
    "segment_blocks",
]