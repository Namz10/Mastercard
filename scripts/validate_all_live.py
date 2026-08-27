#!/usr/bin/env python3
"""Live validation: Tavily + OmniRoute + Postgres pgvector + pytest."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.env import env_configured, load_project_env

LIVE_ENV = {
    "IDENTIFY_LIVE_SEARCH": "true",
    "IDENTIFY_MAX_DOCS": "1",
    "PYTHONPATH": str(ROOT),
}


def _apply_live_env() -> None:
    load_project_env()
    for key, value in LIVE_ENV.items():
        os.environ[key] = value


def _step(name: str) -> None:
    print(f"\n=== {name} ===", flush=True)


def _run(cmd: list[str] | str, *, shell: bool = False) -> None:
    if isinstance(cmd, str):
        print(f"$ {cmd}", flush=True)
    else:
        print(f"$ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, shell=shell, check=True, cwd=ROOT, env=os.environ.copy())


def _require_keys() -> None:
    missing = []
    if not env_configured("TAVILY_API_KEY"):
        missing.append("TAVILY_API_KEY")
    if not env_configured("AEGIS_LLM_API_KEY"):
        missing.append("AEGIS_LLM_API_KEY")
    if missing:
        raise SystemExit(f"Missing .env keys for live validate: {', '.join(missing)}")


def _docker_up() -> None:
    _run(["docker", "compose", "up", "-d", "postgres", "--wait"])


def _catalog() -> None:
    from packages.catalog.loader import catalog_summary, load_catalog_yaml

    summary = catalog_summary(load_catalog_yaml())
    print(summary, flush=True)
    assert summary["count"] >= 28 and not summary["missing_techniques"]


def _live_tavily() -> None:
    from packages.osint.search import tavily_search

    results = tavily_search(max_results=3, search_depth="basic")
    print(f"tavily_results={len(results)}", flush=True)
    for r in results:
        print(f"  {r.source_domain} {r.url[:80]}", flush=True)
    assert len(results) >= 1


def _pgvector_upsert() -> None:
    from packages.agents.embeddings import embed_text
    from packages.osint.extract import extract_url
    from packages.osint.search import tavily_search
    from packages.osint.vector_store import COLLECTION_NAME, upsert_chunk

    hit = tavily_search(max_results=1)[0]
    doc = extract_url(hit.url)
    chunk = upsert_chunk(hit.url, doc.text, hit.source_domain, doc.extractor)
    vec = embed_text(doc.text[:500])
    print(f"embedding_dim={len(vec)} chunk_id={chunk.id} collection={COLLECTION_NAME}", flush=True)
    assert len(vec) == 384


def _llm_extract() -> None:
    from packages.agents.llm import extract_from_document
    from packages.osint.extract import extract_url
    from packages.osint.search import tavily_search

    hit = tavily_search(max_results=1)[0]
    doc = extract_url(hit.url)
    spec = extract_from_document(doc.text, hit.url, hit.source_domain)
    print(f"extraction_source={spec.get('extraction_source')} name={spec.get('name')}", flush=True)
    assert spec.get("extraction_source") == "llm", spec.get("abstain_reason") or spec.get("llm_last_error")


def _seed_db() -> None:
    from apps.api.seed import seed_catalog

    n = seed_catalog(reset=True)
    print(f"seeded {n} rows", flush=True)
    assert n >= 28


def _handoff() -> None:
    from apps.api.db import SessionLocal
    from packages.policy.coverage import build_coverage_map
    from packages.sim.runner import run_canary, run_population

    db = SessionLocal()
    try:
        pop = run_population(db, vector_id="t13-upi-impersonation-app", run_id="live-validate-pop")
        assert pop["injector_id"] == "app_session"
        canary = run_canary(db, campaign_id="fincen-fin-2024-alert004", run_id="live-validate-canary")
        assert canary["event_count"] == 4
        cmap = build_coverage_map(db)
        assert cmap["technique_count"] == 24
        t13 = next(c for c in cmap["cells"] if c["technique_id"] == "T13")
        assert t13["coverage_status"] in {"live_rule", "draft_rule"}
        print(f"handoff OK pop={pop['vector_id']} canary_stages={canary['event_count']}", flush=True)
    finally:
        db.close()


def _identify_graph_live() -> None:
    from packages.agents.identify_graph import run_identify_graph

    result = run_identify_graph(run_id="validate-all-live", topic="deepfake payment fraud UPI")
    urls = result.get("candidate_urls") or []
    docs = result.get("extracted_docs") or []
    proposed = result.get("proposed_specs") or []
    errors = result.get("errors") or []
    print(f"scout_urls={len(urls)} extracted={len(docs)} proposed={len(proposed)}", flush=True)
    if errors:
        print("errors:", errors[:5], flush=True)
    assert len(urls) >= 1, "scout returned no URLs"
    assert len(docs) >= 1, "extractor produced no docs"


def _pytest() -> None:
    _run([sys.executable, "-m", "pytest", "tests/", "-q", "-m", "not live_llm"])


def main() -> None:
    _apply_live_env()
    _step("[0] check API keys")
    _require_keys()

    _step("[1/8] docker postgres (pgvector)")
    _docker_up()

    _step("[2/8] catalog")
    _catalog()

    _step("[3/8] live Tavily search")
    _live_tavily()

    _step("[4/8] pgvector + embeddings upsert")
    _pgvector_upsert()

    _step("[5/8] OmniRoute extraction")
    _llm_extract()

    _step("[6/8] postgres seed + generate/defend handoff")
    _seed_db()
    _handoff()

    _step("[7/8] full identify graph (live Tavily + LLM + librarian)")
    _identify_graph_live()

    _step("[8/8] pytest")
    _pytest()

    print("\n=== ALL LIVE GATES PASSED ===", flush=True)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc
