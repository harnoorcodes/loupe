"""Tests for the typed substrate. All offline."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from loupe.models import (
    Claim,
    ClaimType,
    Currency,
    Finding,
    FindingStatus,
    FindingType,
    Severity,
    Span,
    SpanValidationError,
    is_valid_span,
    validate_span,
)

SOURCE = "The Company has issued 4,250,000 shares as of 31 December 2025."


def make_span(start: int = 23, end: int = 32, doc: str = "doc-1") -> Span:
    return Span(
        document_id=doc,
        page=1,
        char_start=start,
        char_end=end,
        text=SOURCE[start:end],
    )


class TestSpan:
    def test_valid_span(self) -> None:
        span = make_span()
        assert span.text == "4,250,000"
        assert span.length == 9

    def test_end_before_start_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Span(document_id="d", page=1, char_start=10, char_end=5, text="x")

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Span(document_id="d", page=1, char_start=0, char_end=1, text="")

    def test_page_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Span(document_id="d", page=0, char_start=0, char_end=1, text="x")

    def test_overlap_same_document(self) -> None:
        assert make_span(0, 10).overlaps(make_span(5, 15))
        assert not make_span(0, 10).overlaps(make_span(10, 20))

    def test_no_overlap_across_documents(self) -> None:
        assert not make_span(0, 10, "doc-1").overlaps(make_span(0, 10, "doc-2"))

    def test_citation_format(self) -> None:
        assert make_span().citation() == "doc-1 p.1"


class TestSpanValidation:
    def test_matching_span_passes(self) -> None:
        validate_span(make_span(), SOURCE)

    def test_fabricated_text_rejected(self) -> None:
        fake = Span(
            document_id="doc-1", page=1, char_start=23, char_end=32,
            text="9,999,999",
        )
        with pytest.raises(SpanValidationError, match="text mismatch"):
            validate_span(fake, SOURCE)

    def test_out_of_bounds_rejected(self) -> None:
        far = Span(
            document_id="doc-1", page=1, char_start=5000, char_end=5010,
            text="whatever",
        )
        with pytest.raises(SpanValidationError, match="exceeds document length"):
            validate_span(far, SOURCE)

    def test_is_valid_span_does_not_raise(self) -> None:
        bad = Span(
            document_id="doc-1", page=1, char_start=0, char_end=5, text="WRONG"
        )
        assert is_valid_span(make_span(), SOURCE)
        assert not is_valid_span(bad, SOURCE)


class TestClaim:
    def _monetary(self, **kw: object) -> Claim:
        base: dict[str, object] = {
            "claim_id": "c-1",
            "document_id": "doc-1",
            "claim_type": ClaimType.MONETARY,
            "subject": "acme-corp",
            "predicate": "annual revenue",
            "raw_text": "revenue of $4,250,000",
            "span": make_span(),
            "numeric_value": Decimal("4250000"),
            "currency": Currency.USD,
        }
        base.update(kw)
        return Claim(**base)  # type: ignore[arg-type]

    def test_monetary_requires_currency(self) -> None:
        with pytest.raises(ValidationError, match="currency"):
            self._monetary(currency=None)

    def test_monetary_requires_value(self) -> None:
        with pytest.raises(ValidationError, match="numeric_value"):
            self._monetary(numeric_value=None)

    def test_date_claim_requires_date(self) -> None:
        with pytest.raises(ValidationError, match="date_value"):
            Claim(
                claim_id="c-2", document_id="doc-1", claim_type=ClaimType.DATE,
                subject="acme-corp", predicate="incorporated",
                raw_text="incorporated 2019", span=make_span(),
            )

    def test_span_document_must_match(self) -> None:
        with pytest.raises(ValidationError, match="does not match"):
            self._monetary(span=make_span(doc="doc-99"))

    def test_different_currencies_not_comparable(self) -> None:
        usd = self._monetary()
        eur = self._monetary(claim_id="c-2", currency=Currency.EUR)
        assert not usd.is_comparable_to(eur)

    def test_same_currency_comparable(self) -> None:
        assert self._monetary().is_comparable_to(self._monetary(claim_id="c-2"))

    def test_different_subjects_not_comparable(self) -> None:
        a = self._monetary()
        b = self._monetary(claim_id="c-2", subject="other-corp")
        assert not a.is_comparable_to(b)

    def test_cross_document_detection(self) -> None:
        a = self._monetary()
        b = self._monetary(
            claim_id="c-2", document_id="doc-2", span=make_span(doc="doc-2")
        )
        assert a.is_cross_document(b)
        assert not a.is_cross_document(self._monetary(claim_id="c-3"))


class TestFinding:
    def _finding(self, **kw: object) -> Finding:
        base: dict[str, object] = {
            "finding_id": "f-1",
            "finding_type": FindingType.ARITHMETIC,
            "severity": Severity.HIGH,
            "title": "Share count does not reconcile",
            "description": "Cap table total differs from sum of grants.",
            "evidence": (make_span(),),
        }
        base.update(kw)
        return Finding(**base)  # type: ignore[arg-type]

    def test_evidence_required(self) -> None:
        with pytest.raises(ValidationError, match="evidence span"):
            self._finding(evidence=())

    def test_missing_document_needs_no_evidence(self) -> None:
        f = self._finding(
            finding_type=FindingType.MISSING_DOCUMENT, evidence=()
        )
        assert f.evidence == ()

    def test_materiality_requires_currency(self) -> None:
        with pytest.raises(ValidationError, match="materiality_currency"):
            self._finding(materiality=Decimal("100000"))

    def test_cross_document_flag(self) -> None:
        single = self._finding()
        assert not single.is_cross_document
        multi = self._finding(
            evidence=(make_span(doc="doc-1"),),
            contradicts=(make_span(doc="doc-2"),),
        )
        assert multi.is_cross_document

    def test_severity_ordering(self) -> None:
        low = self._finding(severity=Severity.LOW)
        crit = self._finding(severity=Severity.CRITICAL)
        assert crit.severity_rank > low.severity_rank


class TestFindingLifecycle:
    def _f(self) -> Finding:
        return Finding(
            finding_id="f-1",
            finding_type=FindingType.ARITHMETIC,
            severity=Severity.HIGH,
            title="Share count does not reconcile",
            description="Cap table total differs from sum of grants.",
            evidence=(make_span(),),
        )

    def test_starts_proposed(self) -> None:
        assert self._f().status is FindingStatus.PROPOSED

    def test_cannot_confirm_without_challenge(self) -> None:
        with pytest.raises(ValueError, match="must be challenged first"):
            self._f().confirm(by="critic")

    def test_challenge_then_confirm(self) -> None:
        f = self._f().challenge("Could be a rounding artifact.", by="critic")
        assert f.status is FindingStatus.CHALLENGED
        f = f.confirm(by="critic")
        assert f.status is FindingStatus.CONFIRMED
        assert f.reviewed_by == ("critic", "critic")

    def test_challenge_then_retract(self) -> None:
        f = self._f().challenge("Superseded by amendment.", by="critic")
        f = f.retract("Amendment resolves the discrepancy.", by="critic")
        assert f.status is FindingStatus.RETRACTED

    def test_original_is_unmutated(self) -> None:
        original = self._f()
        original.challenge("x", by="critic")
        assert original.status is FindingStatus.PROPOSED