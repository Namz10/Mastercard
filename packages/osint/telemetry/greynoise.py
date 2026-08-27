"""GreyNoise Community API client for corroboration lookups."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

_COMMUNITY_URL = "https://api.greynoise.io/v3/community/{ip}"
_DEFAULT_TIMEOUT = 5.0


@dataclass(frozen=True)
class GreynoiseResult:
    seen: bool
    noise: bool
    riot: bool
    classification: str | None
    tags: list[str]
    raw: dict[str, Any]


def check_ip(ip: str, *, api_key: str | None = None, timeout: float = _DEFAULT_TIMEOUT) -> GreynoiseResult | None:
    """Query GreyNoise Community API. Returns None on missing key or transport error."""
    key = api_key if api_key is not None else os.getenv("GREYNOISE_API_KEY", "")
    if not key or not ip:
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(_COMMUNITY_URL.format(ip=ip), headers={"key": key})
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    noise = bool(payload.get("noise"))
    seen = bool(payload.get("seen", noise))
    riot = bool(payload.get("riot"))
    classification = payload.get("classification")
    tags_raw = payload.get("tags") or []
    tags = [str(t) for t in tags_raw] if isinstance(tags_raw, list) else []
    return GreynoiseResult(
        seen=seen,
        noise=noise,
        riot=riot,
        classification=str(classification) if classification is not None else None,
        tags=tags,
        raw=payload,
    )


def qualifies_for_corroboration(result: GreynoiseResult) -> bool:
    """True when GreyNoise shows attack-relevant noise, not benign RIOT-only infra."""
    if result.noise or result.seen:
        if result.riot and not result.noise and (result.classification or "").lower() == "benign":
            return False
        if result.classification and result.classification.lower() == "benign" and not result.noise:
            return False
        malicious_tags = {"malicious", "scanner", "worm", "botnet", "exploit"}
        if any(t.lower() in malicious_tags for t in result.tags):
            return True
        return bool(result.noise or result.seen)
    return False
