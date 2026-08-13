"""Score card and memo tests. All offline."""

from __future__ import annotations

from pathlib import Path

import pytest

from loupe.corpus.content import PLANTED_DEFECTS
from loupe.eval.scoring import matches, render, score
from loupe.models.finding import Finding, FindingType, Severity
from loupe.models.span import Span
from loupe.report import memo
from loupe.store.evidence import EvidenceStore


def span(doc: str, text: str) -> Span:
    return Span(
        document_id=doc, page=1, char_start=0, char_end=len(text), text=text
    )


def finding(
    fid: str,
    ftype: FindingType,
    title: str,
    description: str = "d",
    spans: tuple[Span, ...] = (),
    severity: Severity = Severity.HIGH,
) -> Finding:
    """Build a confirmed finding, having passed through the lifecycle."""
    f = Finding(
        finding_id=fid,
        finding_type=ftype,
        severity=severity,
        title=title,
        description=description,
        evidence=spans,
    )
    return f.challenge("an objection", by="critic").confirm(by="critic")


def d001() -> Finding:
    return finding(
        "arith-shares-001",
        FindingType.ARITHMETIC,
        "Stated share total does not reconcile",
        "The cap table states 4,250,000 shares but 350,000 are unaccounted for.",
        (span("cap_table", "Total issued and outstanding shares: 4,250,000."),),
    )


def d002() -> Finding:
    return finding(
        "tension-400",
        FindingType.LATENT_LIABILITY,
        "Change of control termination on largest customer",
        "TitanRetail may terminate on thirty (30) days notice.",
        (
            span("contract_titanretail", "upon thirty (30) days written notice"),
            span("financial_statements_2025", "representing 43% of total revenue"),
        ),
    )


def d003() -> Finding:
    return finding(
        "gap-R-005",
        FindingType.MISSING_DOCUMENT,
        "Missing: Equity incentive plan document",
        "No equity incentive plan was found in the data room.",
    )


class TestMatching:
    def test_d001_matches(self) -> None:
        defect = next(d for d in PLANTED_DEFECTS if d.defect_id == "D-001")
        assert matches(d001(), defect)

    def test_d002_matches_latent_liability(self) -> None:
        """The defect accepts either label; the system chose latent_liability."""
        defect = next(d for d in PLANTED_DEFECTS if d.defect_id == "D-002")
        assert matches(d002(), defect)

    def test_d003_matches(self) -> None:
        defect = next(d for d in PLANTED_DEFECTS if d.defect_id == "D-003")
        assert matches(d003(), defect)

    def test_wrong_type_does_not_match(self) -> None:
        defect = next(d for d in PLANTED_DEFECTS if d.defect_id == "D-001")
        wrong = finding(
            "x", FindingType.MISSING_DOCUMENT, "Missing something", "4,250,000"
        )
        assert not matches(wrong, defect)

    def test_missing_anchor_does_not_match(self) -> None:
        defect = next(d for d in PLANTED_DEFECTS if d.defect_id == "D-001")
        wrong = finding(
            "x",
            FindingType.ARITHMETIC,
            "Some other sum",
            "Nothing relevant here.",
            (span("other_doc", "unrelated text"),),
        )
        assert not matches(wrong, defect)


class TestScoring:
    def test_all_three_detected(self) -> None:
        card = score((d001(), d002(), d003()))
        assert card.detected_count == 3
        assert card.recall == 1.0

    def test_none_detected(self) -> None:
        card = score(())
        assert card.detected_count == 0
        assert card.recall == 0.0

    def test_partial_detection(self) -> None:
        card = score((d001(),))
        assert card.detected_count == 1
        assert card.planted_count == 3

    def test_expected_gap_is_not_noise(self) -> None:
        """A real absence that was never planted must not count as an error."""
        extra = finding(
            "gap-R-014",
            FindingType.MISSING_DOCUMENT,
            "Missing: Tax returns for the last three years",
        )
        card = score((d001(), d002(), d003(), extra))
        assert len(card.extra_valid) == 1
        assert len(card.extra_noise) == 0

    def test_unrecognised_finding_is_noise(self) -> None:
        extra = finding(
            "gap-R-999", FindingType.MISSING_DOCUMENT, "Missing: Something invented"
        )
        card = score((extra,))
        assert len(card.extra_noise) == 1

    def test_one_finding_claims_one_defect(self) -> None:
        """A single finding must not be credited with detecting two defects."""
        card = score((d001(), d001()))
        assert card.detected_count == 1

    def test_render_contains_recall(self) -> None:
        text = render(score((d001(), d002(), d003())))
        assert "3/3" in text
        assert "D-001" in text


class TestMemo:
    @pytest.fixture
    def store(self, tmp_path: Path) -> EvidenceStore:
        s = EvidenceStore(tmp_path / "run")
        for f in (d001(), d002(), d003()):
            s.add_finding(f)
        return s

    def test_contains_all_findings(self, store: EvidenceStore) -> None:
        text = memo.build(store)
        assert "Stated share total does not reconcile" in text
        assert "Change of control termination" in text
        assert "Equity incentive plan" in text

    def test_citations_present(self, store: EvidenceStore) -> None:
        text = memo.build(store)
        assert "cap_table p.1" in text
        assert "financial_statements_2025 p.1" in text

    def test_gap_section_present(self, store: EvidenceStore) -> None:
        assert "Documents to request from the seller" in memo.build(store)

    def test_critic_objection_shown(self, store: EvidenceStore) -> None:
        """The reader should see what was argued against a finding."""
        assert "an objection" in memo.build(store)

    def test_disclaimer_present(self, store: EvidenceStore) -> None:
        assert "does not provide legal advice" in memo.build(store)

    def test_writes_file(self, store: EvidenceStore, tmp_path: Path) -> None:
        path = memo.write(store, tmp_path / "out" / "memo.md")
        assert path.exists()
        assert path.read_text(encoding="utf-8").startswith("# Due Diligence")

    def test_empty_store_does_not_crash(self, tmp_path: Path) -> None:
        empty = EvidenceStore(tmp_path / "empty")
        assert "No confirmed findings" in memo.build(empty)