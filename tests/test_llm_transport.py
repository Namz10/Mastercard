"""In-process LLM transport tests (no paid provider)."""

from __future__ import annotations

import json

import httpx
import pytest

from packages.agents.llm.config import load_provider_config, validate_url
from packages.agents.llm.errors import (
    LlmAuthenticationError,
    LlmConfigurationError,
    LlmError,
    LlmModelError,
    LlmRateLimitError,
    LlmRequestError,
    LlmTimeoutError,
    LlmTransientError,
)
from packages.agents.llm.providers import OpenAIChatAdapter, parse_json_content
from packages.agents.llm.transport import SafeHttpTransport, redact_secrets


def _config(**overrides):
    from packages.agents.llm.config import ProviderConfig

    base = dict(
        profile="omniroute",
        protocol="openai_chat",
        model="auto",
        api_key="secret-token-abc",
        base_url="http://127.0.0.1:20128/v1",
        auth_mode="bearer",
        structured_mode="json_object",
        timeout_sec=5.0,
        max_retries=0,
        retry_base_ms=1,
        extra_headers={},
        allow_loopback_http=True,
        max_completion_tokens=128,
    )
    base.update(overrides)
    return ProviderConfig(**base)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), timeout=5.0)


def test_redact_secrets():
    assert "[REDACTED]" in redact_secrets("Bearer secret-token-abc and more")
    assert "secret-token-abc" not in redact_secrets("Bearer secret-token-abc")


def test_loopback_http_rejected_for_non_loopback():
    with pytest.raises(LlmConfigurationError):
        validate_url("http://example.com/v1", allow_loopback_http=True)


def test_loopback_http_ok():
    assert validate_url("http://127.0.0.1:20128/v1", allow_loopback_http=True).endswith("/v1")


def test_extra_headers_cannot_override_auth(monkeypatch):
    monkeypatch.setenv("AEGIS_LLM_PROFILE", "omniroute")
    monkeypatch.setenv("AEGIS_LLM_API_KEY", "k")
    monkeypatch.setenv("AEGIS_LLM_EXTRA_HEADERS_JSON", '{"Authorization": "nope"}')
    with pytest.raises(LlmConfigurationError):
        load_provider_config()


def test_mix_groq_and_omniroute_errors(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setenv("AEGIS_LLM_PROFILE", "omniroute")
    monkeypatch.setenv("AEGIS_LLM_API_KEY", "k")
    with pytest.raises(LlmConfigurationError):
        load_provider_config()


@pytest.mark.parametrize(
    "status,exc_type",
    [
        (400, LlmRequestError),
        (401, LlmAuthenticationError),
        (403, LlmAuthenticationError),
        (404, LlmModelError),
        (429, LlmRateLimitError),
        (500, LlmTransientError),
        (502, LlmTransientError),
        (503, LlmTransientError),
    ],
)
def test_http_error_mapping(status, exc_type):
    def handler(request: httpx.Request) -> httpx.Response:
        assert "secret-token-abc" in request.headers.get("authorization", "")
        return httpx.Response(status, json={"error": "Bearer secret-token-abc leaked?"})

    transport = SafeHttpTransport(client=_client(handler), max_retries=0, allow_loopback_http=True)
    with pytest.raises(exc_type) as err:
        transport.post_json("http://127.0.0.1:20128/v1/chat/completions", {}, {"Authorization": "Bearer secret-token-abc"})
    assert "secret-token-abc" not in str(err.value)


def test_http_200_json():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    transport = SafeHttpTransport(client=_client(handler), allow_loopback_http=True)
    assert transport.post_json("http://127.0.0.1:20128/v1/x", {}, {}) == {"ok": True}


def test_malformed_json_body():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    transport = SafeHttpTransport(client=_client(handler), allow_loopback_http=True)
    with pytest.raises(LlmError):
        transport.post_json("http://127.0.0.1:20128/v1/x", {}, {})


def test_empty_content():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": ""}}]},
        )

    adapter = OpenAIChatAdapter(_config(), client=_client(handler))
    from packages.agents.llm.errors import LlmMalformedOutputError

    with pytest.raises(LlmMalformedOutputError):
        adapter.complete_json(system="s", user="u", schema_name="AttackExtract")


def test_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("slow")

    transport = SafeHttpTransport(client=_client(handler), allow_loopback_http=True)
    with pytest.raises(LlmTimeoutError):
        transport.post_json("http://127.0.0.1:20128/v1/x", {}, {})


def test_schema_downgrade_once():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        body = json.loads(request.content)
        rf = body.get("response_format") or {}
        if rf.get("type") == "json_schema":
            return httpx.Response(400, json={"error": "json_schema not supported"})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"technique_id":"T09","name":"x"}'}}
                ]
            },
        )

    adapter = OpenAIChatAdapter(_config(structured_mode="auto"), client=_client(handler))
    out = adapter.complete_json(system="s", user="u", schema_name="AttackExtract")
    assert out["technique_id"] == "T09"
    assert calls["n"] == 2


def test_parse_json_content_fences():
    assert parse_json_content('```json\n{"a":1}\n```') == {"a": 1}


@pytest.mark.live_llm
def test_live_omniroute_optional():
    from packages.agents.llm.config import is_llm_configured
    from packages.agents.llm.extraction import extract_attack_json

    if not is_llm_configured():
        pytest.skip("OmniRoute not configured")
    data = extract_attack_json("Deepfake KYC liveness bypass on UPI onboarding.", "https://www.fincen.gov/x")
    assert isinstance(data, dict)
