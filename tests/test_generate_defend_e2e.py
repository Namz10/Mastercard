"""Phase 7 §5 — End-to-end Generate → Defend on tmp runs_dir.

All on tmp `runs_dir`, n_customers≈20, no Plan 08 (2400x120x90) execution.
Closes the full loop: Generate population → fit_champion → score_run → Loop M,
across the seed-42 / seed-43 boundary.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import pytest

from apps.api.db import init_db
from apps.api.seed import seed_catalog
from packages.eval.fit import fit_champion, score_run
from packages.eval.loop_m import run_loop_m
from packages.sim.runner import run_population


@pytest.fixture(scope="module")
def pop42(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-gd")
    return run_population(
        None,
        run_id="gd-train",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


def _runs(pop: dict) -> Path:
    return Path(pop["parquet_path"]).parent.parent


def test_gd1_generate_fit_score_metrics(pop42: dict, tmp_path: Path):
    """GD.1 — run_population → fit_champion → score_run; sidecar world_seed==42 and
    Phase-2 metrics keys present."""
    runs = _runs(pop42)
    models = tmp_path / "models"
    fit_champion("gd-train", world_seed=42, runs_dir=runs, models_dir=models)
    scored = score_run("gd-train", model_run_id="gd-train", runs_dir=runs, models_dir=models)

    sidecar = json.loads((runs / "gd-train" / "sidecar.json").read_text(encoding="utf-8"))
    assert sidecar["world_seed"] == 42
    metrics = scored["metrics"]
    for key in ("ap_by_family", "n_pos", "not_comparable", "tpr_at_fpr", "genuine_fp",
                "f1_at_op", "app_ablation", "authgate_ms", "mule_entity_recall"):
        assert key in metrics


def test_gd2_train_invoice_rows_beneficiary_changed(pop42: dict):
    """GD.2 — train parquet keeps invoice cols; invoice rows have beneficiary_changed True."""
    runs = _runs(pop42)
    train = pd.read_parquet(runs / "gd-train" / "train.parquet")
    for col in ("beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag"):
        assert col in train.columns
    invoice = train[train["label_family"].astype(str) == "invoice_fraud"]
    if len(invoice) > 0:
        assert invoice["beneficiary_changed"].any(), "invoice_fraud must include some beneficiary_changed rows"
        assert not invoice["beneficiary_changed"].all(), (
            "invoice_fraud must not be 100% beneficiary_changed (E1 hard-negatives)"
        )


def test_gd3_seed43_all_rows_score_no_overwrite(pop42: dict, tmp_path: Path):
    """GD.3 — second pop at world_seed=43, score_run(all_rows=True) reports the seed-43
    run; the seed-42 train parquet mtime is unchanged (score never overwrites a run)."""
    runs = _runs(pop42)
    models = tmp_path / "models"
    fit_champion("gd-train", world_seed=42, runs_dir=runs, models_dir=models)

    pop43 = run_population(
        None,
        run_id="gd-gtest",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=43,
        pin=True,
        runs_dir=runs,
    )
    runs43 = Path(pop43["parquet_path"]).parent.parent

    seed42_parquet = runs / "gd-train" / "train.parquet"
    mtime_before = seed42_parquet.stat().st_mtime_ns
    time.sleep(0.01)

    scored = score_run("gd-gtest", model_run_id="gd-train",
                       runs_dir=runs, models_dir=models, all_rows=True)

    assert scored["metrics"]["protocol"] == "g_test_full_population"
    assert scored["gtest"]["world_seed"] == 43
    mtime_after = seed42_parquet.stat().st_mtime_ns
    assert mtime_after == mtime_before, "score_run(all_rows=True) must not rewrite the seed-42 parquet"
    seed43_sidecar = json.loads((runs43 / "gd-gtest" / "sidecar.json").read_text(encoding="utf-8"))
    assert seed43_sidecar["world_seed"] == 43


def test_gd4_loop_m_extra_disjoint_from_gtest(pop42: dict, tmp_path: Path):
    """GD.4 — run_loop_m app_fraud with train_seed=42, gtest_seed=48 produces the
    documented extra sidecar seed 10049 and extra ids disjoint from the G-test ids."""
    runs = _runs(pop42)
    models = tmp_path / "models"
    body = run_loop_m(
        "gd-train",
        "app_fraud",
        train_seed=42,
        gtest_seed=48,
        family_chosen_from_slice="gdev44",
        runs_dir=runs,
        models_dir=models,
    )
    assert body["gtest_seed"] == 48
    assert body["extra_seed"] == 42 + 10_007 == 10049

    # extra ids disjoint from G-test ids
    gtest_split = pd.read_parquet(runs / body["gtest_run_id"] / "split.parquet")
    extra_tr = pd.read_parquet(runs / body["run_id"] / "split.parquet")
    aug_tr = pd.read_parquet(runs / f"{body['run_id']}__loopm-train" / "split.parquet")
    extra_ids = set(aug_tr["event_id"].astype(str)) - set(extra_tr["event_id"].astype(str))
    assert extra_ids, "Loop M must add extra rows"
    assert all(str(i).startswith("evt-lm-") for i in extra_ids)
    assert extra_ids.isdisjoint(set(gtest_split["event_id"].astype(str)))


def test_gd5_coverage_24_and_t07_named_gap(postgres_required, tmp_path):
    """GD.5 — GET coverage after generate + seed catalog: 24 cells; T07 named_gap."""
    from fastapi.testclient import TestClient

    init_db()
    seed_catalog(reset=True)
    from apps.api.main import app

    with TestClient(app) as client:
        cov = client.get("/defend/coverage-map")
        assert cov.status_code == 200
        data = cov.json()
        assert data["technique_count"] == 24
        assert len(data["cells"]) == 24
        t07 = next(c for c in data["cells"] if c["technique_id"] == "T07")
        assert t07["coverage_status"] == "named_gap"
