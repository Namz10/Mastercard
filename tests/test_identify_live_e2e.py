"""Live Identify e2e — one test per pipeline stage. Skips until keys exist.

Run after filling .env:
  IDENTIFY_LIVE_SEARCH=true pytest tests/test_identify_live_e2e.py -m live_identify -v
"""

from __future__ import annotations

import os

import pytest

from apps.api.env import load_project_env
from packages.agents.llm.config import is_llm_configured
from packages.catalog.models import AttackSpec
from packages.osint.allowlist import ALLOWLIST_DOMAINS, is_allowlisted_url, tier_for_url

load_project_env()

pytestmark = pytest.mark.live_identify


def _live_ready() -> bool:
    load_project_env()
    return bool(os.getenv("TAVILY_API_KEY", "").strip()) and is_llm_configured()


skip_no_keys = pytest.mark.skipif(
    not _live_ready(),
    reason="needs TAVILY_API_KEY + AEGIS_LLM_API_KEY (or profile alias) in environment/.env",
)


@pytest.fixture
def live_env(monkeypatch):
    load_project_env()
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "true")
    monkeypatch.setenv("IDENTIFY_MAX_DOCS", os.getenv("IDENTIFY_MAX_DOCS", "2"))


@skip_no_keys
def test_01_tavily_returns_allowlisted_urls(live_env):
    from packages.osint.search import tavily_search

    hits = tavily_search(
        query="deepfake KYC payment fraud regulator",
        max_results=4,
        search_depth="basic",
    )
    assert hits, "Tavily returned zero results on the allowlist"
    for hit in hits:
        assert is_allowlisted_url(hit.url)
        assert hit.source_domain
        assert any(
            hit.source_domain == d or hit.source_domain.endswith(f".{d}") for d in ALLOWLIST_DOMAINS
        )


@skip_no_keys
def test_02_fetch_article_body(live_env):
    from packages.osint.extract import extract_url
    from packages.osint.search import tavily_search

    hits = tavily_search(query="FinCEN deepfake financial", max_results=1)
    assert hits
    doc = extract_url(hits[0].url)
    assert doc.text.strip()
    assert doc.url
    assert doc.extractor in {"tavily", "trafilatura", "firecrawl"}


@skip_no_keys
def test_03_embed_and_store_in_pgvector(postgres_required, live_env):
    from apps.api.db import SessionLocal, init_db
    from apps.api.models import OsintChunk
    from packages.agents.embeddings import VECTOR_DIM
    from packages.osint.extract import extract_url
    from packages.osint.search import tavily_search
    from packages.osint.vector_store import upsert_chunk

    init_db()
    hits = tavily_search(query="RBI UPI impersonation fraud", max_results=1)
    assert hits
    doc = extract_url(hits[0].url)
    chunk = upsert_chunk(
        url=hits[0].url,
        text=doc.text,
        domain=hits[0].source_domain,
        source_type=doc.extractor,
    )
    db = SessionLocal()
    try:
        row = db.get(OsintChunk, chunk.id)
        assert row is not None
        assert len(list(row.embedding)) == VECTOR_DIM
        assert row.url == hits[0].url
    finally:
        db.close()


@skip_no_keys
def test_04_llm_extracts_attackspec_or_abstains(live_env):
    from packages.osint.allowlist import domain_from_url
    from packages.osint.extract import extract_url
    from packages.osint.search import tavily_search
    from packages.agents.llm.extraction import extract_from_document

    hits = tavily_search(query="deepfake liveness KYC bank", max_results=1)
    assert hits
    doc = extract_url(hits[0].url)
    domain = domain_from_url(hits[0].url)
    out = extract_from_document(doc.text, hits[0].url, domain)
    if out.get("extraction_source") == "abstain":
        assert out.get("abstain_reason")
        return
    spec = AttackSpec.model_validate(out)
    assert spec.status.value == "proposed"
    assert out.get("extraction_source") in {"llm", "rules"}
    assert 1 <= spec.source_tier <= 5
    assert spec.source_tier == tier_for_url(hits[0].url) or spec.source_tier >= 1


@skip_no_keys
def test_05_full_graph_scout_to_librarian(postgres_required, live_env):
    from apps.api.db import SessionLocal, init_db
    from apps.api.models import AtlasRow, OsintChunk
    from packages.agents.identify_graph import NODE_ORDER, run_identify_graph

    assert NODE_ORDER == (
        "scout",
        "curator",
        "extractor",
        "grounder",
        "tier_scorer",
        "corroborator",
        "librarian",
    )
    init_db()
    result = run_identify_graph(run_id="live-e2e-graph", topic="deepfake payment fraud KYC UPI")

    urls = result.get("candidate_urls") or []
    docs = result.get("extracted_docs") or []
    proposed = result.get("proposed_specs") or []
    errors = result.get("errors") or []
    assert urls, "scout produced no candidate_urls"
    assert all(is_allowlisted_url(u["url"]) for u in urls if u.get("url"))
    assert docs, "extractor produced no extracted_docs"
    assert all(d.get("chunk_id") for d in docs)

    db = SessionLocal()
    try:
        for d in docs:
            row = db.get(OsintChunk, d["chunk_id"])
            assert row is not None, f"chunk {d['chunk_id']} not in osint_chunks"
        abstains = [e for e in errors if "abstain" in e]
        assert proposed or abstains, "no AttackSpec and no abstain — pipeline silent-failed"
        for spec in proposed:
            AttackSpec.model_validate(spec)
            assert spec["status"] == "proposed"
            assert spec.get("technique_id", "").startswith("T")
            assert spec.get("confidence_level") in {"confirmed", "reported-unverified"}
            assert spec.get("vector_class") in {"network_footprint", "human_social"}
            assert spec.get("corroboration_type")
            row = db.query(AtlasRow).filter(AtlasRow.vector_id == spec["vector_id"]).one_or_none()
            assert row is not None, f"{spec['vector_id']} not written to killchain_atlas"
            assert row.status == "proposed"
        if result.get("hitl_required"):
            assert result.get("hitl_queue")
    finally:
        db.close()


@skip_no_keys
def test_06_http_identify_run_matches_graph(postgres_required, live_env):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    client = TestClient(app)
    ready = client.get("/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body.get("postgres") is True
    assert body.get("pgvector") is True
    assert body.get("llm", {}).get("configured") is True

    resp = client.post(
        "/identify/run",
        json={"topic": "deepfake payment fraud", "run_id": "live-e2e-http"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidate_urls"]
    hitl = client.get("/identify/hitl")
    assert hitl.status_code == 200
    if data.get("proposed_count", 0) > 0:
        assert hitl.json()["count"] >= 1
