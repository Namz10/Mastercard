"""Plan 12 Phase C — champion fit, labels, time+entity split, ablation, no denylist."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from packages.eval import fit as fit_mod
from packages.eval.fit import fit_champion
from packages.sim.export import TRAIN_DENYLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS
from packages.sim.runner import run_population


@pytest.fixture(scope="module")
def pop(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs")
    return run_population(
        None,
        run_id="fit-c",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


def test_fit_y_is_family_enum_not_technique(pop: dict, tmp_path: Path):
    dest = tmp_path / "models"
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=dest)
    metrics = body["metrics"]
    cols = metrics["feature_columns"]
    for fam in LABEL_FAMILIES:
        assert fam not in TECHNIQUE_IDS
    assert body["split"] == "time_cut_2_3_plus_entity_holdout"
    assert "ap_by_family" in metrics
    for banned in ("is_authorized_push", "economic_class", "technique_id"):
        assert banned not in cols
    for banned in TRAIN_DENYLIST:
        assert banned not in cols
    assert metrics["n_train"] > 0 and metrics["n_eval"] > 0


def test_reported_split_is_not_shuffle():
    src = inspect.getsource(fit_mod)
    assert "train_test_split" not in src
    assert "shuffle=True" not in src


def test_app_ablation_reported(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "models")
    ab = body["metrics"]["app_ablation"]
    flags = {str(x) for x in ab["app_flags"]}
    for col in ("call_active_flag", "copy_paste_payee_flag", "pause_ms", "urgency_pressure"):
        assert col in flags
    assert "average_precision" in ab["with_app_flags"]
    assert "average_precision" in ab["without_app_flags"]
    assert "app_metric_died_without_synthetic_flags" in ab


def test_fit_reproducible_seed_42(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    a = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "m1")
    b = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "m2")
    assert a["metrics"]["n_train"] == b["metrics"]["n_train"]
    assert a["metrics"]["feature_columns"] == b["metrics"]["feature_columns"]
    assert Path(tmp_path / "m1" / "fit-c" / "champion.joblib").is_file()
    dumped = json.dumps(a)
    assert "simulatable_signals" not in dumped
