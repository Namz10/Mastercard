"""Provider configuration — env parsing and data-only profile registry."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlparse

from packages.agents.llm.errors import LlmConfigurationError

Protocol = Literal["openai_chat"]
AuthMode = Literal["bearer", "none"]
StructuredMode = Literal["auto", "json_schema", "json_object"]

_UNIVERSAL_KEYS = (
    "AEGIS_LLM_PROFILE",
    "AEGIS_LLM_MODEL",
    "AEGIS_LLM_API_KEY",
    "AEGIS_LLM_BASE_URL",
    "AEGIS_LLM_PROTOCOL",
    "AEGIS_LLM_AUTH_MODE",
)

_RESERVED_AUTH_HEADERS = frozenset({"authorization", "x-api-key", "x-goog-api-key", "api-key"})

DEFAULT_OMNIROUTE_BASE = "http://127.0.0.1:20128/v1"
DEFAULT_OMNIROUTE_MODEL = "auto"


@dataclass(frozen=True)
class ProfileRecipe:
    protocol: Protocol
    base_url: str
    auth_mode: AuthMode
    structured_mode: StructuredMode = "json_object"
    default_headers: dict[str, str] = field(default_factory=dict)


_PROFILES: dict[str, ProfileRecipe] = {
    "omniroute": ProfileRecipe(
        protocol="openai_chat",
        base_url=DEFAULT_OMNIROUTE_BASE,
        auth_mode="bearer",
        structured_mode="json_object",
    ),
    "generic_openai": ProfileRecipe(
        protocol="openai_chat",
        base_url="",
        auth_mode="bearer",
        structured_mode="json_object",
    ),
    "groq": ProfileRecipe(
        protocol="openai_chat",
        base_url="https://api.groq.com/openai/v1",
        auth_mode="bearer",
        structured_mode="json_object",
    ),
}


@dataclass(frozen=True)
class ProviderConfig:
    profile: str
    protocol: Protocol
    model: str
    api_key: str
    base_url: str
    auth_mode: AuthMode
    structured_mode: StructuredMode
    timeout_sec: float
    max_retries: int
    retry_base_ms: int
    extra_headers: dict[str, str]
    allow_loopback_http: bool
    max_completion_tokens: int = 2048

    @property
    def endpoint_host(self) -> str:
        return urlparse(self.base_url).hostname or ""


def _env(key: str) -> str:
    return os.environ.get(key, "").strip()


def _env_present(key: str) -> bool:
    return _env(key) != ""


def validate_url(url: str, *, allow_loopback_http: bool) -> str:
    cleaned = url.strip().rstrip("/")
    if not cleaned:
        raise LlmConfigurationError("Base URL is required")
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https"):
        raise LlmConfigurationError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise LlmConfigurationError("Embedded credentials in URL are not allowed")
    if parsed.fragment or parsed.query:
        raise LlmConfigurationError("URL fragments and query parameters are not allowed")
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "http":
        if not allow_loopback_http or host not in ("127.0.0.1", "localhost", "::1"):
            raise LlmConfigurationError("Plain HTTP is only allowed for loopback hosts")
    return cleaned


def _parse_extra_headers(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LlmConfigurationError(f"AEGIS_LLM_EXTRA_HEADERS_JSON is invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LlmConfigurationError("AEGIS_LLM_EXTRA_HEADERS_JSON must be a JSON object")
    headers: dict[str, str] = {}
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise LlmConfigurationError("AEGIS_LLM_EXTRA_HEADERS_JSON keys/values must be strings")
        if key.lower() in _RESERVED_AUTH_HEADERS:
            raise LlmConfigurationError(f"Reserved auth header not allowed in extra headers: {key!r}")
        headers[key] = value
    return headers


def _allow_loopback(profile: str) -> bool:
    raw = _env("AEGIS_LLM_ALLOW_LOOPBACK_HTTP").lower()
    if raw in {"1", "true", "yes"}:
        return True
    if raw in {"0", "false", "no"}:
        return False
    return profile in {"omniroute", "generic_openai"}


def load_provider_config() -> ProviderConfig:
    groq_key = _env("GROQ_API_KEY")
    profile = _env("AEGIS_LLM_PROFILE").lower() or "omniroute"

    if groq_key and profile not in {"groq"}:
        if _env_present("AEGIS_LLM_API_KEY") or any(_env_present(k) for k in _UNIVERSAL_KEYS):
            raise LlmConfigurationError(
                "Cannot mix GROQ_API_KEY with AEGIS_LLM_* unless AEGIS_LLM_PROFILE=groq"
            )
        raise LlmConfigurationError(
            "GROQ_API_KEY is set but AEGIS_LLM_PROFILE is not groq; set AEGIS_LLM_PROFILE=groq to opt in"
        )

    if profile not in _PROFILES:
        known = ", ".join(sorted(_PROFILES))
        raise LlmConfigurationError(f"Unknown AEGIS_LLM_PROFILE={profile!r}; known: {known}")

    recipe = _PROFILES[profile]
    model = _env("AEGIS_LLM_MODEL") or (DEFAULT_OMNIROUTE_MODEL if profile == "omniroute" else "")
    if not model:
        raise LlmConfigurationError("AEGIS_LLM_MODEL is required")

    allow_loopback = _allow_loopback(profile)
    base_override = _env("AEGIS_LLM_BASE_URL")
    if profile == "generic_openai" and not base_override and not recipe.base_url:
        raise LlmConfigurationError("AEGIS_LLM_BASE_URL is required for profile generic_openai")
    base_url = validate_url(base_override or recipe.base_url, allow_loopback_http=allow_loopback)

    api_key = _env("AEGIS_LLM_API_KEY")
    if profile == "groq":
        api_key = api_key or groq_key
    if recipe.auth_mode != "none" and not api_key:
        raise LlmConfigurationError("AEGIS_LLM_API_KEY is required for this profile (or GROQ_API_KEY when profile=groq)")

    timeout_sec = float(_env("AEGIS_LLM_TIMEOUT_SEC") or "60")
    retry_default = "2" if profile == "groq" else "1"
    max_retries = int(_env("AEGIS_LLM_MAX_RETRIES") or retry_default)
    if profile == "groq" and not _env_present("AEGIS_LLM_MAX_RETRIES"):
        max_retries = max(max_retries, 2)
    retry_base_ms = int(_env("AEGIS_LLM_RETRY_BASE_MS") or "500")
    max_tokens = int(_env("AEGIS_LLM_MAX_COMPLETION_TOKENS") or "2048")
    extra = {**recipe.default_headers, **_parse_extra_headers(_env("AEGIS_LLM_EXTRA_HEADERS_JSON"))}

    structured: StructuredMode = recipe.structured_mode
    structured_raw = _env("AEGIS_LLM_STRUCTURED_MODE").lower()
    if structured_raw:
        if structured_raw not in ("auto", "json_schema", "json_object"):
            raise LlmConfigurationError(f"Invalid AEGIS_LLM_STRUCTURED_MODE={structured_raw!r}")
        structured = structured_raw  # type: ignore[assignment]

    return ProviderConfig(
        profile=profile,
        protocol=recipe.protocol,
        model=model,
        api_key=api_key,
        base_url=base_url,
        auth_mode=recipe.auth_mode,
        structured_mode=structured,
        timeout_sec=timeout_sec,
        max_retries=max_retries,
        retry_base_ms=retry_base_ms,
        extra_headers=extra,
        allow_loopback_http=allow_loopback,
        max_completion_tokens=max_tokens,
    )


def list_profiles() -> tuple[str, ...]:
    return tuple(sorted(_PROFILES))


def is_llm_configured() -> bool:
    try:
        load_provider_config()
        return True
    except LlmConfigurationError:
        return False


def public_llm_status() -> dict[str, str | bool]:
    """Safe config snapshot — no keys or secret-bearing URLs."""
    try:
        cfg = load_provider_config()
        return {
            "configured": True,
            "profile": cfg.profile,
            "model": cfg.model,
            "loopback_http": cfg.allow_loopback_http,
        }
    except LlmConfigurationError:
        profile = _env("AEGIS_LLM_PROFILE") or "omniroute"
        return {
            "configured": False,
            "profile": profile,
            "model": _env("AEGIS_LLM_MODEL") or DEFAULT_OMNIROUTE_MODEL,
            "loopback_http": _allow_loopback(profile),
        }
