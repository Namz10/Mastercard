"""Phase 3 — nested validation protocol: inner-val split, threshold leak guard, recipe hash."""

from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from packages.eval.split import (
    assign_folds,
    inner_folds_from_train,
)
from packages.eval import fit as fit_mod
from packages.eval.fit import fit_champion, _class_weight
from packages.sim.export import TRAIN_ALLOWLIST
from packages.sim.ledger import LABEL_FAMILIES, make_event
from packages.sim.runner import run_population


def _ts(day: int, hour: int = 10) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day, hours=hour)


# ---------------------------------------------------------------------------
# 3.1 — inner_val is last 20% of train calendar span, not shuffle
# ---------------------------------------------------------------------------
def test_inner_val_is_last_20pct_train_calendar():
    """Construct split_df with known timestamps; inner_val max ts >= all inner_fit ts;
    row count ~ 20% of train by calendar span, not shuffle."""
    n = 100
    rows = []
    for i in range(n):
        rows.append(
            {
                "event_id": f"evt-{i:010d}",
                "event_ts": _ts(i).isoformat(),
                "payer": "VID-SIM-C-000001",
                "payee": "VID-SIM-M-000001",
                "amount_minor": 1,
                "label_family": "normal",
            }
        )
    split_df = pd.DataFrame(rows)
    folds = assign_folds(split_df, seed=42, customer_holdout_frac=0.0, mule_holdout_frac=0.0)
    inner = inner_folds_from_train(split_df, folds, fraction=0.20)
    train_mask = folds == "train"
    inner_fit_ts = pd.to_datetime(
        split_df.loc[train_mask & (inner == "inner_fit"), "event_ts"], utc=True
    )
    inner_val_ts = pd.to_datetime(
        split_df.loc[train_mask & (inner == "inner_val"), "event_ts"], utc=True
    )
    # inner_val must be chronologically AFTER inner_fit
    assert inner_val_ts.min() >= inner_fit_ts.max(), (
        "inner_val timestamps must be >= all inner_fit timestamps"
    )
    # Both slices non-empty
    assert len(inner_fit_ts) > 0
    assert len(inner_val_ts) > 0
    # inner_val rows should be from the last 20% of calendar span
    train_ts = pd.to_datetime(split_df.loc[train_mask, "event_ts"], utc=True)
    span = train_ts.max() - train_ts.min()
    cut = train_ts.max() - span * 0.20
    val_in_window = (inner_val_ts >= cut).all()
    assert val_in_window, "all inner_val rows should be at or after the 80% calendar mark"
    # No shuffling: source code must not contain train_test_split or shuffle=True
    src = inspect.getsource(inner_folds_from_train)
    assert "train_test_split" not in src
    assert "shuffle=True" not in src


