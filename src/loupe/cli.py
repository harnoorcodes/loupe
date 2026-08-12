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

from loupe.agents.extractor import extract_corpus
from loupe.config.settings import settings
from loupe.ingestion import load_directory
from loupe.llm.provider import ModelRole, describe_routing, get_model
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


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="loupe")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="verify configuration and provider access")

    extract = sub.add_parser("extract", help="ingest documents and extract claims")
    extract.add_argument("--docs", type=Path, default=Path("data/synthetic"))
    extract.add_argument("--out", type=Path, default=Path("data/run"))
    extract.add_argument("--limit", type=int, default=None)

    args = parser.parse_args()

    if args.command == "check":
        return asyncio.run(cmd_check())
    if args.command == "extract":
        return asyncio.run(cmd_extract(args.docs, args.out, args.limit))
    return 2


if __name__ == "__main__":
    sys.exit(main())