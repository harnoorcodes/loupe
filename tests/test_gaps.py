"""Gap auditor, critic, and approval gate tests. All offline."""

from __future__ import annotations

from pathlib import Path

import pytest

from loupe.agents.approval import apply_decision, requires_approval
from loupe.agents.critic import format_finding, validate_evidence
from loupe.corpus.request_list import REQUEST_LIST
from loupe.detect import gaps
from loupe.detect.gaps import _presence_haystack, is_required, is_satisfied
from loupe.models.claim import Claim, ClaimType
from loupe.models.document import Document, DocumentType, ParseStatus
from loupe.models.finding import Finding, FindingStatus, FindingType, Severity
from loupe.models.span import Span
from loupe.store.evidence import EvidenceStore

TEXT = (
    "Employee option grants outstanding: 410,000 options have been granted "
    "to employees under the company equity incentive plan."
)


def doc(doc_id: str, filename: str, text: str = TEXT) -> Document:
    return Document(
        document_id=doc_id,
        filename=filename,
        document_type=DocumentType.OTHER,
        parse_status=ParseStatus.OK,
        page_count=1,
        text=text,
    )


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path / "run")


class TestSatisfaction:
    def test_keyword_in_filename_satisfies(self) -> None:
        item = next(i for i in REQUEST_LIST if i.item_id == "R-002")
        assert is_satisfied(item, "cap table pdf")

    def test_underscores_match_spaces(self) -> None:
        """Filenames use underscores; keyword phrases use spaces."""
        item = next(i for i in REQUEST_LIST if i.item_id == "R-002")
        assert is_satisfied(item, _presence_haystack((doc("c", "cap_table.pdf"),)))

    def test_absent_keyword_not_satisfied(self) -> None:
        item = next(i for i in REQUEST_LIST if i.item_id == "R-014")
        assert not is_satisfied(item, _presence_haystack((doc("c", "cap_table.pdf"),)))

    def test_mention_in_body_text_does_not_satisfy(self) -> None:
        """A reference to a document is not the document.

        This is the core of D-003. The cap table mentions an equity
        incentive plan and no plan file exists. Treating the mention as
        presence would hide the defect the audit exists to find.
        """
        item = next(i for i in REQUEST_LIST if i.item_id == "R-005")
        presence = _presence_haystack((doc("cap_table", "cap_table.pdf"),))
        assert not is_satisfied(item, presence)


class TestConditionalRequirement:
    def test_option_plan_required_when_options_granted(self) -> None:
        """The plan is required BECAUSE options exist in the corpus."""
        item = next(i for i in REQUEST_LIST if i.item_id == "R-005")
        assert is_required(item, "410,000 options have been granted")

    def test_option_plan_not_required_without_options(self) -> None:
        item = next(i for i in REQUEST_LIST if i.item_id == "R-005")
        assert not is_required(item, "a company with no equity awards at all")

    def test_unconditional_item_always_required(self) -> None:
        item = next(i for i in REQUEST_LIST if i.item_id == "R-001")
        assert is_required(item, "")


class TestGapDetection:
    def test_detects_missing_option_plan(self, store: EvidenceStore) -> None:
        """D-003 end to end."""
        store.add_document(doc("cap_table", "cap_table.pdf"))
        findings = gaps.detect(store)
        assert "gap-R-005" in {f.finding_id for f in findings}

    def test_present_document_produces_no_gap(self, store: EvidenceStore) -> None:
        store.add_document(doc("plan", "equity_incentive_plan.pdf"))
        findings = gaps.detect(store)
        assert "gap-R-005" not in {f.finding_id for f in findings}

    def test_gap_findings_need_no_evidence(self, store: EvidenceStore) -> None:
        """Absence has no span to cite. The model must permit that."""
        store.add_document(doc("cap_table", "cap_table.pdf"))
        for finding in gaps.detect(store):
            assert finding.finding_type in {
                FindingType.MISSING_DOCUMENT,
                FindingType.UNREADABLE_DOCUMENT,
            }
            assert finding.evidence == ()

    def test_trigger_quoted_in_description(self, store: EvidenceStore) -> None:
        store.add_document(doc("cap_table", "cap_table.pdf"))
        store.add_claim(
            Claim(
                claim_id="c-1",
                document_id="cap_table",
                claim_type=ClaimType.STATUS,
                subject="Northwind",
                predicate="options granted under equity incentive plan",
                raw_text="410,000 options have been granted",
                span=Span(
                    document_id="cap_table",
                    page=1,
                    char_start=0,
                    char_end=33,
                    text="410,000 options have been granted",
                ),
            )
        )
        finding = next(f for f in gaps.detect(store) if f.finding_id == "gap-R-005")
        assert "410,000" in finding.description

    def test_unreadable_document_reported(self, store: EvidenceStore) -> None:
        store.add_document(
            Document(
                document_id="broken",
                filename="scan.pdf",
                parse_status=ParseStatus.NO_TEXT_LAYER,
                parse_error="no text layer",
            )
        )
        assert "unreadable-broken" in {f.finding_id for f in gaps.detect(store)}