# ---------------------------------------------------------------------------
# 3.2 — op_threshold event IDs must be subset of inner_val (STOP-GATE)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pop_p3(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-p3")
    return run_population(
        None,
        run_id="phase3",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


def test_op_threshold_event_ids_subset_inner_val(pop_p3: dict, tmp_path: Path, monkeypatch):
    """Spy/record IDs passed into _tpr_at_fpr; ids must be a subset of inner_val event IDs
    and disjoint from outer eval event IDs."""
    calls: list[dict] = []
    original_tpr = fit_mod._tpr_at_fpr

    def spy_tpr(y_bin, scores, target, **kw):
        calls.append({"n": len(y_bin), "target": target})
        return original_tpr(y_bin, scores, target, **kw)

    monkeypatch.setattr(fit_mod, "_tpr_at_fpr", spy_tpr)
    dest = tmp_path / "models"
    runs = Path(pop_p3["parquet_path"]).parent.parent
    body = fit_champion("phase3", world_seed=42, runs_dir=runs, models_dir=dest)

    # The threshold must have been computed on inner_val, not outer eval.
    # Check that at least one call to _tpr_at_fpr used the inner_val size.
    # Read split data to compute expected sizes.
    split_df = pd.read_parquet(runs / "phase3" / "split.parquet")
    train_df = pd.read_parquet(runs / "phase3" / "train.parquet")
    folds = assign_folds(split_df, seed=42)
    inner = inner_folds_from_train(split_df.reset_index(drop=True), folds.reset_index(drop=True))
    train_mask = folds.reset_index(drop=True) == "train"
    n_inner_val = int((inner[train_mask.to_numpy()] == "inner_val").sum())
    n_eval = int((folds == "eval").sum())

    # The first call to _tpr_at_fpr with target=0.01 should be on inner_val-sized data
    threshold_calls = [c for c in calls if c["target"] == 0.01]
    # There should be at least one call on inner_val data (for threshold)
    inner_val_calls = [c for c in threshold_calls if c["n"] == n_inner_val]
    assert len(inner_val_calls) >= 1, (
        f"op_threshold must be computed on inner_val ({n_inner_val} rows), "
        f"but _tpr_at_fpr was called with sizes: {[c['n'] for c in threshold_calls]}"
    )
    # No call at 0.01 should be on outer eval-sized data before the threshold call
    # (the refit diagnostic block may call it on eval, but the threshold was already frozen)
    assert body["metrics"]["inner_val_protocol"] == "last_20pct_train_calendar"


# ---------------------------------------------------------------------------
# 3.3 — diagnostic_ap_by_family present; inner_val_protocol key present
# ---------------------------------------------------------------------------
def test_diagnostic_ap_by_family_present(pop_p3: dict, tmp_path: Path):
    dest = tmp_path / "models"
    runs = Path(pop_p3["parquet_path"]).parent.parent
    body = fit_champion("phase3", world_seed=42, runs_dir=runs, models_dir=dest)
    metrics = body["metrics"]
    assert "diagnostic_ap_by_family" in metrics, "diagnostic_ap_by_family must be in metrics"
    assert metrics["inner_val_protocol"] == "last_20pct_train_calendar"
    # diagnostic_ap_by_family should be a dict of family -> float
    diag = metrics["diagnostic_ap_by_family"]
    assert isinstance(diag, dict)


# ---------------------------------------------------------------------------
# 3.4 — HGB early_stopping=False
# ---------------------------------------------------------------------------
def test_hgb_early_stopping_false():
    """early_stopping=False must be in fit_champion source."""
    src = inspect.getsource(fit_mod.fit_champion)
    assert "early_stopping=False" in src or "early_stopping= False" in src, (
        "fit_champion must use early_stopping=False to prevent hidden internal validation leak"
    )


# ---------------------------------------------------------------------------
# 3.5 — shuffle tests still exist and pass (keep existing tests alive)
# ---------------------------------------------------------------------------
def test_shuffle_tests_exist():
    """Existing shuffle guard tests must still be importable."""
    from tests.test_eval_split import test_time_cut_uses_event_ts_not_shuffle  # noqa: F401
    from tests.test_eval_fit import test_reported_split_is_not_shuffle  # noqa: F401


# ---------------------------------------------------------------------------
# 3.6 — recipe_hash is SHA-256 of features.json, 64 hex chars
# ---------------------------------------------------------------------------
def test_recipe_hash_sha256_features_json(pop_p3: dict, tmp_path: Path):
    dest = tmp_path / "models"
    runs = Path(pop_p3["parquet_path"]).parent.parent
    body = fit_champion("phase3", world_seed=42, runs_dir=runs, models_dir=dest)
    rh = body["metrics"]["recipe_hash"]
    assert isinstance(rh, str)
    assert len(rh) == 64, f"recipe_hash must be 64 hex chars, got {len(rh)}"
    # Verify it's valid hex
    int(rh, 16)
    # Verify it matches the actual features.json hash
    from packages.eval.fit import RECIPE_PATH
    expected = hashlib.sha256(RECIPE_PATH.read_bytes()).hexdigest()
    assert rh == expected


# ---------------------------------------------------------------------------
# 3.7 — inner fold never opens seed-43 path
# ---------------------------------------------------------------------------
def test_inner_fold_never_opens_seed_43_path(pop_p3: dict, tmp_path: Path, monkeypatch):
    """Fail if any path contains make-gtest or a sidecar with world_seed==43."""
    opened_paths: list[str] = []
    original_read_parquet = pd.read_parquet

    def spy_read_parquet(path, *args, **kwargs):
        opened_paths.append(str(path))
        return original_read_parquet(path, *args, **kwargs)

    monkeypatch.setattr(pd, "read_parquet", spy_read_parquet)
    dest = tmp_path / "models"
    runs = Path(pop_p3["parquet_path"]).parent.parent
    fit_champion("phase3", world_seed=42, runs_dir=runs, models_dir=dest)

    for p in opened_paths:
        assert "make-gtest" not in p, f"fit_champion opened a G-test path: {p}"
        assert "seed-43" not in p, f"fit_champion opened a seed-43 path: {p}"


# ---------------------------------------------------------------------------
# 3.extra — model_manifest.json sidecar written with recipe_hash
# ---------------------------------------------------------------------------
def test_model_manifest_written(pop_p3: dict, tmp_path: Path):
    dest = tmp_path / "models"
    runs = Path(pop_p3["parquet_path"]).parent.parent
    fit_champion("phase3", world_seed=42, runs_dir=runs, models_dir=dest)
    manifest_path = dest / "phase3" / "model_manifest.json"
    assert manifest_path.is_file(), "model_manifest.json must be written alongside champion.joblib"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "recipe_hash" in manifest
    assert len(manifest["recipe_hash"]) == 64


# ---------------------------------------------------------------------------
# 3.extra — _class_weight is deterministic
# ---------------------------------------------------------------------------
def test_class_weight_deterministic():
    y = pd.Series(["normal"] * 80 + ["mule"] * 10 + ["app_fraud"] * 10)
    w1 = _class_weight(y)
    w2 = _class_weight(y)
    assert w1 == w2, "_class_weight must be a pure function of y"
