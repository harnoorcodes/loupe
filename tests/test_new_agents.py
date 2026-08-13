"""Classifier and materiality scorer tests. All offline."""

from __future__ import annotations

from decimal import Decimal

from loupe.agents.classifier import coerce_type, format_documents
from loupe.agents.materiality import (
    Assessment,
    apply_assessment,
    format_finding,
    parse_amount,
)
from loupe.models.claim import Currency
from loupe.models.document import Document, DocumentType, ParseStatus
from loupe.models.finding import Finding, FindingType, Severity
from loupe.models.span import Span


def doc(doc_id: str, filename: str, text: str) -> Document:
    return Document(
        document_id=doc_id,
        filename=filename,
        parse_status=ParseStatus.OK,
        page_count=1,
        text=text,
    )


def finding(materiality: Decimal | None = None) -> Finding:
    text = "representing 43% of total revenue"
    return Finding(
        finding_id="f-1",
        finding_type=FindingType.LATENT_LIABILITY,
        severity=Severity.HIGH,
        title="Change of control risk",
        description="A major customer may terminate on acquisition.",
        evidence=(
            Span(
                document_id="d1",
                page=1,
                char_start=0,
                char_end=len(text),
                text=text,
            ),
        ),
        materiality=materiality,
        materiality_currency=Currency.USD if materiality else None,
    )


class TestClassifierCoercion:
    def test_known_type(self) -> None:
        assert coerce_type("cap_table") is DocumentType.CAP_TABLE

    def test_case_and_space_tolerated(self) -> None:
        assert coerce_type("  Contract  ") is DocumentType.CONTRACT

    def test_unknown_type_returns_none(self) -> None:
        assert coerce_type("spaceship_manual") is None


class TestClassifierPrompt:
    def test_ids_and_text_included(self) -> None:
        rendered = format_documents(
            (doc("d1", "a.pdf", "This is a cap table."),)
        )
        assert "DOCUMENT ID: d1" in rendered
        assert "cap table" in rendered

    def test_preview_is_truncated(self) -> None:
        rendered = format_documents((doc("d1", "a.pdf", "x" * 2000),))
        assert len(rendered) < 1000


class TestAmountParsing:
    def test_plain_digits(self) -> None:
        assert parse_amount("3612000") == Decimal("3612000")

    def test_separators_stripped(self) -> None:
        assert parse_amount("3,612,000") == Decimal("3612000")

    def test_currency_symbol_stripped(self) -> None:
        assert parse_amount("$3,612,000") == Decimal("3612000")

    def test_none_input(self) -> None:
        assert parse_amount(None) is None

    def test_empty_string(self) -> None:
        assert parse_amount("") is None

    def test_garbage_returns_none(self) -> None:
        assert parse_amount("about three million") is None

    def test_zero_returns_none(self) -> None:
        """Zero impact is not a useful estimate; treat it as unquantified."""
        assert parse_amount("0") is None


class TestApplyAssessment:
    def test_quantifiable_sets_amount(self) -> None:
        assessment = Assessment(
            finding_id="f-1",
            quantifiable=True,
            amount="3612000",
            basis="43% of USD 8,400,000 revenue",
            severity="critical",
        )
        result = apply_assessment(finding(), assessment, Currency.USD)
        assert result.materiality == Decimal("3612000")
        assert result.materiality_currency is Currency.USD
        assert result.severity is Severity.CRITICAL

    def test_unquantifiable_leaves_amount_unset(self) -> None:
        assessment = Assessment(
            finding_id="f-1",
            quantifiable=False,
            amount=None,
            basis="A missing tax return has no inherent value.",
            severity="medium",
        )
        result = apply_assessment(finding(), assessment, Currency.USD)
        assert result.materiality is None
        assert result.severity is Severity.MEDIUM

    def test_bad_amount_does_not_set_materiality(self) -> None:
        """A model claiming quantifiable but returning nonsense sets nothing."""
        assessment = Assessment(
            finding_id="f-1",
            quantifiable=True,
            amount="a lot of money",
            basis="unclear",
            severity="high",
        )
        result = apply_assessment(finding(), assessment, Currency.USD)
        assert result.materiality is None

    def test_unknown_severity_ignored(self) -> None:
        assessment = Assessment(
            finding_id="f-1",
            quantifiable=False,
            amount=None,
            basis="n/a",
            severity="apocalyptic",
        )
        result = apply_assessment(finding(), assessment, Currency.USD)
        assert result.severity is Severity.HIGH


class TestMaterialityPrompt:
    def test_evidence_quoted(self) -> None:
        rendered = format_finding(finding())
        assert "43% of total revenue" in rendered
        assert "FINDING ID: f-1" in rendered

    def test_absent_evidence_stated(self) -> None:
        gap = Finding(
            finding_id="g-1",
            finding_type=FindingType.MISSING_DOCUMENT,
            severity=Severity.HIGH,
            title="Missing tax returns",
            description="Not provided.",
        )
        assert "none" in format_finding(gap)