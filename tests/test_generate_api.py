"""Plan 12 Phase 0.2 — HTTP Generate (no Identify calibrate-world)."""

from __future__ import annotations

from pathlib import Path

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.db import init_db
from apps.api.main import app
from apps.api.seed import seed_catalog


@pytest.fixture()
def client(postgres_required):
    init_db()
    seed_catalog(reset=True)
    with TestClient(app) as test_client:
        yield test_client


def test_post_population_small_t13(client: TestClient):
    resp = client.post(
        "/generate/population",
        json={
            "vector_id": "t13-upi-impersonation-app",
            "run_id": "http-pop-t13",
            "n_customers": 16,
            "n_merchants": 8,
            "sim_days": 40,
            "world_seed": 42,
            "pin": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["event_count"] > 1
    assert "simulatable_signals" not in body
    assert "fidelity" in body
    assert Path(body["parquet_path"]).is_file()
    assert body.get("split_path")
    assert Path(body["split_path"]).is_file()


def test_post_canary_default_campaign(client: TestClient):
    resp = client.post(
        "/generate/canary",
        json={
            "campaign_id": "fincen-fin-2024-alert004",
            "run_id": "http-canary",
            "n_customers": 12,
            "n_merchants": 6,
            "sim_days": 180,
            "world_seed": 42,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    stages = body["lifecycle_stages_logged"]
    assert [s["lifecycle_stage"] for s in stages] == [
        "onboarding_kyc",
        "account_access_ato",
        "payment_initiation",
        "disbursement_mule",
    ]
    parties = {s["party_id"] for s in stages}
    assert len(parties) == 1
    assert "simulatable_signals" not in body


def test_post_calibrate_world_fixture_and_pdf(client: TestClient):
    good = client.post("/generate/calibrate-world", json={"fixture_id": "good_p2m_table"})
    assert good.status_code == 200, good.text
    assert good.json()["status"] == "propose"
    pdf = client.post("/generate/calibrate-world", json={"fixture_id": "npci_stats.pdf"})
    assert pdf.status_code == 200, pdf.text
    assert pdf.json()["status"] == "abstain"


def test_no_identify_calibrate_world(client: TestClient):
    resp = client.post("/identify/calibrate-world", json={"fixture_id": "good_p2m_table"})
    assert resp.status_code in {404, 405}


def test_post_population_stream_emits_progress(client: TestClient):
    resp = client.post(
        "/generate/population/stream",
        json={
            "n_customers": 40,
            "n_merchants": 8,
            "sim_days": 14,
            "world_seed": 42,
            "pin": True,
        },
    )
    assert resp.status_code == 200, resp.text
    events = []
    for chunk in resp.text.split("\n\n"):
        line = chunk.strip()
        if not line.startswith("data:"):
            continue
        events.append(json.loads(line[5:].strip()))
    progress = [e for e in events if e.get("status") == "progress"]
    assert len(progress) >= 3, [e.get("body") for e in progress]
    done = [e for e in events if e.get("status") == "done"]
    assert len(done) == 1
    assert done[0]["result"]["event_count"] > 0
    with_artifacts = [e for e in progress if e.get("artifacts")]
    assert with_artifacts, "expected progress artifacts for UI counters"
