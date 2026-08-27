"""Sanitize LLM-proposed network indicators before telemetry lookup."""

from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

_ATTACK_ROLES = frozenset(
    {
        "scanner",
        "botnet",
        "c2",
        "card_testing",
        "stuffing_source",
        "credential_stuffing",
    }
)

_VICTIM_CONTEXT = re.compile(
    r"\b(victim|customer|legitimate|bank server|financial institution|logged in from|victim's)\b",
    re.IGNORECASE,
)

_ATTACK_CONTEXT = re.compile(
    r"\b(scanner|botnet|malicious|attack|c2|card.?test|stuffing|credential|"
    r"malware|compromis|infrastructure|indicator|command.and.control)\b",
    re.IGNORECASE,
)

_DOC_IOC_CONTEXT = re.compile(
    r"\b(botnet|cybersecurity advisory|indicator[s]? of compromise|"
    r"command and control|malware|c2 infrastructure|public service announcement)\b",
    re.IGNORECASE,
)

_IOC_TABLE_ROW = re.compile(
    r"[a-z0-9][-a-z0-9.]+\.[a-z]{2,}\s+(?:\d{1,3}\.){3}\d{1,3}",
    re.IGNORECASE,
)

_PUBLIC_DNS = frozenset({"8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1"})
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class NetworkIndicator:
    type: str  # ip | domain
    value: str
    role: str
    evidence_span: str
    resolved_ip: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sanitize_network_indicators(
    article_text: str,
    raw_indicators: list[Any] | None,
    source_url: str,
    *,
    max_indicators: int = 5,
) -> list[dict[str, Any]]:
    """Validate and filter indicators; returns JSON-serializable dicts."""
    if not raw_indicators or not article_text.strip():
        return []

    publisher_host = _hostname_from_url(source_url)
    kept: list[NetworkIndicator] = []
    seen_values: set[str] = set()

    for item in raw_indicators:
        if len(kept) >= max_indicators:
            break
        if not isinstance(item, dict):
            continue
        normalized = _normalize_indicator(item, article_text, publisher_host)
        if normalized is None:
            continue
        key = normalized.value.lower()
        if key in seen_values:
            continue
        seen_values.add(key)
        kept.append(normalized)

    return [row.to_dict() for row in kept]


def propose_indicators_from_text(article_text: str, *, max_indicators: int = 5) -> list[dict[str, Any]]:
    """Deterministic fallback: find public IPv4s in article text with attack context windows.

    No fixed IOC list — reads whatever the article actually contains.
    """
    if not article_text.strip():
        return []

    doc_ioc_context = bool(_DOC_IOC_CONTEXT.search(article_text))
    proposed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in _IPV4_RE.finditer(article_text):
        if len(proposed) >= max_indicators:
            break
        ip = match.group(0)
        if ip in seen or not _is_public_ipv4(ip):
            continue
        start = max(0, match.start() - 100)
        end = min(len(article_text), match.end() + 100)
        window = article_text[start:end].strip()
        if len(window) > 200:
            window = window[:200]
        if _VICTIM_CONTEXT.search(window):
            continue

        line_start = article_text.rfind("\n", 0, match.start()) + 1
        line_end = article_text.find("\n", match.end())
        if line_end == -1:
            line_end = len(article_text)
        line = article_text[line_start:line_end].strip()

        attack_ok = bool(_ATTACK_CONTEXT.search(window) or _ATTACK_CONTEXT.search(line))
        if not attack_ok and doc_ioc_context:
            attack_ok = bool(_IOC_TABLE_ROW.search(line))
        if not attack_ok:
            continue
        if ip in _PUBLIC_DNS:
            continue
        role = _infer_role(window if _ATTACK_CONTEXT.search(window) else line)
        if doc_ioc_context and role == "scanner" and "botnet" in article_text.lower():
            role = "botnet"
        evidence = line if len(line) <= 200 else window
        seen.add(ip)
        proposed.append(
            {
                "type": "ip",
                "value": ip,
                "role": role,
                "evidence_span": evidence,
            }
        )
    return proposed


