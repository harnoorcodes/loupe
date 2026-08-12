"""Typed application settings loaded from environment variables.

Every runtime knob lives here. Nothing elsewhere in the codebase reads
os.getenv directly -- that keeps configuration auditable in one place and
means a bad value fails loudly at startup instead of silently at call time.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Tier(StrEnum):
    """Gemini billing tier.

    Matters because the free tier's data-use terms differ from paid. Real
    deal documents must never be sent on a free-tier key.
    """

    FREE = "free"
    PAID = "paid"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    """Application configuration, validated at import time."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # --- Provider ---------------------------------------------------------
    gemini_api_key: str = Field(min_length=10)
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_tier: Tier = Tier.FREE

    # --- Model routing ----------------------------------------------------
    # Logical roles, not hardcoded IDs. Cheap model for high-volume mechanical
    # work, strong model for reasoning. Retiring a model is a .env edit.
    model_extraction: str = "gemini-3.5-flash"
    model_reasoning: str = "gemini-3.5-flash"
    model_critic: str = "gemini-3.5-flash"

    # --- Safety rails -----------------------------------------------------
    allow_real_documents: bool = False
    max_documents_per_run: int = Field(default=250, gt=0)
    max_tokens_per_run: int = Field(default=2_000_000, gt=0)

    # --- Observability ----------------------------------------------------
    log_level: LogLevel = LogLevel.INFO
    log_json: bool = False

    # --- Paths ------------------------------------------------------------
    data_dir: Path = PROJECT_ROOT / "data"

    @field_validator("gemini_api_key")
    @classmethod
    def _reject_placeholder(cls, v: str) -> str:
        """Catch an unedited .env before it becomes a confusing 401."""
        if "paste_your" in v.lower() or v.strip() != v:
            raise ValueError(
                "GEMINI_API_KEY looks wrong: it is still the placeholder, or "
                "has surrounding whitespace. Check .env -- no quotes, no spaces."
            )
        return v

    def assert_safe_for_real_data(self) -> None:
        """Guard against sending confidential documents on a free-tier key.

        Threat model T-2. Free-tier data-use terms differ from paid; this
        makes that a runtime error rather than a policy nobody reads.
        """
        if self.allow_real_documents and self.gemini_tier is Tier.FREE:
            raise RuntimeError(
                "Refusing to process real documents on a free-tier key. "
                "Set GEMINI_TIER=paid, or ALLOW_REAL_DOCUMENTS=false to use "
                "synthetic data only."
            )


settings = Settings()  # type: ignore[call-arg]