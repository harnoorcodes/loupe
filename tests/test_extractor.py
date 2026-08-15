"""Extractor tests. Span resolution is tested offline; no API calls."""

from __future__ import annotations

from pathlib import Path

import pytest

from loupe.agents.extractor import RawClaim, resolve_claim
from loupe.ingestion import load_document
from loupe.models.span import validate_span


@pytest.fixture(scope="module")
def cap_table(tmp_path_factory: pytest.TempPathFactory):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from generate_corpus import write_pdf

    from loupe.corpus.documents.corporate import CAP_TABLE

    out = tmp_path_factory.mktemp("extract")
    write_pdf(CAP_TABLE, out)
    return load_document(out / "cap_table.pdf")


class TestSpanResolution:
    """The core guarantee: quotes are located, never trusted as offsets."""

    def test_exact_quote_resolves(self, cap_table) -> None:
        raw = RawClaim(
            claim_type="quantity",
            subject="Northwind Analytics",
            predicate="issued shares",
            quote="4,250,000",
            numeric_value="4250000",
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is not None
        validate_span(claim.span, cap_table.text)

    def test_fabricated_quote_is_discarded(self, cap_table) -> None:
        """A model inventing text must produce no claim, not a bad one."""
        raw = RawClaim(
            claim_type="quantity",
            subject="Northwind Analytics",
            predicate="issued shares",
            quote="9,999,999 shares were issued to nobody",
            numeric_value="9999999",
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is None

    def test_empty_quote_discarded(self, cap_table) -> None:
        raw = RawClaim(
            claim_type="status", subject="x", predicate="y", quote="   "
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is None

    def test_search_advances_for_repeated_quotes(self, cap_table) -> None:
        """Repeated text must resolve in document order, not all to the first."""
        needle = "shares"
        assert cap_table.text.count(needle) > 1
        raw = RawClaim(
            claim_type="status", subject="x", predicate="y", quote=needle
        )
        first, cursor = resolve_claim(raw, cap_table, 0)
        second, _ = resolve_claim(raw, cap_table, 1, cursor)
        assert first is not None
        assert second is not None
        assert second.span.char_start > first.span.char_start


class TestTypeCoercion:
    def test_monetary_without_value_rejected(self, cap_table) -> None:
        raw = RawClaim(
            claim_type="monetary",
            subject="x",
            predicate="y",
            quote="USD 2.40",
            numeric_value=None,
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is None

    def test_monetary_with_value_accepted(self, cap_table) -> None:
        raw = RawClaim(
            claim_type="monetary",
            subject="Kestrel Ventures",
            predicate="price per share",
            quote="USD 2.40",
            numeric_value="2.40",
            currency="USD",
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is not None
        assert claim.currency is not None

    def test_unknown_type_rejected(self, cap_table) -> None:
        raw = RawClaim(
            claim_type="nonsense", subject="x", predicate="y", quote="4,250,000"
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is None

    def test_numeric_with_separators_parsed(self, cap_table) -> None:
        raw = RawClaim(
            claim_type="quantity",
            subject="x",
            predicate="y",
            quote="4,250,000",
            numeric_value="4,250,000",
        )
        claim, _ = resolve_claim(raw, cap_table, 0)
        assert claim is not None
        assert claim.numeric_value == 4250000