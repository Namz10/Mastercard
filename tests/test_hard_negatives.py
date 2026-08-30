"""H6 hard-negative mining — RED tests before full v1 eval."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from packages.eval import fit as fit_mod
from packages.eval.hard_negatives import (
    HN_ID_PREFIX,
    augment_train_with_hard_negatives,
    assert_hn_ids_inner_fit,
    mine_hard_negatives,
)
from packages.eval.fit import fit_champion, run_paths
from packages.eval.split import folds_from_run, inner_folds_from_train
from packages.policy.rules import load_v0_rules
from packages.sim.runner import run_population

_real_load_recipe = fit_mod.load_recipe


def _test_load_recipe(path=None):
    recipe = dict(_real_load_recipe(path))
    recipe["fold_floor_min"] = 0
    return recipe


fit_mod.load_recipe = _test_load_recipe


@pytest.fixture
def hn_pop(tmp_path: Path) -> dict:
    train_id = "hn-train-42"
    gdev_id = "hn-gdev-44"
    runs = tmp_path / "runs"
    for rid, seed in ((train_id, 42), (gdev_id, 44)):
        run_population(
            None,
            run_id=rid,
            n_customers=80,
            n_merchants=12,
            sim_days=30,
            world_seed=seed,
            pin=True,
            runs_dir=runs,
        )
    fit_champion(train_id, world_seed=42, runs_dir=runs, models_dir=tmp_path / "models")
    return {"runs": runs, "train_id": train_id, "gdev_id": gdev_id, "models_dir": tmp_path / "models"}


def test_mine_hard_negatives_only_normals(hn_pop: dict):
    model_id = hn_pop["train_id"]
    body = mine_hard_negatives(
        hn_pop["gdev_id"],
        model_id,
        top_k=20,
        min_score=0.0,
        runs_dir=hn_pop["runs"],
        models_dir=hn_pop["models_dir"],
    )
    if body.get("status") == "skipped":
        pytest.skip(body.get("reason", "no candidates"))
    assert body["status"] == "ok"
    assert all(m["label_family"] == "normal" for m in body["mined"])
    gdev_sp = pd.read_parquet(run_paths(hn_pop["gdev_id"], hn_pop["runs"])["split"])
    for m in body["mined"]:
        row = gdev_sp.loc[gdev_sp["event_id"].astype(str) == m["event_id"]]
        assert len(row) == 1
        assert str(row.iloc[0]["label_family"]) == "normal"


def test_hn_extra_ids_disjoint_from_gtest_runs(hn_pop: dict, tmp_path: Path):
    mine = mine_hard_negatives(
        hn_pop["gdev_id"],
        hn_pop["train_id"],
        top_k=5,
        min_score=0.0,
        runs_dir=hn_pop["runs"],
        models_dir=hn_pop["models_dir"],
    )
    if mine.get("status") != "ok":
        pytest.skip(mine.get("reason", "no mined"))
    gtest_id = "hn-fake-gtest"
    run_population(
        None,
        run_id=gtest_id,
        n_customers=80,
        n_merchants=12,
        sim_days=30,
        world_seed=48,
        pin=True,
        runs_dir=hn_pop["runs"],
    )
    aug_id, _, hn_ids = augment_train_with_hard_negatives(
        hn_pop["train_id"],
        hn_pop["gdev_id"],
        [m["event_id"] for m in mine["mined"]],
        augmented_run_id="hn-aug",
        runs_dir=hn_pop["runs"],
        forbidden_gtest_run_ids=(gtest_id,),
    )
    assert aug_id == "hn-aug"
    assert all(eid.startswith(HN_ID_PREFIX) for eid in hn_ids)


def test_hn_force_train_stays_inner_fit(hn_pop: dict):
    mine = mine_hard_negatives(
        hn_pop["gdev_id"],
        hn_pop["train_id"],
        top_k=8,
        min_score=0.0,
        runs_dir=hn_pop["runs"],
        models_dir=hn_pop["models_dir"],
    )
    if mine.get("status") != "ok":
        pytest.skip(mine.get("reason", "no mined"))
    aug_id, _, hn_ids = augment_train_with_hard_negatives(
        hn_pop["train_id"],
        hn_pop["gdev_id"],
        [m["event_id"] for m in mine["mined"]],
        augmented_run_id="hn-aug2",
        world_seed=42,
        runs_dir=hn_pop["runs"],
        forbidden_gtest_run_ids=(),
    )
    assert_hn_ids_inner_fit(aug_id, hn_ids, world_seed=42, runs_dir=hn_pop["runs"])
    paths = run_paths(aug_id, hn_pop["runs"])
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    from packages.eval.fit import _attach_rule_bits

    train_df = _attach_rule_bits(train_df, load_v0_rules())
    packed = folds_from_run(train_df, split_df, seed=42)
    inner = inner_folds_from_train(
        split_df.reset_index(drop=True),
        packed["folds"].reset_index(drop=True),
        exclude_event_ids=hn_ids,
    )
    for eid in hn_ids:
        idx = split_df.index[split_df["event_id"].astype(str) == eid][0]
        assert inner.iloc[idx] == "inner_fit"
