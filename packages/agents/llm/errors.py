"""Typed LLM provider errors."""

from __future__ import annotations


class LlmError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, request_id: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class LlmConfigurationError(LlmError):
    """Invalid or incomplete provider configuration."""


class LlmAuthenticationError(LlmError):
    """Authentication or authorization failure."""


class LlmModelError(LlmError):
    """Unknown, unavailable, or invalid model. Do not silently switch models."""


class LlmRequestError(LlmError):
    """Permanent request validation failure."""


class LlmTransientError(LlmError):
    """Transient transport or server failure; may be retried."""


class LlmRateLimitError(LlmTransientError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = 429,
        request_id: str = "",
        retry_after_sec: float = 0.0,
    ):
        super().__init__(message, status_code=status_code, request_id=request_id)
        self.retry_after_sec = retry_after_sec


class LlmTimeoutError(LlmTransientError):
    """Connection or read timeout."""


class LlmMalformedOutputError(LlmError):
    """Model returned content that could not be parsed as JSON."""
