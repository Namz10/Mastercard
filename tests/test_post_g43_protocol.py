"""Post-G43 protocol tests — E0/E4 measurement and split semantics."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

pytest_plugins = ["tests.test_eval_fit"]

from packages.eval import fit as fit_mod
from packages.eval.split import assign_folds, calendar_cut


def test_tune_champion_never_reads_outer_eval_in_objective():
    src = inspect.getsource(fit_mod.tune_champion)
    assert "x_ev_enc" not in src
    assert "outer_genuine" not in src
    assert "outer_fp =" not in src


def test_gtest_ablation_recomputed_on_frozen_champion(fitted: dict):
    body = fit_mod.score_run(
        "fit-c",
        model_run_id="fit-c",
        runs_dir=fitted["runs"],
        models_dir=fitted["dest"],
        all_rows=True,
    )
    ab = body["metrics"]["app_ablation"]
    assert ab["app_ablation_source"] == "frozen_champion"


def test_genuine_fp_uses_n_normal_denom(fitted: dict):
    body = fitted["body"]
    cm = body["metrics"]["confusion_matrix"]
    fp = cm["fp"]
    n_normal = body["metrics"]["n_pos"]["normal"]
    expected = fp / n_normal
    assert body["metrics"]["genuine_fp"] == pytest.approx(expected, rel=1e-6)
    assert "genuine_fp_over_eval" in body["metrics"]


def test_assign_folds_uses_sim_days_not_observed_max():
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(120):
        rows.append(
            {
                "event_id": f"e{i}",
                "event_ts": (t0 + timedelta(days=i)).isoformat(),
                "payer": "VID-SIM-C-000001",
                "payee": "VID-SIM-M-000001",
                "amount_minor": 100,
                "label_family": "normal",
            }
        )
    # Stretch observed max to day 119 but sim_days=90 → cut should use day 60 not day 80
    split_df = pd.DataFrame(rows)
    folds_obs = assign_folds(split_df, seed=1, sim_days=None)
    folds_sim = assign_folds(split_df, seed=1, sim_days=90)
    cut_obs = calendar_cut(pd.Series(split_df["event_ts"]), sim_days=None)
    cut_sim = calendar_cut(pd.Series(split_df["event_ts"]), sim_days=90, t0=pd.Timestamp(t0))
    assert cut_sim < cut_obs
    assert (folds_sim == "eval").sum() != (folds_obs == "eval").sum()


def test_load_champion_accepts_v0_museum_hash():
    champ = fit_mod.load_champion("make-scale-fullmix")
    assert champ.op_threshold > 0


def test_champion_manifest_has_detect_and_act_thr(fitted: dict):
    metrics = fitted["body"]["metrics"]
    assert "detect_thr" in metrics or "op_threshold" in metrics
    assert "act_thr" in metrics or "op_threshold" in metrics
