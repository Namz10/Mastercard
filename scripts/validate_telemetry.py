#!/usr/bin/env python3
"""Live telemetry gate: IC3 IOC advisories → extract → indicators → GreyNoise.

Called from ./run.sh after live product gates. Tries known IC3 cybersecurity
advisories with published IP IOC tables first, then Tavily on allowlisted domains.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.env import load_project_env

# Real FBI IC3 cybersecurity advisories with published IP/domain IOC tables (tier 1).
_DEFAULT_SEED_URLS = (
    "https://www.ic3.gov/CSA/2024/240918.pdf",
    "https://www.ic3.gov/CSA/2025/250507.pdf",
)

_DEFAULT_TOPICS = (
    "site:ic3.gov botnet IP address cybersecurity advisory indicator compromise",
    "FBI IC3 cybersecurity advisory botnet command control infrastructure IP",
    "card testing botnet scanner payment fraud cybersecurity IP",
)


def _require_live_config() -> None:
    from packages.agents.llm.config import is_llm_configured
    from packages.osint.settings import get_osint_settings

    settings = get_osint_settings()
    missing = []
    if not settings.identify_live_search:
        missing.append("IDENTIFY_LIVE_SEARCH=true")
    if not settings.tavily_api_key:
        missing.append("TAVILY_API_KEY")
    if not is_llm_configured():
        missing.append("AEGIS_LLM_API_KEY (or active-profile alias)")
    if missing:
        raise SystemExit(f"Telemetry gate requires live .env: {', '.join(missing)}")


def _telemetry_topics() -> list[str]:
    custom = os.getenv("TELEMETRY_TOPIC", "").strip()
    if custom:
        return [custom]
    return list(_DEFAULT_TOPICS)


def _telemetry_seed_urls() -> list[str]:
    raw = os.getenv("TELEMETRY_SEED_URLS", "").strip()
    if raw:
        return [part.strip() for part in raw.split(",") if part.strip()]
    return list(_DEFAULT_SEED_URLS)


def _minimal_network_spec(sanitized: list[dict], source_url: str, domain: str) -> dict:
    from packages.osint.allowlist import tier_for_domain

    role = str(sanitized[0].get("role") or "scanner")
    technique_id = "T07" if "card" in role or "stuffing" in role or "credential" in role else "T01"
    return {
        "technique_id": technique_id,
        "genai_modality": "bot",
        "confidence_level": "reported-unverified",
        "source_urls": [source_url],
        "source_tier": tier_for_domain(domain),
        "network_indicators": sanitized,
        "name": f"Live network-footprint indicator ({domain})",
    }


def _try_document(
    *,
    url: str,
    domain: str,
    has_gn_key: bool,
) -> bool:
    from packages.agents.corroborator import apply_corroboration
    from packages.agents.llm import extract_from_document
    from packages.osint.extract import extract_url
    from packages.osint.telemetry import collect_network_indicators

    try:
        doc = extract_url(url)
    except Exception as exc:
        print(f"telemetry_extract_fail url={url} error={type(exc).__name__}:{exc}", flush=True)
        return False

    text = doc.text.strip()
    if not text:
        print(f"telemetry_extract_empty url={url}", flush=True)
        return False

    raw = extract_from_document(text, url, domain)
    llm_inds = raw.get("network_indicators") if raw.get("extraction_source") != "abstain" else []
    sanitized = collect_network_indicators(text, llm_inds, url)
    print(
        f"telemetry_doc url={url} extractor={doc.extractor} chars={len(text)} "
        f"llm_source={raw.get('extraction_source')} indicators={len(sanitized)}",
        flush=True,
    )
    if not sanitized:
        return False

    if raw.get("extraction_source") != "abstain" and not raw.get("abstain"):
        spec = dict(raw)
    else:
        spec = _minimal_network_spec(sanitized, url, domain)
    spec["network_indicators"] = sanitized
    spec = apply_corroboration(spec)

    corroboration = spec.get("corroboration_type")
    evidence = spec.get("corroboration_evidence")
    print(
        f"telemetry_match url={url} "
        f"technique_id={spec.get('technique_id')} "
        f"vector_class={spec.get('vector_class')} "
        f"indicator={sanitized[0].get('value')} "
        f"corroboration_type={corroboration} "
        f"greynoise_configured={has_gn_key}",
        flush=True,
    )
    if evidence:
        print(
            f"greynoise_hit ip={evidence.get('lookup_ip')} "
            f"tags={evidence.get('greynoise_tags')} "
            f"qualifier={evidence.get('qualifier')}",
            flush=True,
        )
    elif has_gn_key:
        print(
            "greynoise_miss=ok (live indicator extracted; IP not currently seen as noise)",
            flush=True,
        )
    else:
        print("greynoise_skipped=no_api_key", flush=True)

    vector_class = spec.get("vector_class")
    assert len(sanitized) >= 1
    assert corroboration in {
        "network-telemetry",
        "documentary-case",
        "not-yet-corroborated",
    }
    # Do not coerce T13/APP advisories to network_footprint. IPs on a social
    # engineering CSA are documentary indicators, not a mule-botnet class.
    if vector_class == "human_social":
        print(
            "telemetry_class=human_social indicators_kept_as_documentary",
            flush=True,
        )
    elif vector_class == "network_footprint":
        print("telemetry_class=network_footprint", flush=True)
    else:
        raise AssertionError(f"unexpected vector_class={vector_class}")
    print("=== TELEMETRY GATE PASSED (live) ===", flush=True)
    return True


def main() -> None:
    load_project_env()
    _require_live_config()
    os.environ.setdefault("IDENTIFY_ARXIV_API_ENABLED", "false")

    from packages.agents.settings import get_identify_settings
    from packages.osint.allowlist import domain_from_url
    from packages.osint.collect import gather_live_candidates
    from packages.osint.settings import get_osint_settings

    identify = get_identify_settings()
    osint = get_osint_settings()
    max_docs = int(os.getenv("TELEMETRY_MAX_DOCS", "10"))
    has_gn_key = bool(os.getenv("GREYNOISE_API_KEY", "").strip())

    errors: list[str] = []
    seen_urls: set[str] = set()
    tried_urls: list[str] = []

    def _attempt(url: str, domain: str | None = None) -> bool:
        if not url or url in seen_urls:
            return False
        seen_urls.add(url)
        tried_urls.append(url)
        resolved_domain = domain or domain_from_url(url)
        return _try_document(url=url, domain=resolved_domain, has_gn_key=has_gn_key)

    print("==> Telemetry seed URLs (IC3 IOC advisories)", flush=True)
    for seed_url in _telemetry_seed_urls():
        print(f"telemetry_seed url={seed_url}", flush=True)
        if _attempt(seed_url):
            return

    for topic in _telemetry_topics():
        print(f"telemetry_search topic={topic!r}", flush=True)
        candidates: list[dict[str, Any]] = gather_live_candidates(
            topic,
            identify=identify,
            osint=osint,
            errors=errors,
        )
        for hit in candidates:
            if len(tried_urls) >= max_docs:
                break
            url = str(hit.get("url") or "")
            domain = str(hit.get("source_domain") or "") or None
            if _attempt(url, domain):
                return
        if len(tried_urls) >= max_docs:
            break

    for error in errors[:5]:
        print(f"telemetry_collect_warning={error}", flush=True)
    raise AssertionError(
        "Telemetry gate: no attack-attributed IPs found in live allowlisted documents "
        f"(tried={len(tried_urls)}). IC3 seed fetch may have failed — check network/Tavily extract."
    )


if __name__ == "__main__":
    main()
