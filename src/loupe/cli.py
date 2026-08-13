"""Command-line entry point.

Usage:
    python -m loupe.cli check
    python -m loupe.cli extract [--docs DIR] [--out DIR] [--limit N]
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
from loupe.ingestion import load_directory
from loupe.llm.provider import ModelRole, describe_routing, get_model
from loupe.models.finding import Finding, FindingStatus
from loupe.observability.logging import configure_logging, get_logger
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)


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
    count = await extract_corpus(documents, store)
    elapsed = time.monotonic() - started

    store.save()

    print(f"\n  {count} claims extracted in {elapsed:.1f}s")
    print(f"  store: {store.stats()}")

    subjects = store.subjects()[:8]
    if subjects:
        print("\n  Most-referenced subjects:")
        for subject in subjects:
            n = len(store.claims_about(subject))
            print(f"    {n:>3}  {subject}")

    print()
    return 0


async def cmd_detect(
    run_dir: Path, docs_dir: Path, interactive: bool = True
) -> int:
    """Detect, adversarially review, and gate findings."""
    settings.assert_safe_for_real_data()

    store = EvidenceStore(run_dir)
    store.load()
    for doc in load_directory(docs_dir):
        store.add_document(doc)

    if not store.claims:
        print(f"\nNo claims in {run_dir}. Run 'extract' first.\n")
        return 1

    print(f"\n{len(store.claims)} claims from {len(store.documents)} documents")

    proposed: list[Finding] = []

    print("\n--- Arithmetic (deterministic) ---")
    found = arithmetic.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed")

    print("\n--- Temporal (deterministic) ---")
    found = temporal.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed")

    print("\n--- Gap audit (deterministic) ---")
    found = gaps.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed")

    print("\n--- Cross-document tension (LLM) ---")
    started = time.monotonic()
    found = await tension.detect(store)
    proposed.extend(found)
    print(f"  {len(found)} proposed in {time.monotonic() - started:.1f}s")

    print(f"\n--- Adversarial review of {len(proposed)} findings (LLM) ---")
    started = time.monotonic()
    reviewed = await critic.review_all(proposed, store)
    confirmed = [f for f in reviewed if f.status is FindingStatus.CONFIRMED]
    retracted = [f for f in reviewed if f.status is FindingStatus.RETRACTED]
    print(
        f"  {len(confirmed)} confirmed, {len(retracted)} retracted "
        f"in {time.monotonic() - started:.1f}s"
    )

    for finding in retracted:
        print(f"    RETRACTED: {finding.title}")
        print(f"      because: {finding.challenge_reason[:150]}")

    reviewed = approval.gate(reviewed, interactive=interactive)

    for finding in proposed:
        store.add_finding(finding)
    for finding in reviewed:
        store.replace_finding(finding)
    store.save()

    final = store.confirmed_findings()
    print(f"\n=== {len(final)} confirmed findings ===\n")
    for finding in final:
        marker = "CROSS-DOC" if finding.is_cross_document else "single-doc"
        print(f"[{finding.severity.value.upper():<8}] [{marker}] {finding.title}")
        print(f"  type   : {finding.finding_type.value}")
        print(f"  raised : {finding.raised_by}")
        print(f"  {finding.description[:240]}")
        for span in finding.all_spans[:3]:
            print(f'    cite: {span.citation()} "{span.text[:60]}"')
        if finding.challenge_reason:
            print(f"    critic objected: {finding.challenge_reason[:120]}")
        print()

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

    detect_cmd = sub.add_parser("detect", help="find contradictions in the claim graph")
    detect_cmd.add_argument("--run", type=Path, default=Path("data/run"))
    detect_cmd.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    detect_cmd.add_argument(
        "--no-approval", action="store_true", help="skip the human approval gate"
    )

    args = parser.parse_args()

    if args.command == "check":
        return asyncio.run(cmd_check())
    if args.command == "extract":
        return asyncio.run(cmd_extract(args.docs, args.out, args.limit))
    if args.command == "detect":
        return asyncio.run(
            cmd_detect(args.run, args.docs, interactive=not args.no_approval)
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())