"""Assembles the full corpus and its ground truth.

Import from here rather than from the individual document modules, so that
adding a document category does not require changes at every call site.
"""

from __future__ import annotations

from loupe.corpus.defects import (
    DEFECT_CLASSES,
    DIFFICULTY_ORDER,
    EXPECTED_GAPS,
    PLANTED_DEFECTS,
    primary_class,
)
from loupe.corpus.documents.commercial import COMMERCIAL_DOCUMENTS
from loupe.corpus.documents.compliance import COMPLIANCE_DOCUMENTS
from loupe.corpus.documents.corporate import CORPORATE_DOCUMENTS
from loupe.corpus.documents.employment import EMPLOYMENT_DOCUMENTS
from loupe.corpus.documents.financial import FINANCIAL_DOCUMENTS
from loupe.corpus.spec import DocSpec, ExpectedGap, PlantedDefect

ALL_DOCUMENTS: tuple[DocSpec, ...] = (
    *CORPORATE_DOCUMENTS,
    *FINANCIAL_DOCUMENTS,
    *COMMERCIAL_DOCUMENTS,
    *EMPLOYMENT_DOCUMENTS,
    *COMPLIANCE_DOCUMENTS,
)

CATEGORIES: dict[str, tuple[DocSpec, ...]] = {
    "corporate": CORPORATE_DOCUMENTS,
    "financial": FINANCIAL_DOCUMENTS,
    "commercial": COMMERCIAL_DOCUMENTS,
    "employment": EMPLOYMENT_DOCUMENTS,
    "compliance": COMPLIANCE_DOCUMENTS,
}

__all__ = [
    "ALL_DOCUMENTS",
    "CATEGORIES",
    "DEFECT_CLASSES",
    "DIFFICULTY_ORDER",
    "EXPECTED_GAPS",
    "PLANTED_DEFECTS",
    "DocSpec",
    "ExpectedGap",
    "PlantedDefect",
    "primary_class",
]
