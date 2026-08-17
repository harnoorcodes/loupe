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
from decimal import Decimal
from pathlib import Path

from agents import Agent, Runner

from loupe.agents import approval, classifier, critic, materiality
from loupe.agents.extractor import extract_corpus
from loupe.config.settings import settings
from loupe.detect import adjudicate, arithmetic, gaps, pairs, temporal, tension
from loupe.eval import ablation
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
    run_dir: Path,
    docs_dir: Path,
    interactive: bool,
    fresh: bool,
    deal_value: Decimal,
) -> int:
    """Classify, detect, review, score, and gate findings."""
    settings.assert_safe_for_real_data()

    if fresh:
        (run_dir / "findings.json").unlink(missing_ok=True)
        print("\nCleared previous findings")

    store = EvidenceStore(run_dir)
    store.load()

    print("\n--- Document classification (model) ---")
    documents = await classifier.classify_all(load_directory(docs_dir))
    for doc in documents:
        store.add_document(doc)
    for doc in documents:
        print(f"  {doc.filename:<36} {doc.document_type.value}")

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

    print("\n--- Targeted pair analysis (model) ---")
    started = time.monotonic()
    candidates = pairs.generate(store)
    print(f"  {len(candidates)} candidate pairs from deterministic rules")
    found = await adjudicate.adjudicate(candidates)
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

    print(f"\n--- Materiality scoring of {len(confirmed)} findings (model) ---")
    scored = await materiality.score_all(confirmed, deal_value)
    quantified = [f for f in scored if f.materiality is not None]
    print(f"  {len(quantified)} of {len(scored)} quantified")

    scored_by_id = {f.finding_id: f for f in scored}
    reviewed = [scored_by_id.get(f.finding_id, f) for f in reviewed]

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
        money = (
            f"  ~{finding.materiality_currency.value} {finding.materiality:,.0f}"
            if finding.materiality is not None
            and finding.materiality_currency is not None
            else ""
        )
        print(
            f"[{finding.severity.value.upper():<8}] [{scope}] "
            f"{finding.title}{money}"
        )
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


def cmd_pairs(run_dir: Path, docs_dir: Path) -> int:
    """Show candidate pairs without calling any model.

    Candidate generation is deterministic and free, so the pairs the system
    would spend money adjudicating can be inspected first.
    """
    store = _open_store(run_dir, docs_dir)
    if not store.claims:
        print(f"\nNo claims in {run_dir}. Run 'extract' first.\n")
        return 1

    candidates = pairs.generate(store)
    counts = pairs.summarise(candidates)

    print(f"\n{len(candidates)} candidate pairs from {len(store.claims)} claims\n")
    for strategy, count in sorted(counts.items()):
        print(f"  {strategy:<24} {count}")

    print()
    for index, pair in enumerate(candidates, start=1):
        print(f"{index:>3}. [{pair.strategy}]")
        print(f"     {pair.reason[:150]}")
        print(f"     A ({pair.claim_a.document_id}): {pair.claim_a.raw_text[:90]}")
        print(f"     B ({pair.claim_b.document_id}): {pair.claim_b.raw_text[:90]}")
        print()

    print(f"Adjudicating these would cost roughly "
          f"{max(1, len(candidates) // 6)} model calls.\n")
    return 0


async def cmd_ablate(run_dir: Path, docs_dir: Path, out_path: Path) -> int:
    """Run the ablation study and write the report."""
    settings.assert_safe_for_real_data()

    store = _open_store(run_dir, docs_dir)
    if not store.claims:
        print(f"\nNo claims in {run_dir}. Run 'extract' first.\n")
        return 1

    print(f"\nRunning {len(ablation.CONFIGURATIONS)} configurations over "
        f"{len(store.claims)} claims.")
    print("Most configurations are subsets of the full run, so their model "
        "calls are already cached.\n")

    started = time.monotonic()
    results = await ablation.run_all(store)
    elapsed = time.monotonic() - started

    report = ablation.render(results)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    print(report)
    print(ablation.summarise_contributions(results))
    print(f"\nCompleted in {elapsed:.1f}s. Written to {out_path}\n")
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
    detect.add_argument(
        "--deal-value",
        type=Decimal,
        default=Decimal("25000000"),
        help="transaction value used as the materiality reference",
    )

    memo_cmd = sub.add_parser("memo", help="write the findings memo")
    memo_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    memo_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    memo_cmd.add_argument("--out", type=Path, default=Path("data/memo.md"))

    score_cmd = sub.add_parser("score", help="score against planted defects")
    score_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    score_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    pairs_cmd = sub.add_parser("pairs", help="show candidate pairs, no model calls")
    pairs_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    pairs_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    ablate_cmd = sub.add_parser("ablate", help="measure what each component contributes")
    ablate_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    ablate_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    ablate_cmd.add_argument("--out", type=Path, default=Path("data/ablation.md"))

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
                deal_value=args.deal_value,
            )
        )
    if args.command == "memo":
        return cmd_memo(args.run, args.docs, args.out)
    if args.command == "score":
        return cmd_score(args.run, args.docs)
    if args.command == "pairs":
        return cmd_pairs(args.run, args.docs)
    if args.command == "ablate":
        return asyncio.run(cmd_ablate(args.run, args.docs, args.out))
    return 2


if __name__ == "__main__":
    sys.exit(main())