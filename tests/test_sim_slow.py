"""Phase G — 50k-row smoke + APP flag ablation (Plan 08 lock 5 items 11–12)."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pytest

from packages.sim.ablation import APP_FLAG_COLS, ablation_report
from packages.sim.export import assert_train_schema
from packages.sim.inject.mix import apply_mix
from packages.sim.runner import run_population
from packages.sim.world import generate_quiet_world

ABLATION_DOC = Path(__file__).resolve().parents[1] / "Docs" / "generate_app_ablation.md"


@pytest.mark.slow
def test_50k_row_smoke_not_stub(tmp_path: Path):
    t0 = time.perf_counter()
    result = run_population(
        None,
        run_id="slow-50k",
        n_customers=420,
        n_merchants=40,
        sim_days=90,
        world_seed=42,
        runs_dir=tmp_path / "runs",
        pin=True,
    )
    elapsed = time.perf_counter() - t0
    n = result["event_count"]
    assert n > 1, "still the 1-row injector stub"
    assert n >= 50_000
    assert result["mode"] == "population"
    assert "simulatable_signals" not in result
    assert_train_schema(result["parquet_path"])
    # Plan: do not fail CI on ~6 minutes; do fail a hang / stub.
    assert elapsed < 900
    _ = elapsed


@pytest.mark.slow
def test_app_flag_ablation_metric_is_reported():
    rng = np.random.default_rng(42)
    world = generate_quiet_world(world_seed=42, n_customers=80, n_merchants=16, sim_days=45)
    apply_mix(world, rng, target_rate=0.02, pin=True)
    report = ablation_report(world.events)
    assert report["n_rows"] > 1
    with_ap = report["with_app_flags"]["average_precision"]
    without_ap = report["without_app_flags"]["average_precision"]
    assert report["app_flags"] == list(APP_FLAG_COLS)
    assert report["split"] == "time_cut_first_2_3"
    assert "average_precision" in report["with_app_flags"]
    assert "roc_auc" in report["without_app_flags"]
    assert report["with_app_flags"]["n_app_test"] >= 1
    assert np.isfinite(with_ap)
    assert np.isfinite(without_ap)
    assert "is_authorized_push is not a feature" in report["note"]
    assert ABLATION_DOC.is_file()
    text = ABLATION_DOC.read_text(encoding="utf-8")
    assert "synthetic session flags" in text.lower()
    assert "lab" in text.lower()
    _ = report["app_metric_died_without_synthetic_flags"]
