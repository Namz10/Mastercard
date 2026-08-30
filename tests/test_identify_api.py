"""Identify API config and run response."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_identify_config_exposes_limits():
    client = TestClient(app)
    resp = client.get("/identify/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "limits" in data
    limits = data["limits"]
    assert "identify_max_docs" in limits
    assert "identify_curator_enabled" in limits
    assert data["identify_live_search"] is False


def test_identify_run_returns_curator_counts(postgres_required):
    client = TestClient(app)
    resp = client.post("/identify/run", json={"run_id": "api-unit-test", "topic": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert "scout_candidate_count" in data
    assert "curator_kept_count" in data
    assert data["proposed_count"] >= 1


def test_identify_stream_completes_without_fallback(postgres_required):
    """SSE stream should finish with PROPOSE done, not recorded fallback."""
    client = TestClient(app)
    with client.stream("POST", "/identify/run/stream", json={"run_id": "stream-unit", "topic": ""}) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text())
    assert '"fallback"' not in body
    assert '"verb": "PROPOSE"' in body or '"verb": "REPLAY"' in body
    assert '"status": "done"' in body


def test_hitl_includes_catalog_demo_rows(postgres_required):
    """Approved identify-* rows stay visible as in_catalog demo context."""
    client = TestClient(app)
    run = client.post("/identify/run", json={"run_id": "hitl-catalog-demo", "topic": ""}).json()
    specs = run.get("proposed_specs") or []
    if not specs:
        return
    vid = specs[0]["vector_id"]
    client.post(f"/identify/approve/{vid}", json={"action": "approve"})
    hitl = client.get("/identify/hitl").json()
    pending_ids = [i["vector_id"] for i in hitl["items"] if i.get("disposition") != "in_catalog"]
    assert vid not in pending_ids
    assert hitl.get("catalog_count", 0) >= 1
    assert any(i.get("disposition") == "in_catalog" and i["vector_id"] == vid for i in hitl["items"])


def test_hitl_dedupes_pending_rows(postgres_required):
    """GET /identify/hitl returns one row per technique+name+rail identity."""
    from apps.api.db import SessionLocal, init_db
    from packages.agents.librarian_db import merge_proposed_spec

    init_db()
    db = SessionLocal()
    base = {
        "technique_id": "T09",
        "name": "Dedupe test VKYC bypass (unit)",
        "one_liner": "x",
        "category": 2,
        "rail": "onboarding",
        "lifecycle_stage": "onboarding_kyc",
        "genai_modality": "video",
        "social_surface": "in_app",
        "actor_type": "consumer",
        "economic_class": "ATO",
        "is_authorized_push": False,
        "generate_mode": "name_only",
        "source_tier": 1,
        "confidence_level": "confirmed",
        "vector_class": "human_social",
        "source_urls": ["https://www.fincen.gov/a"],
        "status": "proposed",
    }
    merge_proposed_spec(db, {**base, "vector_id": "identify-dup-a"})
    merge_proposed_spec(db, {**base, "vector_id": "identify-dup-b"})
    db.close()

    client = TestClient(app)
    hitl = client.get("/identify/hitl").json()
    pending = [i for i in hitl["items"] if i.get("disposition") != "in_catalog"]
    dup_names = [i for i in pending if i.get("name") == base["name"]]
    assert len(dup_names) == 1


def test_librarian_skips_open_catalog_targets(postgres_required):
    """Re-running discover must not re-stage attacks already approved to catalog."""
    from apps.api.db import SessionLocal, init_db
    from apps.api.models import AtlasRow
    from packages.agents.librarian_db import merge_proposed_spec
    from packages.agents.nodes.librarian import librarian
    from packages.agents.state import empty_identify_state

    init_db()
    db = SessionLocal()
    spec = {
        "vector_id": "identify-open-skip-test",
        "technique_id": "T07",
        "name": "Card-testing botnet on payment APIs (identified)",
        "one_liner": "x",
        "category": 1,
        "rail": "card_cnp",
        "lifecycle_stage": "authorization",
        "genai_modality": "bot",
        "social_surface": "none",
        "actor_type": "consumer",
        "economic_class": "CNP",
        "is_authorized_push": False,
        "generate_mode": "name_only",
        "source_tier": 1,
        "confidence_level": "confirmed",
        "vector_class": "network_footprint",
        "source_urls": ["https://www.fincen.gov/a"],
        "status": "proposed",
        "simulator": {"injector_id": "graph_mule", "param_schema": {}},
    }
    merge_proposed_spec(db, spec)
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == spec["vector_id"]).one()
    row.status = "open"
    db.commit()
    db.close()

    state = empty_identify_state()
    state["proposed_specs"] = [{**spec, "status": "proposed"}]
    out = librarian(state)
    assert out["hitl_queue"] == []
    db = SessionLocal()
    try:
        row = db.query(AtlasRow).filter(AtlasRow.vector_id == spec["vector_id"]).one()
        assert row.status == "open"
    finally:
        db.close()

