"""OpenAI-compatible chat adapter (OmniRoute / Groq / generic)."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

import httpx

from packages.agents.llm.config import ProviderConfig
from packages.agents.llm.errors import LlmMalformedOutputError, LlmRequestError
from packages.agents.llm.schemas import get_json_schema
from packages.agents.llm.transport import SafeHttpTransport

_UNSUPPORTED_SCHEMA_RE = re.compile(
    r"(response_format|json_schema|structured|not supported|unknown|invalid|unrecognized)",
    re.IGNORECASE,
)


class LlmProvider(Protocol):
    last_meta: dict

    def complete_json(self, *, system: str, user: str, schema_name: str) -> dict: ...


def build_provider(config: ProviderConfig, *, client: httpx.Client | None = None) -> LlmProvider:
    if config.protocol != "openai_chat":
        raise LlmRequestError(f"Unsupported protocol: {config.protocol!r}")
    return OpenAIChatAdapter(config, client=client)


def _auth_headers(config: ProviderConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json", **config.extra_headers}
    if config.auth_mode == "bearer":
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _extract_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    if not cleaned.startswith("{") and "{" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if end > start:
            cleaned = cleaned[start : end + 1]
    return cleaned.strip()


def parse_json_content(text: str) -> dict:
    cleaned = _extract_json_text(text)
    if not cleaned:
        raise LlmMalformedOutputError("Provider returned empty content")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LlmMalformedOutputError(f"Provider returned invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LlmMalformedOutputError("Provider returned non-object JSON")
    if "attacks" in data and isinstance(data["attacks"], list) and data["attacks"]:
        first = data["attacks"][0]
        if isinstance(first, dict):
            return first
    return data


class OpenAIChatAdapter:
    def __init__(self, config: ProviderConfig, *, client: httpx.Client | None = None):
        self.config = config
        self.transport = SafeHttpTransport(
            timeout_sec=config.timeout_sec,
            max_retries=config.max_retries,
            retry_base_ms=config.retry_base_ms,
            allow_loopback_http=config.allow_loopback_http,
            client=client,
        )
        self.last_meta: dict = {}
        self._schema_downgraded = False

    def complete_json(self, *, system: str, user: str, schema_name: str) -> dict:
        schema = get_json_schema(schema_name)
        mode = "json_object" if self.config.structured_mode != "json_schema" else "json_schema"
        if self.config.structured_mode == "auto":
            mode = "json_schema"
        try:
            return self._complete(system, user, schema, mode)
        except Exception as exc:
            if (
                self.config.structured_mode == "auto"
                and not self._schema_downgraded
                and mode == "json_schema"
                and isinstance(exc, LlmRequestError)
                and exc.status_code in (400, 422)
                and _UNSUPPORTED_SCHEMA_RE.search(str(exc))
            ):
                self._schema_downgraded = True
                return self._complete(system, user, schema, "json_object")
            raise

    def _complete(self, system: str, user: str, schema: dict, mode: str) -> dict:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "stream": False,
            "temperature": 0.1,
            "max_tokens": self.config.max_completion_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if mode == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "AttackExtract", "strict": False, "schema": schema},
            }
        else:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        body = self.transport.post_json(url, payload, _auth_headers(self.config))
        self.last_meta = {
            "provider": self.config.profile,
            "model": self.config.model,
            "schema_mode": mode,
            "wire_attempts": self.transport.meta.wire_attempts,
            "request_id": self.transport.meta.request_id,
        }
        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmMalformedOutputError("Response missing message content") from exc
        content = ""
        for key in ("content", "reasoning"):
            val = message.get(key)
            if val is not None and str(val).strip():
                content = str(val).strip()
                break
        if not content:
            raise LlmMalformedOutputError("Provider returned empty message content")
        return parse_json_content(content)
