"""Staged connectivity check for the OpenAI Agents SDK running on Gemini.

Each stage tests exactly one risk area and fails loudly on its own. Run this
before writing any project code -- if stage 4 fails, the architecture changes,
and you want to know that on day one rather than day nine.

Usage:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

PASS = "[PASS]"
FAIL = "[FAIL]"


def banner(stage: int, title: str) -> None:
    print(f"\n{'=' * 62}\nSTAGE {stage}: {title}\n{'=' * 62}")


async def stage_0_list_models() -> bool:
    """Confirm the key works and show which model IDs actually exist today.

    Model IDs churn fast. Never trust a tutorial (including mine) for the
    current name -- read it off this list.
    """
    banner(0, "Key is valid / which models exist")
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=API_KEY, base_url=GEMINI_BASE_URL)
        models = await client.models.list()
        names = sorted(m.id.replace("models/", "") for m in models.data)
        flash = [n for n in names if "flash" in n and "image" not in n]
        print(f"{PASS} Key accepted. {len(names)} models visible.")
        print("\n  Flash-family models (cheapest, use these):")
        for n in flash[:12]:
            marker = "  <-- your GEMINI_MODEL" if n == MODEL_NAME else ""
            print(f"    {n}{marker}")
        if MODEL_NAME not in names:
            print(f"\n  WARNING: '{MODEL_NAME}' is not in the list.")
            print("  Set GEMINI_MODEL in .env to one of the names above.")
        return True
    except Exception as exc:
        print(f"{FAIL} {type(exc).__name__}: {exc}")
        print("\n  Most likely: GEMINI_API_KEY is missing, wrong, or has a")
        print("  stray space/quote in .env. Regenerate at aistudio.google.com.")
        return False


async def stage_1_raw_call() -> bool:
    """Plain OpenAI SDK -> Gemini. Isolates the endpoint from the Agents SDK."""
    banner(1, "Raw OpenAI SDK talks to Gemini")
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=API_KEY, base_url=GEMINI_BASE_URL)
        resp = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        print(f"{PASS} Model replied: {resp.choices[0].message.content!r}")
        return True
    except Exception as exc:
        print(f"{FAIL} {type(exc).__name__}: {exc}")
        print("\n  If this is a 404, GEMINI_MODEL is wrong -- see stage 0.")
        return False


async def stage_2_agents_sdk() -> bool:
    """Agents SDK Runner on Gemini. Tests the Responses-vs-ChatCompletions fix."""
    banner(2, "Agents SDK Runner works on Gemini")
    try:
        from agents import (
            Agent,
            AsyncOpenAI,
            OpenAIChatCompletionsModel,
            Runner,
            set_tracing_disabled,
        )

        # Trap 2: traces upload to OpenAI and 401 without an OpenAI key.
        set_tracing_disabled(disabled=True)

        client = AsyncOpenAI(api_key=API_KEY, base_url=GEMINI_BASE_URL)
        # Trap 1: Gemini has no Responses API, so pin Chat Completions.
        model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

        agent = Agent(
            name="Smoke test agent",
            instructions="You are terse. Answer in under 10 words.",
            model=model,
        )
        result = await Runner.run(agent, "What is due diligence?")
        print(f"{PASS} Agent replied: {result.final_output!r}")
        return True
    except Exception as exc:
        print(f"{FAIL} {type(exc).__name__}: {exc}")
        print("\n  A 404 here means the SDK still tried the Responses API.")
        return False


async def stage_3_tool_calling() -> bool:
    """Function tools through Gemini. This is where adapter setups tend to break."""
    banner(3, "Tool calling works")
    try:
        from agents import (
            Agent,
            AsyncOpenAI,
            OpenAIChatCompletionsModel,
            Runner,
            function_tool,
            set_tracing_disabled,
        )

        set_tracing_disabled(disabled=True)

        @function_tool
        def get_share_count(company: str) -> int:
            """Return the issued share count on record for a company."""
            print(f"    -> tool actually executed with company={company!r}")
            return 4_250_000

        client = AsyncOpenAI(api_key=API_KEY, base_url=GEMINI_BASE_URL)
        model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

        agent = Agent(
            name="Tool test agent",
            instructions=(
                "You look up company data. You must use the get_share_count "
                "tool -- never guess a number from memory."
            ),
            model=model,
            tools=[get_share_count],
        )
        result = await Runner.run(agent, "How many shares has Acme Corp issued?")
        ok = "4,250,000" in result.final_output or "4250000" in result.final_output
        print(f"{PASS if ok else FAIL} Agent replied: {result.final_output!r}")
        if not ok:
            print("\n  Tool may not have run -- check for the '->' line above.")
        return ok
    except Exception as exc:
        print(f"{FAIL} {type(exc).__name__}: {exc}")
        return False


class Finding(BaseModel):
    """Minimal stand-in for the real Finding model built in a later milestone."""

    risk_type: str = Field(description="Short category, e.g. ARITHMETIC")
    severity: str = Field(description="One of: LOW, MEDIUM, HIGH, CRITICAL")
    summary: str = Field(description="One sentence describing the risk")
    confidence: float = Field(ge=0.0, le=1.0)


async def stage_4_structured_output() -> bool:
    """Typed output via Pydantic. THE critical stage -- the design assumes this."""
    banner(4, "Structured output works  <-- the important one")
    try:
        from agents import (
            Agent,
            AsyncOpenAI,
            OpenAIChatCompletionsModel,
            Runner,
            set_tracing_disabled,
        )

        set_tracing_disabled(disabled=True)

        client = AsyncOpenAI(api_key=API_KEY, base_url=GEMINI_BASE_URL)
        model = OpenAIChatCompletionsModel(model=MODEL_NAME, openai_client=client)

        agent = Agent(
            name="Structured output agent",
            instructions="You extract risks from text into the required schema.",
            model=model,
            output_type=Finding,
        )
        result = await Runner.run(
            agent,
            "The cap table lists 4,250,000 shares but the sum of individual "
            "grants is 4,310,000. Flag this.",
        )
        finding = result.final_output
        print(f"{PASS} Parsed into a typed object:")
        print(f"    risk_type  = {finding.risk_type}")
        print(f"    severity   = {finding.severity}")
        print(f"    summary    = {finding.summary}")
        print(f"    confidence = {finding.confidence}")
        return True
    except Exception as exc:
        print(f"{FAIL} {type(exc).__name__}: {exc}")
        print("\n  If this mentions 'response_format' or 'json_schema', Gemini")
        print("  rejected the strict schema. Not fatal -- we add a validate/")
        print("  repair/retry layer in a later milestone. Tell me if you see it.")
        return False


async def main() -> int:
    if not API_KEY:
        print(f"{FAIL} GEMINI_API_KEY is not set.")
        print("  Copy .env.example to .env and paste your key into it.")
        return 1

    print(f"Model under test: {MODEL_NAME}")
    print(f"Endpoint:         {GEMINI_BASE_URL}")

    stages = [
        ("List models", stage_0_list_models),
        ("Raw SDK call", stage_1_raw_call),
        ("Agents SDK", stage_2_agents_sdk),
        ("Tool calling", stage_3_tool_calling),
        ("Structured output", stage_4_structured_output),
    ]

    results: list[tuple[str, bool]] = []
    for label, fn in stages:
        results.append((label, await fn()))

    print(f"\n{'=' * 62}\nSUMMARY\n{'=' * 62}")
    for label, ok in results:
        print(f"  {PASS if ok else FAIL}  {label}")

    failed = [label for label, ok in results if not ok]
    if not failed:
        print("\nAll stages passed. The stack works. We can start building.")
        return 0
    print(f"\n{len(failed)} stage(s) failed: {', '.join(failed)}")
    print("Paste the full output above into the chat and I'll diagnose it.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))