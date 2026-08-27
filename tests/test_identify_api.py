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
