"""Shared agent infrastructure.

Three problems every agent hits, solved once here:

1. Rate limits. The free provider tier permits a limited number of requests
   per minute and per day. Concurrency is capped and 429s are retried with
   exponential backoff and jitter.

2. Malformed structured output. Provider schema enforcement is not strict,
   so a response can parse as JSON and still violate the model. The fix is
   validate, then re-prompt with the error, then retry -- never crash the
   run for one bad document.

3. Repeated identical requests. Responses are cached on disk by content
   hash, so re-running a pipeline costs nothing and produces identical
   output. This makes demos reproducible as well as free.
"""

from __future__ import annotations

import asyncio
import random
from typing import TypeVar

from agents import Agent, Runner
from pydantic import BaseModel, ValidationError

from loupe.llm import cache
from loupe.observability.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

MAX_CONCURRENT_CALLS = 1
MAX_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 5.0

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)


class AgentCallError(Exception):
    """Raised when an agent call fails after every retry."""


def _is_rate_limit(exc: Exception) -> bool:
    """Detect a rate-limit or quota error without depending on an exception type."""
    text = str(exc).lower()
    return "429" in text or "rate limit" in text or "resource_exhausted" in text


def _model_name(agent: Agent) -> str:
    """Best-effort model identifier, for the cache key."""
    model = getattr(agent, "model", None)
    return str(getattr(model, "model", model))


async def run_agent(
    agent: Agent,
    prompt: str,
    output_type: type[T],
    *,
    label: str = "agent",
    use_cache: bool = True,
) -> T:
    """Run an agent and return a validated typed result.

    Args:
        agent: A configured Agent with output_type set.
        prompt: The user-role input.
        output_type: Pydantic model the result must conform to.
        label: Identifier for logging.
        use_cache: Whether to read and write the on-disk response cache.

    Returns:
        The validated model instance.

    Raises:
        AgentCallError: If every attempt fails.
    """
    instructions = str(getattr(agent, "instructions", ""))
    key = cache.cache_key(instructions, prompt, _model_name(agent))

    if use_cache:
        cached = cache.read(key)
        if cached is not None:
            try:
                log.info("cache hit", label=label)
                return output_type.model_validate(cached)
            except ValidationError:
                log.debug("cached entry no longer matches schema", label=label)

    last_error: Exception | None = None
    current_prompt = prompt

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            async with _semaphore:
                result = await Runner.run(agent, current_prompt)

            output = result.final_output
            validated = (
                output
                if isinstance(output, output_type)
                else output_type.model_validate(output)
            )

            if use_cache:
                cache.write(key, validated.model_dump(mode="json"))

            return validated

        except ValidationError as exc:
            last_error = exc
            log.warning(
                "structured output invalid",
                label=label,
                attempt=attempt,
                error=str(exc)[:300],
            )
            current_prompt = (
                f"{prompt}\n\n"
                f"Your previous response did not match the required schema. "
                f"The validation error was:\n{str(exc)[:500]}\n\n"
                f"Return a response that satisfies the schema exactly."
            )

        except Exception as exc:  # noqa: BLE001 - provider raises broadly
            last_error = exc
            if _is_rate_limit(exc):
                delay = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                delay += random.uniform(0, 2)  # noqa: S311 - jitter, not crypto
                log.warning(
                    "rate limited, backing off",
                    label=label,
                    attempt=attempt,
                    delay=round(delay, 1),
                )
                await asyncio.sleep(delay)
            else:
                log.warning(
                    "agent call failed",
                    label=label,
                    attempt=attempt,
                    error=str(exc)[:300],
                )
                await asyncio.sleep(1.0)

    raise AgentCallError(
        f"{label} failed after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error