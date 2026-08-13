"""Command-line entry point.

Usage:
    python -m loupe.cli check
    python -m loupe.cli extract [--docs DIR] [--out DIR] [--limit N]
    python -m loupe.cli detect  [--run DIR] [--docs DIR] [--fresh]
    python -m loupe.cli memo    [--run DIR] [--docs DIR] [--out FILE]
    python -m loupe.cli score   [--run DIR] [--docs DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from agents import Agent, Runner

from loupe.agents import approval, critic
from loupe.agents.extractor import extract_corpus
from loupe.config.settings import settings
from loupe.detect import arithmetic, gaps, temporal, tension
from loupe.eval import render as render_score
from loupe.eval import score as score_run
from loupe.ingestion import load_directory
from loupe.llm.provider import ModelRole, describe_routing, get_model
from loupe.models.finding import Finding, FindingStatus
from loupe.observability.logging import configure_logging, get_logger
from loupe.report import memo
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)


def _open_store(run_dir: Path, docs_dir: Path) -> EvidenceStore:
    """Load the store and register every document in the corpus."""
    store = EvidenceStore(run_dir)
    store.load()
    for doc in load_directory(docs_dir):
        store.add_document(doc)
    return store


async def cmd_check() -> int:
    """Print resolved config and confirm a live model call works."""
    print("\n=== Configuration ===")
    print(f"  tier              : {settings.gemini_tier.value}")
    print(f"  api key           : ...{settings.gemini_api_key[-4:]}")
    print(f"  real documents    : {settings.allow_real_documents}")

    print("\n=== Model routing ===")
    for role, model_id in describe_routing().items():
        print(f"  {role:<12} -> {model_id}")

    print("\n=== Safety check ===")
    try:
        settings.assert_safe_for_real_data()
        print("  OK: tier and data policy are consistent")
    except RuntimeError as exc:
        print(f"  BLOCKED: {exc}")
        return 1

    print("\n=== Live call ===")
    try:
        agent = Agent(
            name="Config check agent",
            instructions="Reply with exactly the word: READY",
            model=get_model(ModelRole.REASONING),
        )
        result = await Runner.run(agent, "Report status.")
        print(f"  model replied: {result.final_output!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        return 1

    print("\nAll checks passed.\n")
    return 0


async def cmd_extract(docs_dir: Path, out_dir: Path, limit: int | None) -> int:
    """Ingest documents and extract claims into the evidence store."""
    settings.assert_safe_for_real_data()

    print(f"\nLoading documents from {docs_dir}")
    documents = load_directory(docs_dir)
    if limit:
        documents = documents[:limit]

    readable = [d for d in documents if d.is_readable]
    print(f"  {len(documents)} documents, {len(readable)} readable")
    for doc in documents:
        flag = "ok " if doc.is_readable else "SKIP"
        print(f"    [{flag}] {doc.filename} ({len(doc.blocks)} blocks)")

    store = EvidenceStore(out_dir)
    store.load()
    for doc in documents:
        store.add_document(doc)

    print("\nExtracting claims...")
    started = time.monotonic()
    new_claims = await extract_corpus(documents, store)
    store.save()

    print(f"\n  {new_claims} new claims in {time.monotonic() - started:.1f}s")
    print(f"  store now holds {len(store.claims)} claims")

    subjects = store.subjects()[:8]
    if subjects:
        print("\n  Most-referenced entities:")
        for subject in subjects:
            print(f"    {len(store.claims_about(subject)):>3}  {subject}")

    print()
    return 0


async def cmd_detect(
    run_dir: Path, docs_dir: Path, interactive: bool, fresh: bool
) -> int:
    """Detect, adversarially review, and gate findings."""
    settings.assert_safe_for_real_data()

    if fresh:
        ledger = run_dir / "findings.json"
        ledger.unlink(missing_ok=True)
        print(f"\nCleared previous findings from {ledger}")

    store = _open_store(run_dir, docs_dir)

    if not store.claims:
        print(f"\nNo claims in {run_dir}. Run 'extract' first.\n")
        return 1

    print(f"\n{len(store.claims)} claims from {len(store.documents)} documents")

    proposed: list[Finding] = []

    print("\n--- Arithmetic (no model) ---")
    found = arithmetic.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed")

    print("\n--- Temporal (no model) ---")
    found = temporal.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed")

    print("\n--- Gap audit (no model) ---")
    found = gaps.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed")

    print("\n--- Cross-document tension (model) ---")
    started = time.monotonic()
    found = await tension.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed in {time.monotonic() - started:.1f}s")

    print(f"\n--- Adversarial review of {len(proposed)} findings (model) ---")
    started = time.monotonic()
    reviewed = await critic.review_all(proposed, store)
    confirmed = [f for f in reviewed if f.status is FindingStatus.CONFIRMED]
    retracted = [f for f in reviewed if f.status is FindingStatus.RETRACTED]
    print(
        f"  {len(confirmed)} confirmed, {len(retracted)} retracted "
        f"in {time.monotonic() - started:.1f}s"
    )
    for finding in retracted:
        print(f"    withdrawn: {finding.title}")

    reviewed = approval.gate(reviewed, interactive=interactive)

    for finding in proposed:
        store.add_finding(finding)
    for finding in reviewed:
        store.replace_finding(finding)
    store.save()

    final = store.confirmed_findings()
    print(f"\n=== {len(final)} confirmed findings ===\n")
    for finding in final:
        scope = "CROSS-DOC " if finding.is_cross_document else "single-doc"
        print(f"[{finding.severity.value.upper():<8}] [{scope}] {finding.title}")
        for span in finding.all_spans[:3]:
            print(f'    {span.citation()}  "{span.text[:60]}"')
        print()

    return 0


def cmd_memo(run_dir: Path, docs_dir: Path, out_path: Path) -> int:
    """Write the findings memo."""
    store = _open_store(run_dir, docs_dir)
    if not store.confirmed_findings():
        print("\nNo confirmed findings. Run 'detect' first.\n")
        return 1

    path = memo.write(store, out_path)
    print(f"\nMemo written to {path}")
    print(f"  {len(store.confirmed_findings())} findings included\n")
    return 0


def cmd_score(run_dir: Path, docs_dir: Path) -> int:
    """Score the run against the planted defects."""
    store = _open_store(run_dir, docs_dir)
    card = score_run(store.confirmed_findings())
    print()
    print(render_score(card))
    return 0


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="loupe")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify configuration and provider access")

    extract = sub.add_parser("extract", help="ingest documents and extract claims")
    extract.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    extract.add_argument("--out", type=Path, default=Path("data/run"))
    extract.add_argument("--limit", type=int, default=None)

    detect = sub.add_parser("detect", help="find and review problems")
    detect.add_argument("--run", type=Path, default=Path("data/run"))
    detect.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    detect.add_argument("--no-approval", action="store_true")
    detect.add_argument(
        "--fresh", action="store_true", help="clear previous findings first"
    )

    memo_cmd = sub.add_parser("memo", help="write the findings memo")
    memo_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    memo_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    memo_cmd.add_argument("--out", type=Path, default=Path("data/memo.md"))

    score_cmd = sub.add_parser("score", help="score against planted defects")
    score_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    score_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))

    args = parser.parse_args()

    if args.command == "check":
        return asyncio.run(cmd_check())
    if args.command == "extract":
        return asyncio.run(cmd_extract(args.docs, args.out, args.limit))
    if args.command == "detect":
        return asyncio.run(
            cmd_detect(
                args.run,
                args.docs,
                interactive=not args.no_approval,
                fresh=args.fresh,
            )
        )
    if args.command == "memo":
        return cmd_memo(args.run, args.docs, args.out)
    if args.command == "score":
        return cmd_score(args.run, args.docs)
    return 2


if __name__ == "__main__":
    sys.exit(main())