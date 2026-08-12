"""Tests for settings and model routing.

None of these hit the network. Fast tests get run; slow ones get skipped.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from loupe.config.settings import LogLevel, Settings, Tier
from loupe.llm.provider import ModelRole, describe_routing
from loupe.observability.logging import _redact


def _make(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "gemini_api_key": "AIzaSyTESTKEY1234567890",
        "gemini_tier": Tier.FREE,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


class TestSettings:
    def test_defaults_are_sane(self) -> None:
        s = _make()
        assert s.gemini_tier is Tier.FREE
        assert s.allow_real_documents is False
        assert s.log_level is LogLevel.INFO

    def test_placeholder_key_rejected(self) -> None:
        with pytest.raises(ValidationError, match="placeholder"):
            _make(gemini_api_key="paste_your_key_here")

    def test_whitespace_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make(gemini_api_key="  AIzaSyTESTKEY1234567890  ")

    def test_short_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _make(gemini_api_key="abc")

    def test_settings_are_immutable(self) -> None:
        s = _make()
        with pytest.raises(ValidationError):
            s.log_level = LogLevel.DEBUG  # type: ignore[misc]


class TestSafetyRail:
    def test_free_tier_blocks_real_documents(self) -> None:
        s = _make(gemini_tier=Tier.FREE, allow_real_documents=True)
        with pytest.raises(RuntimeError, match="free-tier"):
            s.assert_safe_for_real_data()

    def test_paid_tier_allows_real_documents(self) -> None:
        s = _make(gemini_tier=Tier.PAID, allow_real_documents=True)
        s.assert_safe_for_real_data()

    def test_free_tier_fine_for_synthetic(self) -> None:
        s = _make(gemini_tier=Tier.FREE, allow_real_documents=False)
        s.assert_safe_for_real_data()


class TestRouting:
    def test_every_role_resolves(self) -> None:
        routing = describe_routing()
        assert set(routing) == {r.value for r in ModelRole}
        assert all(routing.values())


class TestRedaction:
    def test_document_text_is_redacted(self) -> None:
        out = _redact(None, "info", {"doc_id": "d-1", "text": "confidential"})
        assert out["doc_id"] == "d-1"
        assert "confidential" not in str(out["text"])

    def test_api_key_is_redacted(self) -> None:
        out = _redact(None, "info", {"api_key": "AIzaSySECRET"})
        assert "AIzaSySECRET" not in str(out["api_key"])