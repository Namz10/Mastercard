"""Safe synchronous HTTP transport with secret redaction."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from packages.agents.llm.errors import (
    LlmAuthenticationError,
    LlmError,
    LlmModelError,
    LlmRateLimitError,
    LlmRequestError,
    LlmTimeoutError,
    LlmTransientError,
)

_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})
_SECRET_PATTERNS = (
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{8,}"),
    re.compile(r"gsk_[a-zA-Z0-9]{8,}"),
    re.compile(r"AQ\.[a-zA-Z0-9._-]{8,}"),
)


@dataclass
class TransportMeta:
    wire_attempts: int = 0
    request_id: str = ""


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


@dataclass
class SafeHttpTransport:
    timeout_sec: float = 60.0
    max_retries: int = 1
    retry_base_ms: int = 500
    allow_loopback_http: bool = False
    client: httpx.Client | None = None
    meta: TransportMeta = field(default_factory=TransportMeta)

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        self.meta = TransportMeta()
        self._validate_url(url)
        max_attempts = max(1, self.max_retries + 1)
        last_error: Exception | None = None
        client = self.client
        own_client = client is None
        if own_client:
            client = httpx.Client(timeout=self.timeout_sec)
        assert client is not None
        try:
            for attempt in range(1, max_attempts + 1):
                self.meta.wire_attempts = attempt
                try:
                    response = client.post(url, json=payload, headers=headers)
                except httpx.TimeoutException as exc:
                    raise LlmTimeoutError("Request timed out") from exc
                except httpx.TransportError as exc:
                    last_error = LlmTransientError(f"Network error: {exc}")
                    if attempt >= max_attempts:
                        raise last_error from exc
                    continue
                request_id = response.headers.get("x-request-id", "")
                self.meta.request_id = request_id
                if response.status_code < 400:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise LlmError(
                            f"Provider returned non-JSON body (HTTP {response.status_code})",
                            status_code=response.status_code,
                            request_id=request_id,
                        ) from exc
                try:
                    self._raise_for_status(response)
                except (LlmRateLimitError, LlmTransientError) as exc:
                    last_error = exc
                    if attempt >= max_attempts:
                        raise
                    continue
            assert last_error is not None
            raise last_error
        finally:
            if own_client:
                client.close()

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise LlmRequestError(f"Unsupported URL scheme: {parsed.scheme!r}")
        host = (parsed.hostname or "").lower()
        if parsed.scheme == "http" and host not in ("127.0.0.1", "localhost", "::1"):
            raise LlmRequestError("Plain HTTP is only allowed for loopback hosts")

    def _raise_for_status(self, response: httpx.Response) -> None:
        request_id = response.headers.get("x-request-id", "")
        safe_body = redact_secrets(response.text[:2000])
        message = f"HTTP {response.status_code}: {safe_body[:500]}" if safe_body else f"HTTP {response.status_code}"
        status = response.status_code
        if status in (401, 403):
            raise LlmAuthenticationError(message, status_code=status, request_id=request_id)
        if status == 404:
            raise LlmModelError(message, status_code=status, request_id=request_id)
        if status == 429:
            retry_after = 0.0
            if response.headers.get("Retry-After"):
                try:
                    retry_after = float(response.headers["Retry-After"])
                except ValueError:
                    retry_after = 0.0
            raise LlmRateLimitError(
                message, status_code=status, request_id=request_id, retry_after_sec=retry_after
            )
        if status in _RETRYABLE_STATUS:
            raise LlmTransientError(message, status_code=status, request_id=request_id)
        if 400 <= status < 500:
            raise LlmRequestError(message, status_code=status, request_id=request_id)
        raise LlmError(message, status_code=status, request_id=request_id)
