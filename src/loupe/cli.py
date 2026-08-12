"""Command-line entry point.

Usage:
    python -m loupe.cli check
"""

from __future__ import annotations

import asyncio
import sys

from agents import Agent, Runner

from loupe.config.settings import settings
from loupe.llm.provider import ModelRole, describe_routing, get_model
from loupe.observability.logging import configure_logging, get_logger

log = get_logger(__name__)


async def check() -> int:
    """Print resolved config and confirm a live model call works."""
    configure_logging()

    print("\n=== Configuration ===")
    print(f"  tier              : {settings.gemini_tier.value}")
    print(f"  base url          : {settings.gemini_base_url}")
    print(f"  api key           : ...{settings.gemini_api_key[-4:]}")
    print(f"  real documents    : {settings.allow_real_documents}")
    print(f"  max documents/run : {settings.max_documents_per_run}")
    print(f"  log level         : {settings.log_level.value}")

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
    except Exception as exc:
        print(f"  FAILED: {type(exc).__name__}: {exc}")
        return 1

    print("\nAll checks passed.\n")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] != "check":
        print("usage: python -m loupe.cli check")
        return 2
    return asyncio.run(check())


if __name__ == "__main__":
    sys.exit(main())