def merge_raw_indicators(*groups: list[Any] | None) -> list[dict[str, Any]]:
    """Dedupe indicator dicts by normalized value."""
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        if not group:
            continue
        for item in group:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or "").lower()
            value = str(item.get("value") or "").strip().lower()
            if not kind or not value:
                continue
            key = f"{kind}:{value}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(item))
    return merged


def collect_network_indicators(
    article_text: str,
    llm_indicators: list[Any] | None,
    source_url: str,
    *,
    max_indicators: int = 5,
) -> list[dict[str, Any]]:
    """Merge LLM + text-proposed indicators, then sanitize against article text."""
    proposed = propose_indicators_from_text(article_text, max_indicators=max_indicators)
    merged = merge_raw_indicators(llm_indicators, proposed)
    return sanitize_network_indicators(
        article_text,
        merged,
        source_url,
        max_indicators=max_indicators,
    )


def _infer_role(window: str) -> str:
    lower = window.lower()
    if "card" in lower and "test" in lower:
        return "card_testing"
    if "stuffing" in lower or "credential" in lower:
        return "credential_stuffing"
    if "botnet" in lower:
        return "botnet"
    if re.search(r"\bc2\b", lower) or "command and control" in lower:
        return "c2"
    return "scanner"


def indicator_lookup_ip(indicator: dict[str, Any]) -> str | None:
    """Return IPv4 string to query, or None."""
    kind = str(indicator.get("type") or "").lower()
    if kind == "ip":
        value = str(indicator.get("value") or "").strip()
        return value if value else None
    if kind == "domain":
        resolved = indicator.get("resolved_ip")
        return str(resolved).strip() if resolved else None
    return None


def _normalize_indicator(
    item: dict[str, Any],
    article_text: str,
    publisher_host: str | None,
) -> NetworkIndicator | None:
    kind = str(item.get("type") or "").lower()
    if kind not in {"ip", "domain"}:
        return None

    role = str(item.get("role") or "").lower().replace("-", "_")
    if role not in _ATTACK_ROLES:
        return None

    value = str(item.get("value") or "").strip().lower()
    evidence_span = str(item.get("evidence_span") or "").strip()
    if not value or not evidence_span or len(evidence_span) > 200:
        return None

    if not _evidence_in_article(evidence_span, article_text):
        return None
    if value not in evidence_span.lower() and not _value_in_span(value, evidence_span):
        return None
    if _VICTIM_CONTEXT.search(evidence_span):
        return None

    if kind == "ip":
        if not _is_public_ipv4(value):
            return None
        if value in _PUBLIC_DNS and not _ATTACK_CONTEXT.search(evidence_span):
            return None
        if publisher_host and value == publisher_host:
            return None
        return NetworkIndicator("ip", value, role, evidence_span)

    if not _DOMAIN_RE.match(value):
        return None
    if publisher_host and (value == publisher_host or value.endswith(f".{publisher_host}")):
        return None

    resolved = _resolve_domain(value)
    if not resolved or not _is_public_ipv4(resolved):
        return None
    return NetworkIndicator("domain", value, role, evidence_span, resolved_ip=resolved)


def _evidence_in_article(span: str, article_text: str) -> bool:
    if span in article_text:
        return True
    return span.lower() in article_text.lower()


def _value_in_span(value: str, span: str) -> bool:
    return value in span.lower()


def _is_public_ipv4(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value)
    except ValueError:
        return False
    if addr.version != 4:
        return False
    return addr.is_global


def _hostname_from_url(source_url: str) -> str | None:
    try:
        host = urlparse(source_url).hostname
    except ValueError:
        return None
    return host.lower() if host else None


def _resolve_domain(hostname: str) -> str | None:
    try:
        infos = socket.getaddrinfo(hostname, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
    except OSError:
        return None
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            return str(sockaddr[0])
    return None
