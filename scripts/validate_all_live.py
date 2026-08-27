#!/usr/bin/env python3
"""Observable live product validation called only by ./run.sh.

This reads .env through the application loader and never overrides whether
live search is enabled.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.env import load_project_env


def _step(name: str):
    print(f"\n=== {name} ===", flush=True)
    started = time.perf_counter()
    return lambda: print(f"stage_seconds={time.perf_counter() - started:.2f}", flush=True)


def _require_live_config() -> None:
    from packages.agents.llm.config import is_llm_configured, public_llm_status
    from packages.agents.settings import get_identify_settings
    from packages.osint.settings import get_osint_settings

    settings = get_osint_settings()
    identify = get_identify_settings()
    missing = []
    if not settings.identify_live_search:
        missing.append("IDENTIFY_LIVE_SEARCH=true")
    if identify.identify_tavily_enabled and not settings.tavily_api_key:
        missing.append("TAVILY_API_KEY (or IDENTIFY_TAVILY_ENABLED=false)")
    if not is_llm_configured():
        missing.append("AEGIS_LLM_API_KEY (or active-profile alias)")
    if missing:
        raise SystemExit(f"Missing live .env configuration: {', '.join(missing)}")
    llm = public_llm_status()
    print(
        f"live_search={settings.identify_live_search} "
        f"llm_profile={llm.get('profile')} llm_model={llm.get('model')}",
        flush=True,
    )


def _catalog() -> None:
    from packages.catalog.loader import catalog_summary, load_catalog_yaml

    summary = catalog_summary(load_catalog_yaml())
    print(summary, flush=True)
    assert summary["count"] >= 28 and not summary["missing_techniques"]


def _seed_db() -> None:
    from apps.api.seed import seed_catalog

    count = seed_catalog(reset=True)
    print(f"seeded_atlas_rows={count}", flush=True)
    assert count >= 28


def _discover_document() -> tuple[Any, Any]:
    """Try all enabled collectors; prefer tier-1 Tavily/regulator hits."""
    from packages.osint.extract import extract_url
    from packages.osint.search import DEFAULT_QUERY
    from packages.osint.collect import gather_live_candidates
    from packages.osint.settings import get_osint_settings
    from packages.agents.settings import get_identify_settings

    topic = os.getenv("IDENTIFY_TOPIC", DEFAULT_QUERY).strip() or DEFAULT_QUERY
    identify = get_identify_settings()
    osint = get_osint_settings()
    errors: list[str] = []
    candidates = gather_live_candidates(topic, identify=identify, osint=osint, errors=errors)
    for error in errors[:3]:
        print(f"collect_warning={error}", flush=True)

    for hit in candidates:
        try:
            doc = extract_url(hit["url"])
        except Exception as exc:
            print(f"extract_error url={hit.get('url')} error={type(exc).__name__}", flush=True)
            continue
        if not doc.text.strip():
            continue
        print(
            f"selected source={hit.get('source')} domain={hit.get('source_domain')} "
            f"extractor={doc.extractor} chars={len(doc.text)} url={hit.get('url')}",
            flush=True,
        )

        class _Hit:
            url = hit["url"]
            source_domain = hit["source_domain"]

        return _Hit(), doc

    raise AssertionError("Collectors returned no extractable allowlisted document")


def _pgvector_upsert(hit: Any, doc: Any) -> None:
    from packages.agents.embeddings import embed_text
    from packages.osint.vector_store import COLLECTION_NAME, upsert_chunk

    chunk = upsert_chunk(hit.url, doc.text, hit.source_domain, doc.extractor)
    vector = embed_text(doc.text[:500])
    print(
        f"embedding_dim={len(vector)} chunk_id={chunk.id} collection={COLLECTION_NAME}",
        flush=True,
    )
    assert len(vector) == 384


def _llm_extract(hit: Any, doc: Any) -> None:
    from packages.agents.llm import extract_from_document

    spec = extract_from_document(doc.text, hit.url, hit.source_domain)
    source = spec.get("extraction_source")
    print(
        f"extraction_source={source} name={spec.get('name')} "
        f"abstain_reason={spec.get('abstain_reason')}",
        flush=True,
    )
    llm_abstained = source == "abstain" and spec.get("abstain_reason") == "llm_invalid_or_weak"
    assert source == "llm" or llm_abstained, (
        spec.get("llm_last_error") or spec.get("abstain_reason")
    )


def _identify_graph_live() -> None:
    from apps.api.db import SessionLocal
    from apps.api.models import AtlasRow
    from packages.agents.identify_graph import run_identify_graph
    from packages.osint.search import DEFAULT_QUERY

    topic = os.getenv("IDENTIFY_TOPIC", DEFAULT_QUERY).strip() or DEFAULT_QUERY
    result = run_identify_graph(run_id="run-sh-live", topic=topic)
    urls = result.get("candidate_urls") or []
    docs = result.get("extracted_docs") or []
    proposed = result.get("proposed_specs") or []
    hitl = result.get("hitl_queue") or []
    errors = result.get("errors") or []
    tavily_urls = [row for row in urls if row.get("source") == "tavily"]
    rss_urls = [row for row in urls if str(row.get("source", "")).startswith("rss:")]
    print(
        f"topic={topic!r} scout_urls={len(urls)} tavily={len(tavily_urls)} "
        f"rss={len(rss_urls)} scout_candidates={result.get('scout_candidate_count')} "
        f"curator_kept={result.get('curator_kept_count')} extracted={len(docs)} "
        f"proposal_candidates={len(proposed)} staged_hitl={len(hitl)}",
        flush=True,
    )
    for error in errors[:5]:
        print(f"pipeline_error={error}", flush=True)
    assert urls, "Scout returned no URLs"
    assert docs, "Extractor produced no documents"
    assert proposed or any("abstain" in error for error in errors), (
        "Pipeline produced neither proposals nor explicit abstains"
    )

    db = SessionLocal()
    try:
        for item in hitl:
            vector_id = item.get("vector_id")
            assert db.get(AtlasRow, vector_id) is not None, (
                f"HITL row {vector_id} was not persisted"
            )
    finally:
        db.close()


def _handoff() -> None:
    from apps.api.db import SessionLocal
    from packages.policy.coverage import build_coverage_map
    from packages.sim.runner import run_canary, run_population

    db = SessionLocal()
    try:
        population = run_population(
            db,
            vector_id="t13-upi-impersonation-app",
            run_id="run-sh-population",
        )
        canary = run_canary(
            db,
            campaign_id="fincen-fin-2024-alert004",
            run_id="run-sh-canary",
        )
        coverage = build_coverage_map(db)
        assert population["injector_id"] == "app_session"
        assert canary["event_count"] == 4
        assert coverage["technique_count"] == 24
        print(
            f"population_events={population['event_count']} "
            f"canary_stages={canary['event_count']} "
            f"coverage_techniques={coverage['technique_count']}",
            flush=True,
        )
    finally:
        db.close()


def _http_smoke() -> None:
    from fastapi.testclient import TestClient

    from apps.api.main import app

    with TestClient(app) as client:
        ready = client.get("/ready")
        eligible = client.get("/generate/eligible")
        coverage = client.get("/defend/coverage-map")
        hitl = client.get("/identify/hitl")
        assert ready.status_code == eligible.status_code == coverage.status_code == hitl.status_code == 200
        ready_body = ready.json()
        assert ready_body["postgres"] is True
        assert ready_body["pgvector"] is True
        assert ready_body["llm"]["configured"] is True
        print(
            f"http_ready={ready_body['status']} "
            f"generate_eligible={eligible.json()['count']} "
            f"defend_techniques={coverage.json()['technique_count']} "
            f"hitl_pending={hitl.json()['count']}",
            flush=True,
        )


def main() -> None:
    load_project_env()

    stages = (
        ("[1/8] live configuration", _require_live_config),
        ("[2/8] catalog", _catalog),
        ("[3/8] seed atlas + catalog vectors", _seed_db),
    )
    for name, function in stages:
        done = _step(name)
        function()
        done()

    done = _step("[4/8] Tavily search + extract")
    hit, doc = _discover_document()
    done()

    done = _step("[5/8] pgvector document embedding")
    _pgvector_upsert(hit, doc)
    done()

    done = _step("[6/8] OmniRoute structured extraction")
    _llm_extract(hit, doc)
    done()

    done = _step("[7/8] live Identify graph + Librarian")
    _identify_graph_live()
    done()

    done = _step("[8/8] Generate/Defend + FastAPI smoke")
    _handoff()
    _http_smoke()
    done()

    print("\n=== ALL LIVE PRODUCT GATES PASSED ===", flush=True)


if __name__ == "__main__":
    main()
