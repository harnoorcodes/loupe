"""Provider-agnostic model factory.

Agents ask for a ROLE ("give me the reasoning model"), never a model ID.
That indirection is what let us survive gemini-2.5-flash being retired
mid-setup, and it is what will let this project swap to OpenAI, Anthropic,
or a local model with a config change rather than a refactor.

Provider notes (from the Agents SDK docs on non-OpenAI providers):
  1. Gemini has no Responses API -> pin OpenAIChatCompletionsModel.
  2. Tracing uploads to OpenAI and 401s without an OpenAI key -> disabled.
  3. Some compatible providers stream tool-call deltas unreliably.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from agents import AsyncOpenAI, OpenAIChatCompletionsModel, set_tracing_disabled

from loupe.config.settings import settings
from loupe.observability.logging import get_logger

log = get_logger(__name__)

# Trap 2. Without this every run emits 401s from the trace exporter.
set_tracing_disabled(disabled=True)


class ModelRole(StrEnum):
    """What a model is being asked to do, independent of which model it is."""

    EXTRACTION = "extraction"  # high volume, mechanical, cheap
    REASONING = "reasoning"    # cross-document analysis, expensive
    CRITIC = "critic"          # adversarial review


_ROLE_TO_SETTING = {
    ModelRole.EXTRACTION: "model_extraction",
    ModelRole.REASONING: "model_reasoning",
    ModelRole.CRITIC: "model_critic",
}


@lru_cache(maxsize=1)
def get_client() -> AsyncOpenAI:
    """Return the shared async HTTP client pointed at the provider.

    Cached: one client, one connection pool, for the whole process.
    """
    log.debug("creating provider client", base_url=settings.gemini_base_url)
    return AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
    )


@lru_cache(maxsize=len(ModelRole))
def get_model(role: ModelRole) -> OpenAIChatCompletionsModel:
    """Return the model bound to a logical role.

    Args:
        role: What the caller needs the model for.

    Returns:
        A model instance an Agent can be constructed with.
    """
    model_id: str = getattr(settings, _ROLE_TO_SETTING[role])
    log.debug("resolving model", role=role.value, model_id=model_id)
    # Trap 1. Chat Completions, not Responses.
    return OpenAIChatCompletionsModel(model=model_id, openai_client=get_client())


def describe_routing() -> dict[str, str]:
    """Return the current role -> model mapping, for startup logging."""
    return {r.value: getattr(settings, _ROLE_TO_SETTING[r]) for r in ModelRole}