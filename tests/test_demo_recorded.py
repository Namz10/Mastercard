"""Recorded booth packs — filesystem JSON only, no live search."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_recorded_score_has_metrics():
    client = TestClient(app)
    resp = client.get("/demo/recorded/score")
    if resp.status_code == 404:
        return
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "recall_at_op" in data["metrics"]
    assert "genuine_fp" in data["metrics"]
    assert data.get("model_run_id")


def test_recorded_identify_has_collect_first():
    client = TestClient(app)
    resp = client.get("/demo/recorded/identify")
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert events[0]["verb"] == "COLLECT"
    assert events[0]["t"] == 0
