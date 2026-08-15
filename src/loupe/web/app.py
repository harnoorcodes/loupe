"""Web interface for Loupe.

A thin layer over the existing pipeline. Nothing in the analysis changes:
the same functions the CLI calls are called here, in the same order.

Analysis runs as a background task and the browser polls for progress,
because a full cold run takes around a minute and a blocking request would
time out. Run state lives in memory, which is correct for a single-analyst
tool and would need replacing with a store for anything multi-user.

Citations carry the source filename and page number so the browser can open
the document at the right page. That matters more than it looks: the whole
premise of the system is that every claim is checkable, and a citation you
cannot click is an assertion rather than a demonstration.
"""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from loupe.agents import classifier, critic, materiality
from loupe.agents.extractor import extract_corpus
from loupe.config.settings import settings
from loupe.detect import arithmetic, gaps, temporal, tension
from loupe.eval import score as score_run
from loupe.ingestion import load_directory
from loupe.models.finding import Finding, FindingStatus
from loupe.observability.logging import configure_logging, get_logger
from loupe.report import memo
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
UPLOAD_ROOT = Path("data/uploads")
ALLOWED_SUFFIXES = {".pdf", ".docx"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

TOTAL_STAGES = 9
DEMO_RUNS: set[str] = set()

configure_logging()

app = FastAPI(title="Loupe", docs_url="/api/docs")


@dataclass
class RunState:
    """Progress and results for one analysis run."""

    run_id: str
    status: str = "pending"  # pending | running | done | failed
    stage: str = "Waiting to start"
    stage_index: int = 0
    log_lines: list[str] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    filenames: dict[str, str] = field(default_factory=dict)
    findings: list[dict[str, Any]] = field(default_factory=list)
    retracted: list[dict[str, Any]] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)
    score: dict[str, Any] | None = None
    error: str | None = None

    def note(self, stage: str, detail: str = "") -> None:
        """Record a stage transition, visible to the browser on next poll."""
        self.stage = stage
        self.stage_index = min(self.stage_index + 1, TOTAL_STAGES)
        self.log_lines.append(f"{stage}||{detail}")
        log.info("run stage", run_id=self.run_id, stage=stage, detail=detail)


RUNS: dict[str, RunState] = {}


def _finding_to_dict(finding: Finding, filenames: dict[str, str]) -> dict[str, Any]:
    """Serialise a finding for the browser, with clickable citations."""
    citations = []
    for span in finding.all_spans:
        citations.append(
            {
                "label": span.citation(),
                "quote": span.text[:300],
                "document_id": span.document_id,
                "filename": filenames.get(span.document_id, ""),
                "page": span.page,
            }
        )

    return {
        "id": finding.finding_id,
        "title": finding.title,
        "description": finding.description,
        "severity": finding.severity.value,
        "type": finding.finding_type.value.replace("_", " "),
        "raised_by": finding.raised_by.replace("_", " "),
        "cross_document": finding.is_cross_document,
        "materiality": (
            f"{finding.materiality_currency.value} {finding.materiality:,.0f}"
            if finding.materiality is not None
            and finding.materiality_currency is not None
            else None
        ),
        "objection": finding.challenge_reason,
        "citations": citations,
    }