class TestEvidenceValidation:
    def test_valid_evidence_passes(self, store: EvidenceStore) -> None:
        source = "The total is 4,250,000 shares."
        store.add_document(doc("d1", "d1.pdf", source))
        start = source.index("4,250,000")
        finding = Finding(
            finding_id="f-1",
            finding_type=FindingType.ARITHMETIC,
            severity=Severity.HIGH,
            title="t",
            description="d",
            evidence=(
                Span(
                    document_id="d1",
                    page=1,
                    char_start=start,
                    char_end=start + 9,
                    text="4,250,000",
                ),
            ),
        )
        assert validate_evidence(finding, store)

    def test_fabricated_evidence_fails(self, store: EvidenceStore) -> None:
        store.add_document(doc("d1", "d1.pdf", "The total is 4,250,000 shares."))
        finding = Finding(
            finding_id="f-1",
            finding_type=FindingType.ARITHMETIC,
            severity=Severity.HIGH,
            title="t",
            description="d",
            evidence=(
                Span(
                    document_id="d1",
                    page=1,
                    char_start=0,
                    char_end=9,
                    text="9,999,999",
                ),
            ),
        )
        assert not validate_evidence(finding, store)

    def test_unknown_document_fails(self, store: EvidenceStore) -> None:
        finding = Finding(
            finding_id="f-1",
            finding_type=FindingType.ARITHMETIC,
            severity=Severity.HIGH,
            title="t",
            description="d",
            evidence=(
                Span(
                    document_id="ghost",
                    page=1,
                    char_start=0,
                    char_end=3,
                    text="abc",
                ),
            ),
        )
        assert not validate_evidence(finding, store)


class TestApprovalGate:
    def _confirmed(self, severity: Severity) -> Finding:
        f = Finding(
            finding_id="f-1",
            finding_type=FindingType.MISSING_DOCUMENT,
            severity=severity,
            title="t",
            description="d",
        )
        return f.challenge("objection", by="critic").confirm(by="critic")

    def test_critical_requires_approval(self) -> None:
        assert requires_approval(self._confirmed(Severity.CRITICAL))

    def test_high_does_not(self) -> None:
        assert not requires_approval(self._confirmed(Severity.HIGH))

    def test_unconfirmed_not_gated(self) -> None:
        f = Finding(
            finding_id="f-1",
            finding_type=FindingType.MISSING_DOCUMENT,
            severity=Severity.CRITICAL,
            title="t",
            description="d",
        )
        assert not requires_approval(f)

    def test_rejection_retracts(self) -> None:
        f = apply_decision(self._confirmed(Severity.CRITICAL), False, "immaterial")
        assert f.status is FindingStatus.RETRACTED

    def test_approval_records_reviewer(self) -> None:
        f = apply_decision(self._confirmed(Severity.CRITICAL), True)
        assert "human_reviewer" in f.reviewed_by


class TestCriticFormatting:
    def test_absent_evidence_is_explicit(self) -> None:
        f = Finding(
            finding_id="f-1",
            finding_type=FindingType.MISSING_DOCUMENT,
            severity=Severity.HIGH,
            title="Missing plan",
            description="No plan document found.",
        )
        assert "ABSENT" in format_finding(f)
        