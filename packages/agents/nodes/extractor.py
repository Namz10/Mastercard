"""Extractor node — fetch body, LLM/rule extract, pgvector chunk."""

import time

from pydantic import ValidationError

from packages.agents.limits import resolve_limit
from packages.agents.llm import extract_from_document
from packages.agents.settings import get_identify_settings
from packages.agents.state import IdentifyState
from packages.catalog.models import AttackSpec
from packages.osint.allowlist import domain_from_url, is_allowlisted_url
from packages.osint.extract import extract_fixture_text, extract_url
from packages.osint.fixtures import FIXTURE_FILES
from packages.osint.settings import get_osint_settings
from packages.osint.telemetry.indicators import collect_network_indicators
from packages.osint.vector_store import upsert_chunk


def _body_for_url(url: str) -> tuple[str, str]:
    """Return (text, extractor_name). Fixture lookup is keyed by URL only."""
    settings = get_osint_settings()
    for key, (_, fixture_url) in FIXTURE_FILES.items():
        if url == fixture_url or url.rstrip("/") == fixture_url.rstrip("/"):
            doc = extract_fixture_text(key)
            return doc.text, doc.extractor

    if not settings.identify_live_search:
        raise ValueError(f"no_fixture_for_url:{url}")

    doc = extract_url(url)
    return doc.text, doc.extractor


def extractor(state: IdentifyState) -> IdentifyState:
    identify = get_identify_settings()
    candidates = state.get("candidate_urls") or []
    extracted_docs: list[dict] = []
    proposed: list[dict] = []
    errors = list(state.get("errors") or [])
    max_chars = identify.identify_max_extract_chars
    max_docs = resolve_limit(identify.identify_max_docs) or 3
    sleep_s = max(0, identify.identify_extract_sleep_ms) / 1000.0
    extracts_done = 0

    for item in candidates:
        if max_docs is not None and extracts_done >= max_docs:
            break
        url = item.get("url", "")
        if not url or not is_allowlisted_url(url):
            continue
        try:
            if extracts_done and sleep_s > 0:
                time.sleep(sleep_s)
            text, extractor_name = _body_for_url(url)
            if not text.strip():
                errors.append(f"extract_empty:{url}")
                continue
            domain = domain_from_url(url)
            chunk = upsert_chunk(
                url=url,
                text=text,
                domain=domain,
                source_type=extractor_name,
                date=item.get("fetched_at"),
            )
            raw = extract_from_document(text, url, domain)
            extracts_done += 1
            if raw.get("extraction_source") != "abstain" and not raw.get("abstain"):
                raw["network_indicators"] = collect_network_indicators(
                    text,
                    raw.get("network_indicators"),
                    url,
                )
            extracted_docs.append(
                {
                    "url": url,
                    "domain": domain,
                    "text": text[:max_chars],
                    "text_len": len(text),
                    "chunk_id": chunk.id,
                    "extractor": extractor_name,
                    "extraction_source": raw.get("extraction_source"),
                    "abstain_reason": raw.get("abstain_reason"),
                }
            )
            if raw.get("extraction_source") == "abstain" or raw.get("abstain"):
                errors.append(f"extract_abstain:{url}:{raw.get('abstain_reason')}")
                continue
            raw.setdefault("source_urls", [url])
            raw["source_urls"] = [url]
            raw.setdefault("status", "proposed")
            if raw.get("llm_last_error"):
                errors.append(f"llm_fallback:{url}:{raw['llm_last_error']}")
            try:
                AttackSpec.model_validate(raw)
                proposed.append(raw)
            except ValidationError as exc:
                errors.append(f"extract_validate:{url}:{exc.errors()[0]['msg']}")
        except Exception as exc:
            errors.append(f"extract_fail:{url}:{exc}")

    state["extracted_docs"] = extracted_docs
    state["proposed_specs"] = proposed
    state["errors"] = errors
    return state
