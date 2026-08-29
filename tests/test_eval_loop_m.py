"""Plan 12 Phase E — Loop M once: extra on train only, G-test new seed, no solved."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pandas as pd
import pytest

from packages.eval import loop_m as loop_m_mod
from packages.eval.loop_m import run_loop_m
from packages.sim.export import TRAIN_DENYLIST
from packages.sim.runner import run_population


@pytest.fixture(scope="module")
def pop(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-loop-m")
    return run_population(
        None,
        run_id="loop-m-train",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


def test_loop_m_g_test_new_seed_reports_ap_and_fpr(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    models = tmp_path / "models"
    body = run_loop_m(
        "loop-m-train",
        "app_fraud",
        train_seed=42,
        gtest_seed=48,
        runs_dir=runs,
        models_dir=models,
    )
    assert body["train_seed"] != body["gtest_seed"]
    assert body["gtest_seed"] == 48
    assert body["catalog_solved"] is False
    assert body["catalog_status"] == "open"
    assert body["n_extra"] > 0
    assert body["n_extra"] <= body["extra_row_cap"]
    cmp_ = body["comparison"]
    assert cmp_["family"] == "app_fraud"
    assert "ap_before" in cmp_ and "ap_after" in cmp_
    assert "ap_verdict" in cmp_
    assert cmp_["ap_verdict"] in {"improved", "equal", "regressed", "not_comparable"}
    assert "genuine_fp_before" in cmp_ and "genuine_fp_after" in cmp_
    assert isinstance(cmp_["other_family_ok"], bool)
    assert "other_family_ap" in cmp_

    eps = float(body["ap_equal_eps"])
    a0, a1 = cmp_["ap_before"], cmp_["ap_after"]
    if a0 is not None and a1 is not None:
        if a1 >= a0 - eps:
            expected = "improved" if a1 > a0 else "equal"
        else:
            expected = "regressed"
        assert cmp_["ap_verdict"] == expected

    fpr0, fpr1 = cmp_["genuine_fp_before"], cmp_["genuine_fp_after"]
    fpr_eps = float(body["genuine_fpr_eps"])
    if fpr0 is not None and fpr1 is not None:
        assert cmp_["genuine_fp_ok"] == (fpr1 <= fpr0 + fpr_eps)

    gtest_split = pd.read_parquet(runs / body["gtest_run_id"] / "split.parquet")
    extra_ids = set(
        pd.read_parquet(runs / f"{body['run_id']}__loopm-train" / "split.parquet")["event_id"]
        .astype(str)
    ) - set(pd.read_parquet(runs / "loop-m-train" / "split.parquet")["event_id"].astype(str))
    assert extra_ids
    assert extra_ids.isdisjoint(set(gtest_split["event_id"].astype(str)))
    assert all(str(i).startswith("evt-lm-") for i in extra_ids)

    blob = json.dumps(body)
    for banned in (
        "simulatable_signals",
        "is_authorized_push",
        "economic_class",
        "world_seed",
        "technique_id",
        "knobs_used",
    ):
        assert banned not in blob
    src = inspect.getsource(loop_m_mod)
    assert "injectors" not in src
    assert "train_test_split" not in src


def test_loop_m_rejects_same_seed(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    with pytest.raises(ValueError, match="differ"):
        run_loop_m(
            "loop-m-train",
            "app_fraud",
            train_seed=42,
            gtest_seed=42,
            runs_dir=runs,
            models_dir=tmp_path / "models",
        )
