"""Plan 12 Phase D — POST /defend/fit + /score, metrics keys, hang guard."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.db import init_db
from apps.api.main import app
from apps.api.seed import seed_catalog
from packages.sim.export import TRAIN_DENYLIST, RUNS_DIR
from packages.sim.runner import run_population


def test_defend_fit_and_score_http(postgres_required, tmp_path):
    init_db()
    seed_catalog(reset=True)
    run_id = "defend-cd-http"
    run_population(
        None,
        run_id=run_id,
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=RUNS_DIR,
    )
    _ = tmp_path
    with TestClient(app) as client:
        fit = client.post("/defend/fit", json={"run_id": run_id, "world_seed": 42})
        assert fit.status_code == 200, fit.text
        fit_body = fit.json()
        assert fit_body["metrics"]["split"] == "time_cut_2_3_plus_entity_holdout"
        score = client.post("/defend/score", json={"run_id": run_id, "model_run_id": run_id})
        assert score.status_code == 200, score.text
        body = score.json()
        metrics = body["metrics"]
        for key in (
            "ap_by_family",
            "tpr_at_fpr",
            "genuine_fp",
            "f1_at_op",
            "app_ablation",
            "authgate_ms",
            "mule_entity_recall",
            "pass",
        ):
            assert key in metrics
        assert "p99_ms_per_row" in metrics["authgate_ms"]
        assert metrics["authgate_ms"]["batch_seconds_1k"] < 120
        assert "action_histogram" in body
        blob = json.dumps(body)
        assert "simulatable_signals" not in blob
        for banned in TRAIN_DENYLIST:
            assert f'"{banned}"' not in blob
        cov = client.get("/defend/coverage-map")
        assert cov.status_code == 200
        assert cov.json()["technique_count"] == 24
        miss = client.post("/defend/miss/t13-upi-impersonation-app")
        assert miss.status_code == 200
        assert miss.json()["status"] == "open"
        loop = client.post(
            "/defend/loop-m",
            json={
                "run_id": run_id,
                "miss_family": "app_fraud",
                "train_seed": 42,
                "gtest_seed": 43,
            },
        )
        assert loop.status_code == 200, loop.text
        lm = loop.json()
        assert lm["catalog_solved"] is False
        assert lm["catalog_status"] == "open"
        assert lm["train_seed"] != lm["gtest_seed"]
        assert "ap_verdict" in lm["comparison"]
        assert "genuine_fp_ok" in lm["comparison"]
        miss2 = client.post("/defend/miss/t13-upi-impersonation-app")
        assert miss2.status_code == 200
        assert miss2.json()["status"] == "open"
        lm_blob = json.dumps(lm)
        assert "simulatable_signals" not in lm_blob
        assert "world_seed" not in lm_blob
        assert "knobs_used" not in lm_blob

