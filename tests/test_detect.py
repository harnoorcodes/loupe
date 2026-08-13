"""Detector tests. Deterministic detectors tested fully offline."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from loupe.detect import arithmetic, temporal
from loupe.detect.temporal import extract_date
from loupe.detect.tension import RawTension, format_claims, resolve_tension
from loupe.models.claim import Claim, ClaimType
from loupe.models.finding import FindingType, Severity
from loupe.models.span import Span
from loupe.store.evidence import EvidenceStore


def make_claim(
    cid: str,
    doc: str,
    predicate: str,
    raw: str,
    value: Decimal | None = None,
    ctype: ClaimType = ClaimType.QUANTITY,
    subject: str = "Northwind Analytics",
) -> Claim:
    return Claim(
        claim_id=cid,
        document_id=doc,
        claim_type=ctype,
        subject=subject,
        predicate=predicate,
        raw_text=raw,
        span=Span(
            document_id=doc, page=1, char_start=0, char_end=len(raw), text=raw
        ),
        numeric_value=value,
    )


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path / "run")


class TestArithmetic:
    def test_detects_the_planted_mismatch(self, store: EvidenceStore) -> None:
        """D-001: 1.8M + 1.2M + 900k + 410k = 4.31M, not the stated 4.25M."""
        store.add_claim(
            make_claim(
                "c-1", "cap_table", "total issued and outstanding shares",
                "Total issued and outstanding shares: 4,250,000",
                Decimal("4250000"),
            )
        )
        for cid, name, amount in (
            ("c-2", "Sarah Chen holds 1,800,000 common shares", "1800000"),
            ("c-3", "David Okonkwo holds 1,200,000 common shares", "1200000"),
            ("c-4", "Kestrel Ventures LP holds 900,000 preferred shares", "900000"),
            ("c-5", "410,000 options have been granted to employees", "410000"),
        ):
            store.add_claim(
                make_claim(cid, "cap_table", "holds shares", name, Decimal(amount))
            )

        findings = arithmetic.detect(store)
        assert len(findings) == 1
        assert findings[0].finding_type is FindingType.ARITHMETIC
        assert "60,000" in findings[0].description

    def test_reconciling_totals_produce_nothing(self, store: EvidenceStore) -> None:
        """A correct cap table must produce no finding. Precision matters."""
        store.add_claim(
            make_claim(
                "c-1", "cap_table", "total outstanding shares",
                "Total outstanding shares: 3,000,000", Decimal("3000000"),
            )
        )
        store.add_claim(
            make_claim(
                "c-2", "cap_table", "holds shares",
                "Sarah Chen holds 2,000,000 common shares", Decimal("2000000"),
            )
        )
        store.add_claim(
            make_claim(
                "c-3", "cap_table", "holds shares",
                "David Okonkwo holds 1,000,000 common shares", Decimal("1000000"),
            )
        )
        assert arithmetic.detect(store) == []

    def test_authorised_shares_excluded(self, store: EvidenceStore) -> None:
        """Authorised capital is a ceiling, not a total of holdings."""
        store.add_claim(
            make_claim(
                "c-1", "articles", "authorised shares of common stock",
                "authorised capital consists of 10,000,000 shares",
                Decimal("10000000"),
            )
        )
        store.add_claim(
            make_claim(
                "c-2", "cap_table", "holds shares",
                "Sarah Chen holds 1,800,000 common shares", Decimal("1800000"),
            )
        )
        assert arithmetic.detect(store) == []

    def test_no_components_produces_nothing(self, store: EvidenceStore) -> None:
        store.add_claim(
            make_claim(
                "c-1", "cap_table", "total shares",
                "Total shares: 4,250,000", Decimal("4250000"),
            )
        )
        assert arithmetic.detect(store) == []


class TestDateParsing:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("dated 14 March 2024", date(2024, 3, 14)),
            ("on March 14, 2024", date(2024, 3, 14)),
            ("incorporated on 19 June 2019", date(2019, 6, 19)),
            ("no date here", None),
            ("32 March 2024", None),
        ],
    )
    def test_parsing(self, text: str, expected: date | None) -> None:
        assert extract_date(text) == expected


class TestTemporal:
    def test_detects_event_before_incorporation(self, store: EvidenceStore) -> None:
        store.add_claim(
            make_claim(
                "c-1", "articles", "was incorporated on",
                "incorporated in Delaware on 19 June 2019",
                ctype=ClaimType.STATUS,
            )
        )
        store.add_claim(
            make_claim(
                "c-2", "contract", "agreement entered into",
                "entered into on 8 May 2018", ctype=ClaimType.STATUS,
            )
        )
        findings = temporal.detect(store)
        assert len(findings) == 1
        assert findings[0].finding_type is FindingType.TEMPORAL_IMPOSSIBILITY

    def test_normal_ordering_produces_nothing(self, store: EvidenceStore) -> None:
        store.add_claim(
            make_claim(
                "c-1", "articles", "was incorporated on",
                "incorporated in Delaware on 19 June 2019",
                ctype=ClaimType.STATUS,
            )
        )
        store.add_claim(
            make_claim(
                "c-2", "contract", "agreement entered into",
                "entered into on 8 May 2024", ctype=ClaimType.STATUS,
            )
        )
        assert temporal.detect(store) == []


class TestTensionResolution:
    """The model cannot manufacture findings from claims it was not given."""

    def _pair(self) -> dict[str, Claim]:
        a = make_claim(
            "c-1", "contract_titanretail", "may terminate on change of control",
            "Customer may terminate upon thirty days notice",
            ctype=ClaimType.RIGHT, subject="TitanRetail Group",
        )
        b = make_claim(
            "c-2", "financial_statements", "share of total revenue",
            "representing 43% of total revenue",
            ctype=ClaimType.STATUS, subject="TitanRetail Group",
        )
        return {"c-1": a, "c-2": b}

    def test_valid_pair_resolves(self) -> None:
        raw = RawTension(
            claim_id_a="c-1", claim_id_b="c-2",
            conflict_type="latent_liability", severity="high",
            title="Change of control risk on largest customer",
            explanation="Termination right held by a 43% revenue customer.",
        )
        finding = resolve_tension(raw, self._pair(), 0)
        assert finding is not None
        assert finding.finding_type is FindingType.LATENT_LIABILITY
        assert finding.is_cross_document

    def test_hallucinated_claim_id_discarded(self) -> None:
        raw = RawTension(
            claim_id_a="c-1", claim_id_b="c-999",
            conflict_type="contradiction", severity="critical",
            title="Invented conflict",
            explanation="Cites a claim that was never supplied.",
        )
        assert resolve_tension(raw, self._pair(), 0) is None

    def test_self_pair_discarded(self) -> None:
        raw = RawTension(
            claim_id_a="c-1", claim_id_b="c-1",
            conflict_type="contradiction", severity="high",
            title="Claim conflicts with itself",
            explanation="Nonsense.",
        )
        assert resolve_tension(raw, self._pair(), 0) is None

    def test_cross_document_escalates_severity(self) -> None:
        raw = RawTension(
            claim_id_a="c-1", claim_id_b="c-2",
            conflict_type="contradiction", severity="medium",
            title="Cross-document conflict",
            explanation="Two documents disagree.",
        )
        finding = resolve_tension(raw, self._pair(), 0)
        assert finding is not None
        assert finding.severity is Severity.HIGH

    def test_unknown_severity_defaults_to_medium(self) -> None:
        raw = RawTension(
            claim_id_a="c-1", claim_id_b="c-2",
            conflict_type="contradiction", severity="apocalyptic",
            title="Odd severity",
            explanation="Model returned a value outside the enum.",
        )
        finding = resolve_tension(raw, self._pair(), 0)
        assert finding is not None


class TestPromptFormatting:
    def test_claim_ids_and_sources_visible(self) -> None:
        claims = (
            make_claim("c-1", "doc-a", "p", "text one", ctype=ClaimType.STATUS),
            make_claim("c-2", "doc-b", "p", "text two", ctype=ClaimType.STATUS),
        )
        rendered = format_claims(claims)
        assert "[c-1]" in rendered
        assert "source: doc-a" in rendered
        assert "[c-2]" in rendered