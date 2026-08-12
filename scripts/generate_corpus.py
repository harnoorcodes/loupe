"""Render the synthetic data room to PDF and DOCX.

Usage:
    python scripts/generate_corpus.py
    python scripts/generate_corpus.py --out data/synthetic
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docx import Document as DocxDocument
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from loupe.corpus.content import ALL_DOCUMENTS, PLANTED_DEFECTS, DocSpec


def write_pdf(spec: DocSpec, out_dir: Path) -> Path:
    """Render a document spec to PDF."""
    path = out_dir / spec.filename
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=spec.title)
    flow: list[object] = [Paragraph(spec.title, styles["Heading1"]), Spacer(1, 12)]
    for para in spec.paragraphs:
        flow.append(Paragraph(para, styles["BodyText"]))
        flow.append(Spacer(1, 8))
    doc.build(flow)
    return path


def write_docx(spec: DocSpec, out_dir: Path) -> Path:
    """Render a document spec to DOCX."""
    path = out_dir / spec.filename
    docx = DocxDocument()
    docx.add_heading(spec.title, level=1)
    for para in spec.paragraphs:
        docx.add_paragraph(para)
    docx.save(str(path))
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the synthetic data room")
    parser.add_argument("--out", default="data/synthetic", type=Path)
    args = parser.parse_args()

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for spec in ALL_DOCUMENTS:
        if spec.filename.endswith(".pdf"):
            path = write_pdf(spec, out_dir)
        elif spec.filename.endswith(".docx"):
            path = write_docx(spec, out_dir)
        else:
            raise ValueError(f"unsupported extension: {spec.filename}")
        written.append(path.name)
        print(f"  wrote {path}")

    truth_path = out_dir / "ground_truth.json"
    truth_path.write_text(
        json.dumps(
            {
                "documents": written,
                "defects": [d._asdict() for d in PLANTED_DEFECTS],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  wrote {truth_path}")
    print(f"\n{len(written)} documents, {len(PLANTED_DEFECTS)} planted defects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())