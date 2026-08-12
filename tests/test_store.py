"""Evidence store tests. All offline."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from loupe.models.claim import Claim, ClaimType
from loupe.models.finding import Finding, FindingStatus, FindingType, Severity
from loupe.models.span import Span
from loupe.store.evidence import EvidenceStore


def span(doc: str = "doc-1") -> Span:
    return Span(
        document_id=doc, page=1, char_start=0, char_end=9, text="4,250,000"
    )


def claim(cid: str = "c-1", doc: str = "doc-1", subject: str = "northwind") -> Claim:
    return Claim(
        claim_id=cid,
        document_id=doc,
        claim_type=ClaimType.QUANTITY,
        subject=subject,
        predicate="issued shares",
        raw_text="4,250,000",
        span=span(doc),
        numeric_value=Decimal("4250000"),
    )


def finding(fid: str = "f-1") -> Finding:
    return Finding(
        finding_id=fid,
        finding_type=FindingType.ARITHMETIC,
        severity=Severity.HIGH,
        title="Share count mismatch",
        description="Total does not reconcile.",
        evidence=(span(),),
    )


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    return EvidenceStore(tmp_path / "run")


class TestClaims:
    def test_add_and_retrieve(self, store: EvidenceStore) -> None:
        store.add_claim(claim())
        assert len(store.claims) == 1

    def test_claims_by_document(self, store: EvidenceStore) -> None:
        store.add_claim(claim("c-1", "doc-1"))
        store.add_claim(claim("c-2", "doc-2"))
        assert len(store.claims_for_document("doc-1")) == 1

    def test_claims_about_subject_is_cross_document(
        self, store: EvidenceStore
    ) -> None:
        """The retrieval primitive the tension detector depends on."""
        store.add_claim(claim("c-1", "doc-1", "Northwind Analytics Inc."))
        store.add_claim(claim("c-2", "doc-2", "Northwind Analytics"))
        store.add_claim(claim("c-3", "doc-3", "TitanRetail Group"))
        matches = store.claims_about("Northwind Analytics Limited")
        assert len(matches) == 2
        assert {m.document_id for m in matches} == {"doc-1", "doc-2"}

    def test_subjects_ordered_by_frequency(self, store: EvidenceStore) -> None:
        store.add_claim(claim("c-1", "doc-1", "northwind"))
        store.add_claim(claim("c-2", "doc-2", "northwind"))
        store.add_claim(claim("c-3", "doc-3", "titanretail"))
        assert store.subjects()[0] == "northwind"

    def test_duplicate_id_does_not_double_index(
        self, store: EvidenceStore
    ) -> None:
        store.add_claim(claim("c-1"))
        store.add_claim(claim("c-1"))
        assert len(store.claims_for_document("doc-1")) == 1


class TestFindingLedger:
    def test_append_only(self, store: EvidenceStore) -> None:
        f = finding()
        store.add_finding(f)
        store.replace_finding(f.challenge("maybe rounding", by="critic"))
        assert len(store.all_findings) == 2
        assert len(store.current_findings()) == 1

    def test_current_is_latest_version(self, store: EvidenceStore) -> None:
        f = finding()
        store.add_finding(f)
        store.replace_finding(f.challenge("x", by="critic"))
        assert store.current_findings()[0].status is FindingStatus.CHALLENGED

    def test_only_confirmed_reach_memo(self, store: EvidenceStore) -> None:
        a = finding("f-1")
        store.add_finding(a)
        store.replace_finding(a.challenge("x", by="critic").confirm(by="critic"))
        b = finding("f-2")
        store.add_finding(b)
        store.replace_finding(b.challenge("y", by="critic").retract("no", by="critic"))
        confirmed = store.confirmed_findings()
        assert len(confirmed) == 1
        assert confirmed[0].finding_id == "f-1"

    def test_confirmed_sorted_by_severity(self, store: EvidenceStore) -> None:
        for fid, sev in (("f-1", Severity.LOW), ("f-2", Severity.CRITICAL)):
            f = Finding(
                finding_id=fid,
                finding_type=FindingType.ARITHMETIC,
                severity=sev,
                title="t",
                description="d",
                evidence=(span(),),
            )
            store.add_finding(f)
            store.replace_finding(f.challenge("x", by="c").confirm(by="c"))
        assert store.confirmed_findings()[0].severity is Severity.CRITICAL


class TestPersistence:
    def test_round_trip(self, tmp_path: Path) -> None:
        root = tmp_path / "run"
        a = EvidenceStore(root)
        a.add_claim(claim())
        a.add_finding(finding())
        a.mark_processed("doc-1")
        a.save()

        b = EvidenceStore(root)
        b.load()
        assert len(b.claims) == 1
        assert len(b.all_findings) == 1
        assert b.is_processed("doc-1")

    def test_missing_files_are_empty(self, tmp_path: Path) -> None:
        store = EvidenceStore(tmp_path / "empty")
        store.load()
        assert store.claims == ()

    def test_corrupt_file_does_not_raise(self, tmp_path: Path) -> None:
        root = tmp_path / "run"
        root.mkdir(parents=True)
        (root / "claims.json").write_text("{ this is not json")
        store = EvidenceStore(root)
        store.load()
        assert store.claims == ()


class TestCheckpointing:
    def test_processed_tracking(self, store: EvidenceStore) -> None:
        assert not store.is_processed("doc-1")
        store.mark_processed("doc-1")
        assert store.is_processed("doc-1")