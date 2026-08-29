"""H9 frozen-champion ablation audit — minimal coverage."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from packages.eval import fit as fit_mod
from packages.eval.ablation_audit import (
    ABLATION_GROUPS,
    _stamp_cols,
    audit_frozen_champion,
)
from packages.eval.fit import fit_champion
from packages.sim.ablation import APP_FLAG_COLS
from packages.sim.runner import run_population

_real_load_recipe = fit_mod.load_recipe


def _test_load_recipe(path=None):
    recipe = dict(_real_load_recipe(path))
    recipe["fold_floor_min"] = 0
    return recipe


fit_mod.load_recipe = _test_load_recipe


@pytest.fixture(scope="module")
def pop(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs")
    return run_population(
        None,
        run_id="h9-ab",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


def test_ablation_groups_keys():
    assert set(ABLATION_GROUPS) == {"stamps", "app_flags", "velocity", "merchant", "temporal", "graph"}
    assert list(ABLATION_GROUPS["app_flags"]) == list(APP_FLAG_COLS)


def test_stamp_cols_includes_rule_prefix(pop: dict):
    runs = Path(pop["parquet_path"]).parent.parent
    import pandas as pd

    train = pd.read_parquet(runs / "h9-ab" / "train.parquet")
    cols = _stamp_cols(train, {})
    assert "is_new_payee" in cols
    assert all(not c.startswith("call_") for c in cols)


def test_audit_frozen_champion_smoke(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    models = tmp_path / "models"
    fit_champion("h9-ab", world_seed=42, runs_dir=runs, models_dir=models, dest_run_id="h9-champ")
    out = tmp_path / "h9.json"
    body = audit_frozen_champion(
        model_run_id="h9-champ",
        run_ids=("h9-ab",),
        runs_dir=runs,
        models_dir=models,
        out_path=out,
    )
    assert out.is_file()
    world = body["worlds"]["h9-ab"]
    assert np.isfinite(world["baseline_binary_ap"])
    assert "without_stamps" in world
    assert world["without_stamps"]["source"] == "frozen_champion"
    for g in ABLATION_GROUPS:
        assert g in world
        assert "binary_ap" in world[g]
    ranked = world["largest_drop_vs_baseline"]
    assert ranked[0]["delta_vs_baseline"] <= ranked[-1]["delta_vs_baseline"]
