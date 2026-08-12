"""Ingestion tests. Generates its own fixtures; no network, no API cost."""

from __future__ import annotations

from pathlib import Path

import pytest

from loupe.corpus.content import ALL_DOCUMENTS, PLANTED_DEFECTS
from loupe.ingestion import load_directory, load_document, page_for_offset
from loupe.models.document import DocumentType, ParseStatus
from loupe.models.span import Span, validate_span


@pytest.fixture(scope="module")
def corpus_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate the synthetic corpus once for the whole module."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from generate_corpus import write_docx, write_pdf

    out = tmp_path_factory.mktemp("corpus")
    for spec in ALL_DOCUMENTS:
        if spec.filename.endswith(".pdf"):
            write_pdf(spec, out)
        else:
            write_docx(spec, out)
    return out


class TestPageMapping:
    def test_offset_before_second_page(self) -> None:
        assert page_for_offset(50, (0, 100, 200)) == 1

    def test_offset_on_page_boundary(self) -> None:
        assert page_for_offset(100, (0, 100, 200)) == 2

    def test_offset_on_last_page(self) -> None:
        assert page_for_offset(250, (0, 100, 200)) == 3

    def test_empty_offsets_defaults_to_page_one(self) -> None:
        assert page_for_offset(0, ()) == 1


class TestClassification:
    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("cap_table.pdf", DocumentType.CAP_TABLE),
            ("financial_statements_2025.pdf", DocumentType.FINANCIAL_STATEMENT),
            ("contract_titanretail.pdf", DocumentType.CONTRACT),
            ("board_minutes_2024.pdf", DocumentType.BOARD_MINUTES),
            ("employment_ceo.docx", DocumentType.EMPLOYMENT_AGREEMENT),
            ("mystery.pdf", DocumentType.OTHER),
        ],
    )
    def test_classify(self, filename: str, expected: DocumentType) -> None:
        from loupe.ingestion import classify

        assert classify(filename) is expected


class TestPdfLoading:
    def test_loads_successfully(self, corpus_dir: Path) -> None:
        doc = load_document(corpus_dir / "cap_table.pdf")
        assert doc.parse_status is ParseStatus.OK
        assert doc.is_readable
        assert doc.page_count >= 1

    def test_produces_blocks(self, corpus_dir: Path) -> None:
        doc = load_document(corpus_dir / "cap_table.pdf")
        assert len(doc.blocks) >= 3

    def test_content_hash_present(self, corpus_dir: Path) -> None:
        doc = load_document(corpus_dir / "cap_table.pdf")
        assert len(doc.content_hash) == 16

    def test_key_text_survives_round_trip(self, corpus_dir: Path) -> None:
        doc = load_document(corpus_dir / "cap_table.pdf")
        assert "4,250,000" in doc.text
        assert "410,000" in doc.text


class TestDocxLoading:
    def test_loads_successfully(self, corpus_dir: Path) -> None:
        doc = load_document(corpus_dir / "employment_ceo.docx")
        assert doc.parse_status is ParseStatus.OK
        assert "Sarah Chen" in doc.text

    def test_single_page(self, corpus_dir: Path) -> None:
        doc = load_document(corpus_dir / "employment_ceo.docx")
        assert doc.page_count == 1


class TestSpanIntegrity:
    """The critical property: every generated span must validate."""

    def test_all_block_spans_validate(self, corpus_dir: Path) -> None:
        for doc in load_directory(corpus_dir):
            if not doc.is_readable:
                continue
            for block in doc.blocks:
                validate_span(block.span, doc.text)

    def test_span_page_within_document(self, corpus_dir: Path) -> None:
        for doc in load_directory(corpus_dir):
            if not doc.is_readable:
                continue
            for block in doc.blocks:
                assert 1 <= block.span.page <= max(doc.page_count, 1)

    def test_span_located_by_search_validates(self, corpus_dir: Path) -> None:
        """Spans derived by searching extracted text must validate.

        This is the pattern every extraction agent will follow: find the
        text, take its offsets, never compute them by hand.
        """
        doc = load_document(corpus_dir / "financial_statements_2025.pdf")
        needle = "43%"
        start = doc.text.find(needle)
        assert start != -1
        span = Span(
            document_id=doc.document_id,
            page=1,
            char_start=start,
            char_end=start + len(needle),
            text=needle,
        )
        validate_span(span, doc.text)


class TestFailureHandling:
    def test_unsupported_format(self, tmp_path: Path) -> None:
        bad = tmp_path / "notes.txt"
        bad.write_text("hello")
        doc = load_document(bad)
        assert doc.parse_status is ParseStatus.UNSUPPORTED_FORMAT
        assert not doc.is_readable

    def test_corrupt_pdf(self, tmp_path: Path) -> None:
        bad = tmp_path / "broken.pdf"
        bad.write_bytes(b"this is not a pdf")
        doc = load_document(bad)
        assert doc.parse_status is not ParseStatus.OK
        assert doc.parse_error

    def test_failure_does_not_raise(self, tmp_path: Path) -> None:
        bad = tmp_path / "broken.pdf"
        bad.write_bytes(b"\x00\x01\x02")
        load_document(bad)  # must not raise


class TestDirectoryLoading:
    def test_loads_all_documents(self, corpus_dir: Path) -> None:
        docs = load_directory(corpus_dir)
        assert len(docs) == len(ALL_DOCUMENTS)

    def test_deduplicates_by_content(self, corpus_dir: Path, tmp_path: Path) -> None:
        import shutil

        work = tmp_path / "dupes"
        work.mkdir()
        src = corpus_dir / "cap_table.pdf"
        shutil.copy(src, work / "cap_table.pdf")
        shutil.copy(src, work / "cap_table_copy.pdf")
        assert len(load_directory(work)) == 1


class TestPlantedDefects:
    """Every defect anchor must survive rendering and extraction.

    If an anchor cannot be found, the eval harness cannot score that defect.
    """

    def test_anchors_present_in_corpus(self, corpus_dir: Path) -> None:
        docs = {d.document_id: d for d in load_directory(corpus_dir)}
        for defect in PLANTED_DEFECTS:
            if defect.defect_type == "missing_document":
                continue
            corpus_text = " ".join(
                docs[Path(f).stem].text for f in defect.documents
            )
            for anchor in defect.anchors:
                assert anchor in corpus_text, (
                    f"{defect.defect_id}: anchor {anchor!r} did not survive "
                    f"round trip"
                )

    def test_missing_document_really_absent(self, corpus_dir: Path) -> None:
        names = {p.name for p in corpus_dir.iterdir()}
        assert not any("incentive_plan" in n for n in names)