async def run_pipeline(run_id: str, docs_dir: Path, deal_value: Decimal) -> None:
    """Execute the full analysis, updating run state as it goes.

    Mirrors cmd_detect in the CLI exactly. Any failure is recorded on the
    run rather than raised, so the browser shows a message instead of a
    dead poll.
    """
    state = RUNS[run_id]
    run_dir = docs_dir.parent / "run"

    try:
        state.status = "running"
        settings.assert_safe_for_real_data()

        state.note("Reading documents")
        documents = load_directory(docs_dir)
        if not documents:
            raise ValueError("No readable PDF or DOCX files were found.")

        state.note("Classifying documents", f"{len(documents)} files")
        documents = await classifier.classify_all(documents)
        state.filenames = {d.document_id: d.filename for d in documents}
        state.documents = [
            {
                "id": d.document_id,
                "name": d.filename,
                "type": d.document_type.value.replace("_", " "),
                "blocks": len(d.blocks),
                "pages": d.page_count,
                "readable": d.is_readable,
            }
            for d in documents
        ]

        store = EvidenceStore(run_dir)
        for doc in documents:
            store.add_document(doc)

        state.note("Extracting claims", "reading every document")
        await extract_corpus(documents, store)
        state.note("Claims extracted", f"{len(store.claims)} facts found")

        proposed: list[Finding] = []

        state.note("Reconciling numbers", "no model needed")
        proposed.extend(arithmetic.detect(store))
        proposed.extend(temporal.detect(store))
        proposed.extend(gaps.detect(store))

        state.note("Comparing across documents", "the important step")
        proposed.extend(await tension.detect(store))

        state.note("Adversarial review", f"attacking {len(proposed)} findings")
        reviewed = await critic.review_all(proposed, store)
        confirmed = [f for f in reviewed if f.status is FindingStatus.CONFIRMED]
        retracted = [f for f in reviewed if f.status is FindingStatus.RETRACTED]

        state.note(
            "Review complete",
            f"{len(confirmed)} survived, {len(retracted)} withdrawn",
        )

        state.note("Estimating financial impact")
        scored = await materiality.score_all(confirmed, deal_value)
        by_id = {f.finding_id: f for f in scored}
        reviewed = [by_id.get(f.finding_id, f) for f in reviewed]

        for finding in proposed:
            store.add_finding(finding)
        for finding in reviewed:
            store.replace_finding(finding)
        store.save()

        final = store.confirmed_findings()
        state.findings = [_finding_to_dict(f, state.filenames) for f in final]
        state.retracted = [
            {"title": f.title, "reason": f.challenge_reason or ""}
            for f in retracted
        ]
        state.stats = store.stats()

        memo.write(store, run_dir / "memo.md")

        card = score_run(final)
        if card.planted_count:
            state.score = {
                "detected": card.detected_count,
                "planted": card.planted_count,
                "noise": len(card.extra_noise),
                "total": card.total_findings,
            }

        state.note("Done")
        state.stage_index = TOTAL_STAGES
        state.status = "done"

    except Exception as exc:  # noqa: BLE001 - surfaced to the browser
        log.warning("run failed", run_id=run_id, error=str(exc)[:300])
        state.status = "failed"
        state.error = str(exc)[:500]
        state.note("Failed", str(exc)[:200])


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the single-page interface."""
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.post("/api/runs")
async def create_run(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    deal_value: str = "25000000",
) -> JSONResponse:
    """Accept uploaded documents and start an analysis run."""
    accepted = [
        f for f in files if Path(f.filename or "").suffix.lower() in ALLOWED_SUFFIXES
    ]
    if not accepted:
        raise HTTPException(400, "Upload at least one PDF or DOCX file.")
    if len(accepted) > settings.max_documents_per_run:
        raise HTTPException(
            400, f"Too many files. The limit is {settings.max_documents_per_run}."
        )

    run_id = uuid.uuid4().hex[:12]
    docs_dir = UPLOAD_ROOT / run_id / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    for upload in accepted:
        raw = await upload.read()
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, f"{upload.filename} is larger than 20 MB.")
        safe_name = Path(upload.filename or "unnamed").name
        (docs_dir / safe_name).write_bytes(raw)

    state = RunState(run_id=run_id)
    state.note("Uploaded", f"{len(accepted)} files received")
    RUNS[run_id] = state

    try:
        value = Decimal(deal_value)
    except Exception:  # noqa: BLE001
        value = Decimal("25000000")

    background.add_task(run_pipeline, run_id, docs_dir, value)
    return JSONResponse({"run_id": run_id})


@app.post("/api/runs/demo")
async def create_demo_run(background: BackgroundTasks) -> JSONResponse:
    """Start a run over the bundled synthetic corpus.

    Reads data/synthetic in place rather than copying it. Copying would give
    the documents new IDs, which changes every prompt, which misses the
    response cache and forces a full set of live model calls. Reading in
    place keeps the cache warm, so the demo run is instant and free.
    """
    source = Path("data/synthetic")
    if not source.exists():
        raise HTTPException(404, "Run 'python scripts/generate_corpus.py' first.")

    run_id = uuid.uuid4().hex[:12]
    state = RunState(run_id=run_id)
    state.note("Sample data room loaded", "10 documents")
    RUNS[run_id] = state
    DEMO_RUNS.add(run_id)

    background.add_task(run_pipeline, run_id, source, Decimal("25000000"))
    return JSONResponse({"run_id": run_id})


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> JSONResponse:
    """Return current progress and results for a run."""
    state = RUNS.get(run_id)
    if state is None:
        raise HTTPException(404, "Unknown run.")
    return JSONResponse(
        {
            "status": state.status,
            "stage": state.stage,
            "progress": round(100 * state.stage_index / TOTAL_STAGES),
            "log": state.log_lines,
            "documents": state.documents,
            "findings": state.findings,
            "retracted": state.retracted,
            "stats": state.stats,
            "score": state.score,
            "error": state.error,
        }
    )


@app.get("/api/runs/{run_id}/source/{filename}")
async def get_source(run_id: str, filename: str) -> FileResponse:
    """Serve a source document so a citation can be verified.

    This is what turns a citation from an assertion into something the
    reader can check in one click.
    """
    safe = Path(filename).name
    base = Path("data/synthetic") if run_id in DEMO_RUNS else UPLOAD_ROOT / run_id / "docs"
    path = base / safe
    if not path.exists():
        raise HTTPException(404, "Document not found.")
    media = "application/pdf" if path.suffix.lower() == ".pdf" else None
    return FileResponse(path, media_type=media, filename=safe)


@app.get("/api/runs/{run_id}/memo")
async def get_memo(run_id: str) -> HTMLResponse:
    """Return the generated memo as plain text."""
    base = Path("data") if run_id in DEMO_RUNS else UPLOAD_ROOT / run_id
    path = base / "run" / "memo.md"
    if not path.exists():
        raise HTTPException(404, "No memo has been generated for this run.")
    return HTMLResponse(path.read_text(encoding="utf-8"), media_type="text/plain")


def main() -> None:
    """Entry point: python -m loupe.web.app"""
    import uvicorn

    print("\n  Loupe running at http://127.0.0.1:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()