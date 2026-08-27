"""Extractor node — fetch body, LLM/rule extract, Qdrant chunk."""

import os

from pydantic import ValidationError

from packages.agents.llm import extract_from_document
from packages.agents.state import IdentifyState
from packages.catalog.models import AttackSpec
from packages.osint.allowlist import domain_from_url, is_allowlisted_url, tier_for_domain
from packages.osint.extract import extract_fixture_text, extract_url
from packages.osint.fixtures import FIXTURE_FILES
from packages.osint.settings import get_osint_settings
from packages.osint.vector_store import upsert_chunk

DEFAULT_MAX_DOCS = 3


def _max_docs() -> int:
    raw = os.getenv("IDENTIFY_MAX_DOCS", str(DEFAULT_MAX_DOCS))
    try:
        return max(1, min(int(raw), 8))
    except ValueError:
        return DEFAULT_MAX_DOCS


def _body_for_url(url: str) -> tuple[str, str]:
    """Return (text, extractor_name)."""
    settings = get_osint_settings()
    for key, (_, fixture_url) in FIXTURE_FILES.items():
        if url == fixture_url or url.rstrip("/") == fixture_url.rstrip("/"):
            doc = extract_fixture_text(key)
            return doc.text, doc.extractor

    if not settings.identify_live_search:
        doc = extract_fixture_text("fincen_alert004")
        return doc.text, doc.extractor

    doc = extract_url(url)
    return doc.text, doc.extractor


def extractor(state: IdentifyState) -> IdentifyState:
    candidates = state.get("candidate_urls") or []
    # Prefer tier-1/2 regulator sources when Tavily returns vendor blogs first.
    candidates = sorted(
        candidates,
        key=lambda c: tier_for_domain(domain_from_url(c.get("url", ""))),
    )
    extracted_docs: list[dict] = []
    proposed: list[dict] = []
    errors = list(state.get("errors") or [])

    for item in candidates[:_max_docs()]:
        url = item.get("url", "")
        if not url or not is_allowlisted_url(url):
            continue
        try:
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
            extracted_docs.append(
                {
                    "url": url,
                    "domain": domain,
                    "text": text[:8000],
                    "text_len": len(text),
                    "chunk_id": chunk.id,
                    "extractor": extractor_name,
                    "extraction_source": raw.get("extraction_source"),
                }
            )
            raw.setdefault("source_urls", [url])
            raw.setdefault("status", "proposed")
            if raw.get("extraction_source") == "rules" and raw.get("groq_last_error"):
                errors.append(f"groq_fallback:{url}:{raw['groq_last_error']}")
            try:
                AttackSpec.model_validate(raw)
                proposed.append(raw)
            except ValidationError as exc:
                errors.append(f"extract_validate:{url}:{exc.errors()[0]['msg']}")
        except Exception as exc:
            errors.append(f"extract_fail:{url}:{exc}")

    state["extracted_docs"] = extracted_docs
    state["proposed_specs"] = proposed[:_max_docs()]
    state["errors"] = errors
    return state
