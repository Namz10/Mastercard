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
    assert data.get("model_run_id") == "v1-train-46__loopm-train"
    m = data["metrics"]
    assert abs(m["recall_at_op"] - 0.9851609657947686) < 0.001
    assert m["genuine_fp"] < 0.001
    tpr = m.get("tpr_at_fpr") or {}
    recalls = []
    for entry in tpr.values():
        if isinstance(entry, dict):
            recalls.append(float(entry.get("tpr", 0)))
        else:
            recalls.append(float(entry))
    if len(recalls) >= 2:
        assert max(recalls) - min(recalls) > 0.01, "frozen curve must not be a flat line"
    entry_01 = tpr.get("0.001")
    if isinstance(entry_01, dict):
        assert abs(float(entry_01.get("tpr", 0)) - 0.9867) < 0.001


def test_recorded_identify_has_collect_first():
    client = TestClient(app)
    resp = client.get("/demo/recorded/identify")
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert events[0]["verb"] == "COLLECT"
    assert events[0]["t"] == 0
