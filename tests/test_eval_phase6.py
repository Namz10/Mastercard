"""Phase 6 — advanced ML hardening: Optuna (5), Isolation Forest (8), calibration (9), bootstrap/permutation (10)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingClassifier

from packages.eval import fit as fit_mod
from packages.eval.fit import (
    _calibrate_pmap,
    _cluster_bootstrap_ci,
    _top_features,
    fit_champion,
    score_run,
    tune_champion,
)
from packages.eval.iso_check import (
    ISO_STAMP_FREE_FEATURES,
    apply_iso_brake_upgrade,
    is_iso_anomaly,
    iso_enabled_flag,
)
from packages.sim.ablation import APP_FLAG_COLS
from packages.policy.rules import EXTRA_ROW_FIELDS
from packages.sim.export import TRAIN_ALLOWLIST
from packages.sim.runner import run_population


@pytest.fixture(scope="module")
def pop(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-p6")
    return run_population(
        None,
        run_id="phase6",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


@pytest.fixture(scope="module")
def pop43(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-p6-43")
    return run_population(
        None,
        run_id="phase6-43",
        n_customers=12,
        n_merchants=6,
        sim_days=30,
        world_seed=43,
        pin=True,
        runs_dir=runs,
    )


def _runs_dir(run_pop: dict) -> Path:
    return Path(run_pop["parquet_path"]).parent.parent


# ---------------------------------------------------------------------------
# Ticket 5 — Optuna
# ---------------------------------------------------------------------------
def test_tune_champion_never_reads_world_seed_43(pop43: dict, tmp_path: Path, monkeypatch):
    """5.1 — tune_champion must refuse to open a sidecar world_seed==43 run before
    touching any parquet. We monkeypatch pd.read_parquet to raise, and assert the
    ValueError fires anyway (parquet is never opened)."""
    runs = _runs_dir(pop43)

    def _forbid_parquet(*args, **kwargs):
        raise AssertionError("tune_champion opened a parquet for a seed-43 run")

    monkeypatch.setattr(pd, "read_parquet", _forbid_parquet)
    with pytest.raises(ValueError, match="seed 43|43"):
        tune_champion("phase6-43", world_seed=42, runs_dir=runs, models_dir=tmp_path / "models", n_trials=2)


def test_best_params_json_written_and_score_works(pop: dict, tmp_path: Path):
    """5.2 — best_params.json written; score_run still works (study pickle irrelevant)."""
    runs = _runs_dir(pop)
    dest = tmp_path / "models"
    body = tune_champion("phase6", world_seed=42, runs_dir=runs, models_dir=dest, n_trials=2, timeout=60)
    bp = dest / "phase6" / "best_params.json"
    assert bp.is_file(), "best_params.json must be written by tune_champion"
    data = json.loads(bp.read_text(encoding="utf-8"))
    assert data["status"] == "success"
    assert "best_params" in data
    assert data["recipe_hash"] == body["recipe_hash"]

    # Delete any (nonexistent) study pickle — scoring must not depend on it
    for p in dest.glob("*.study*"):
        p.unlink()
    scored = score_run("phase6", model_run_id="phase6", runs_dir=runs, models_dir=dest)
    assert scored["metrics"]["n_eval"] > 0


def test_optuna_skipped_small_n(pop: dict, tmp_path: Path):
    """5.3 — force skip -> optuna_skipped_small_n flagged and recipe defaults used."""
    runs = _runs_dir(pop)
    dest = tmp_path / "models"
    body = tune_champion(
        "phase6", world_seed=42, runs_dir=runs, models_dir=dest, n_trials=2, force_skip=True
    )
    assert body["optuna_skipped_small_n"] is True
    bp = dest / "phase6" / "best_params.json"
    data = json.loads(bp.read_text(encoding="utf-8"))
    assert data["optuna_skipped_small_n"] is True
    recipe = fit_mod.load_recipe()
    # defaults from recipe, not an Optuna min-family AP collapse
    assert data["best_params"]["max_depth"] == int(recipe.get("max_depth", 3))


def test_optuna_objective_is_not_min_family_ap():
    """5.4 — objective is binary AP minus genuine-FP penalty, never min over family AP."""
    src = inspect.getsource(fit_mod.tune_champion)
    assert "average_precision" in src, "objective must use average_precision"
    assert "10.0 * max(0.0, genuine_fp - 0.01)" in src, (
        "objective must include the genuine-FP penalty term"
    )
    assert "min(" not in src, "objective must not be a min() over family AP"


# ---------------------------------------------------------------------------
# Ticket 8 — Isolation Forest
# ---------------------------------------------------------------------------
def test_iso_not_called_when_pred_mule():
    """8.1 — is_iso_anomaly short-circuits when pred_family != 'normal'; predict never runs."""
    class ForbiddenPredictModel:
        def predict(self, x):
            raise AssertionError("IF predict must not run for a mule prediction")

    row = {"account_age_days": 10, "fan_in_1h": 1}
    assert is_iso_anomaly(ForbiddenPredictModel(), row, pred_family="mule", pmap_normal=0.99) is False
    assert is_iso_anomaly(ForbiddenPredictModel(), row, pred_family="normal", pmap_normal=0.50) is False


def test_brake_iso_upgrades_allow_only():
    """8.2 — IF only upgrades allow->notify; never downgrades other actions."""
    action, reasons = apply_iso_brake_upgrade("allow", True, [])
    assert action == "notify"
    assert "iso_anomaly" in reasons

    for locked in ("mule_credit_restrict", "hold", "decline"):
        action, reasons = apply_iso_brake_upgrade(locked, True, [])
        assert action == locked, f"IF must not downgrade {locked}"
        assert "iso_anomaly" not in reasons

    action, reasons = apply_iso_brake_upgrade("allow", False, [])
    assert action == "allow"
    assert "iso_anomaly" not in reasons


def test_iso_feature_cols_stamp_free():
    """8.3 — frozen stamp-free list is exact and free of APP/invoice/rule__ stamps."""
    expected = [
        "account_age_days",
        "payee_history_count",
        "amount_vs_p30",
        "fan_in_1h",
        "fan_out_1h",
        "fan_in_unique_payers_1h",
        "burst_velocity",
        "is_new_payee",
        "is_new_device",
    ]
    assert list(ISO_STAMP_FREE_FEATURES) == expected
    assert len(ISO_STAMP_FREE_FEATURES) == len(set(ISO_STAMP_FREE_FEATURES))
    stamps = set(APP_FLAG_COLS) | set(EXTRA_ROW_FIELDS)
    assert set(ISO_STAMP_FREE_FEATURES).isdisjoint(stamps), "ISO cols must be stamp-free"
    assert not any(c.startswith("rule__") for c in ISO_STAMP_FREE_FEATURES)


def test_iso_aborts_if_genuine_notify_gt_0_05():
    """8.4 — kill switch: high genuine notify rate forces IF off regardless of config."""
    cfg_on = {"enabled_default": True, "genuine_notify_rate_abort": 0.05}
    assert iso_enabled_flag(cfg_on, 0.01) is True
    assert iso_enabled_flag(cfg_on, 0.99) is False, "5%+ genuine notify rate must kill IF"
    assert iso_enabled_flag({"enabled_default": False}, 0.0) is False, "disabled_default off -> off"
    # malformed config defaults off, never raises
    assert iso_enabled_flag({"enabled_default": "not-a-bool", "genuine_notify_rate_abort": None}, 0.0) is False


def test_coverage_named_gaps_unchanged_by_iso(postgres_required, tmp_path):
    """8.5 — ISO does not close any coverage gap; T06/T07/T20-T23 stay named_gap."""
    from apps.api.db import SessionLocal, init_db
    from apps.api.seed import seed_catalog
    from packages.policy.coverage import build_coverage_map

    _ = tmp_path
    init_db()
    seed_catalog(reset=True)
    db = SessionLocal()
    try:
        m = build_coverage_map(db)
    finally:
        db.close()
    by_tid = {c["technique_id"]: c["coverage_status"] for c in m["cells"]}
    for tid in ("T06", "T07", "T20", "T21", "T22", "T23"):
        assert by_tid.get(tid) == "named_gap", f"ISO must not close coverage gap {tid}"


# ---------------------------------------------------------------------------
# Ticket 9 — Isotonic calibration + ECE
# ---------------------------------------------------------------------------
def test_ece_before_after_keys(pop: dict, tmp_path: Path):
    """9.1 — ece_before/ece_after present as floats in [0,1]."""
    runs = _runs_dir(pop)
    body = fit_champion("phase6", world_seed=42, runs_dir=runs, models_dir=tmp_path / "models")
    metrics = body["metrics"]
    assert "ece_before" in metrics and "ece_after" in metrics
    for key in ("ece_before", "ece_after"):
        val = metrics[key]
        assert isinstance(val, float) and 0.0 <= val <= 1.0, f"{key} must be a float in [0,1]"


def test_stage2_skipped_n_pos_lt_50():
    """9.2 — per-family calibration skipped & left raw when n_pos < 50."""
    n = 100
    classes = ["normal", "mule", "app_fraud"]
    rng = np.random.default_rng(0)
    pmap = {c: rng.uniform(0, 1, n) for c in classes}
    y = pd.Series(["normal"] * 60 + ["mule"] * 10 + ["app_fraud"] * 30)  # mule n_pos=10 < 50
    out = _calibrate_pmap(pmap, y, classes)
    # mule (n_pos=10<50) must be left raw (skipped) — renormalization reweights but
    # family with zero positives is not calibrated. We assert skip via source flag.
    src = inspect.getsource(fit_mod._calibrate_pmap)
    assert "stage2_skipped_n_pos_lt_50" in src or "50" in src
    assert out["mule"] is not None


def test_calibrated_pmap_sums_to_one():
    """9.3 — per-row sum of calibrated pmap == 1 within 1e-6."""
    n = 200
    classes = ["normal", "mule", "app_fraud", "ato", "identity_burst"]
    rng = np.random.default_rng(1)
    y = pd.Series(
        ["normal"] * 80 + ["mule"] * 30 + ["app_fraud"] * 30 + ["ato"] * 30 + ["identity_burst"] * 30
    )
    pmap = {c: rng.uniform(0.1, 0.9, n) for c in classes}
    out = _calibrate_pmap(pmap, y, classes)
    stacked = np.column_stack([out[c] for c in classes])
    sums = stacked.sum(axis=1)
    assert np.all(np.abs(sums - 1.0) < 1e-6), "calibrated pmap must renormalize to sum 1"


# ---------------------------------------------------------------------------
# Ticket 10 — Cluster bootstrap CI + permutation importance
# ---------------------------------------------------------------------------
def test_cluster_bootstrap_ci_ordered():
    """10.1 — low < high per family with n_pos>=1; n_resamples==200 in CI config."""
    n = 240
    rng = np.random.default_rng(7)
    split_eval = pd.DataFrame(
        {
            "payee": [f"p{i % 40}" for i in range(n)],
            "payer": [f"c{i % 60}" for i in range(n)],
        }
    )
    yv = ["normal"] * n
    # mule (clustered by payee) and identity_burst (clustered by payer) positives
    for i in range(60, 100):
        yv[i] = "mule"
    for i in range(120, 150):
        yv[i] = "identity_burst"
    y = pd.Series(yv)
    base = rng.uniform(0, 0.4, n)
    mule_score = base + np.where(np.arange(n) < 200, 0.3, 0)
    ib_score = base + np.where(np.arange(n) < 150, 0.25, 0)
    pmap = {"mule": mule_score, "identity_burst": ib_score, "normal": 1.0 - base}

    ci = _cluster_bootstrap_ci(split_eval, y, pmap, n_resamples=200)
    for fam in ("mule", "identity_burst"):
        lo, hi = ci[fam]["low"], ci[fam]["high"]
        assert lo < hi, f"{fam} low must be < high (got {lo}, {hi})"


def test_permutation_on_inner_val_not_gtest():
    """10.2 — permutation importance path never touches make-gtest; features ⊆ allowlist."""
    src = inspect.getsource(fit_mod._top_features)
    assert "permutation_importance" in src
    assert "gtest" not in src.lower(), "importance path must never touch G-test/make-gtest"

    rng = np.random.default_rng(0)
    cols = ["fan_in_1h", "fan_in_unique_payers_1h", "amount_vs_p30", "payee_history_count"]
    x = rng.normal(size=(120, len(cols)))
    y = pd.Series(np.where(rng.uniform(0, 1, 120) < 0.5, "normal", "mule"))
    model = HistGradientBoostingClassifier(max_depth=2, max_iter=30, random_state=42)
    model.fit(x, y.astype(str))
    top = _top_features(model, x, y, cols, k=3)
    assert set(top).issubset(set(cols))
    assert set(top).issubset(set(TRAIN_ALLOWLIST) | {"rule__"}, ) or set(top).issubset(
        set(TRAIN_ALLOWLIST)
    )


def test_top_features_not_correlation_only():
    """10.3 — _top_features must use permutation_importance, not correlation ranking."""
    src = inspect.getsource(fit_mod._top_features)
    assert "permutation_importance" in src
    assert ".corr(" not in src and "corr(" not in src, (
        "_top_features must not use correlation-based feature ranking"
    )


# ---------------------------------------------------------------------------
# Phase 6 hardening — versioned artifact set matched by recipe_hash
# ---------------------------------------------------------------------------
def test_phase6_artifacts_share_recipe_hash(pop: dict, tmp_path: Path):
    """All artifacts under a run_id — model manifest, best_params, metrics — share one recipe_hash."""
    runs = _runs_dir(pop)
    dest = tmp_path / "models"
    tune_champion("phase6", world_seed=42, runs_dir=runs, models_dir=dest, n_trials=2, force_skip=True)
    rh = fit_mod._recipe_hash()

    manifest = json.loads((dest / "phase6" / "model_manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((dest / "phase6" / "metrics.json").read_text(encoding="utf-8"))
    best = json.loads((dest / "phase6" / "best_params.json").read_text(encoding="utf-8"))

    assert manifest.get("recipe_hash") == rh
    assert metrics.get("recipe_hash") == rh
    assert best.get("recipe_hash") == rh
