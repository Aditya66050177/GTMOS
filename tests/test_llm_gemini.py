"""Tests for LLMService Gemini live-provider path (mocked at the SDK level)."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel
from typing import List

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ai.llm import LLMService


# ---- Tiny schemas for testing ----

class SimpleSchema(BaseModel):
    name: str
    score: float

class ListSchema(BaseModel):
    items: List[str]


# ---- Tests ----

class TestGeminiMocked:
    """All tests monkey-patch _call_gemini so no real API call is made."""

    def test_gemini_structured_output(self):
        """Valid JSON from Gemini is validated through Pydantic and returned."""
        expected = {"name": "Acme Corp", "score": 87.5}

        svc = LLMService(mode="live", api_key="test-key-never-real",
                         provider="gemini", model="gemini-2.0-flash")

        with patch.object(svc, "_call_gemini", return_value=json.dumps(expected)):
            result = svc.generate_structured("Score Acme Corp", SimpleSchema)

        assert isinstance(result, SimpleSchema)
        assert result.name == "Acme Corp"
        assert result.score == 87.5

    def test_gemini_retry_on_bad_json(self):
        """First call returns garbage, second call returns valid JSON -> success."""
        good = json.dumps({"name": "Retry Corp", "score": 10.0})

        svc = LLMService(mode="live", api_key="test-key-never-real",
                         provider="gemini", model="gemini-2.0-flash")

        with patch.object(svc, "_call_gemini", side_effect=["NOT JSON {{{", good]):
            result = svc.generate_structured("Score Retry Corp", SimpleSchema)

        assert result.name == "Retry Corp"

    def test_gemini_fails_after_two_bad(self):
        """Two consecutive bad responses raise RuntimeError."""
        svc = LLMService(mode="live", api_key="test-key-never-real",
                         provider="gemini", model="gemini-2.0-flash")

        with patch.object(svc, "_call_gemini", side_effect=["NOT JSON", '{"wrong_field": 1}']):
            with pytest.raises(RuntimeError, match="Failed to generate valid"):
                svc.generate_structured("bad prompt", SimpleSchema)

    def test_gemini_latency_and_tokens_recorded(self):
        """After a successful call, latency_ms and token counts are set."""
        svc = LLMService(mode="live", api_key="test-key-never-real",
                         provider="gemini", model="gemini-2.0-flash")

        resp_json = json.dumps({"name": "Metrics Corp", "score": 5.0})

        def fake_gemini(prompt, schema):
            svc.last_latency_ms = 123.4
            svc.last_prompt_tokens = 15
            svc.last_candidates_tokens = 25
            svc.last_total_tokens = 40
            return resp_json

        with patch.object(svc, "_call_gemini", side_effect=fake_gemini):
            svc.generate_structured("prompt", SimpleSchema)

        assert svc.last_latency_ms == 123.4
        assert svc.last_prompt_tokens == 15
        assert svc.last_candidates_tokens == 25
        assert svc.last_total_tokens == 40

    def test_no_api_key_raises(self):
        """Live mode with empty key raises ValueError."""
        svc = LLMService(mode="live", api_key="", provider="gemini")
        with pytest.raises(ValueError, match="LLM_API_KEY is not set"):
            svc.generate_structured("prompt", SimpleSchema)

    def test_unsupported_provider_raises(self):
        """Unknown provider raises NotImplementedError."""
        svc = LLMService(mode="live", api_key="key", provider="openai")
        with pytest.raises(NotImplementedError, match="Unsupported LLM_PROVIDER"):
            svc.generate_structured("prompt", SimpleSchema)

    def test_mock_mode_unchanged(self):
        """Mock mode still works and returns schema-valid data."""
        svc = LLMService(mode="mock")
        result = svc.generate_structured("anything", SimpleSchema)
        assert isinstance(result, SimpleSchema)
        assert isinstance(result.name, str)
        assert isinstance(result.score, float)

    def test_rate_limit_delay_exists(self):
        """The GEMINI_CALL_DELAY_SECS constant is defined and positive."""
        from app.ai.llm import GEMINI_CALL_DELAY_SECS
        assert GEMINI_CALL_DELAY_SECS > 0

    def test_provider_and_model_default(self):
        """LLMService picks up provider/model from settings by default."""
        svc = LLMService(mode="mock")
        assert svc.provider == "gemini"
        assert "gemini" in svc.model.lower()
