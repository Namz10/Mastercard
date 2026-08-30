"""Freeze internal operating point @ genuine FPR ≤ 0.1% from inner_val only (Phase A)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import (
    FRAUD_FAMILIES,
    _ap_by_family,
    _attach_rule_bits,
    _binary_op_metrics,
    _brake_action_hist,
    _cost_sketch,
    _encode,
    _fraud_score,
    _genuine_fp_rate,
    _n_pos_by_family,
    _not_comparable,
    _pred_family,
    _proba_map,
    folds_from_run,
    inner_folds_from_train,
    load_champion,
    run_paths,
)
from packages.eval.fpr_pareto import max_recall_at_genuine_fpr
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR

FPR_TARGET = 0.001
THRESHOLD_SPLIT = "inner_val"
THRESHOLD_RUN = "v1-train-46"
EVAL_RUN = "v1-gtest-48"
DEFAULT_CHAMPION = "v1-train-46__loopm-train"


def _score_fold(
    champ,
    train_df: pd.DataFrame,
    split_df: pd.DataFrame,
    mask: np.ndarray,
) -> tuple[np.ndarray, pd.Series, pd.DataFrame, dict[str, np.ndarray], pd.DataFrame]:
    rules = load_v0_rules()
    attached = _attach_rule_bits(train_df, rules)
    y = split_df["label_family"].astype(str).iloc[mask].reset_index(drop=True)
    raw_sub = attached.iloc[mask].reset_index(drop=True)
    x_raw = raw_sub.reindex(columns=champ.raw_columns, fill_value=0)
    split_sub = split_df.iloc[mask].reset_index(drop=True)
    x, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x)
    if getattr(champ, "pmap_calibrators", None):
        from packages.eval.fit import _apply_pmap_calibrators

        pmap = _apply_pmap_calibrators(pmap, champ.pmap_calibrators, champ.classes)
    scores = _fraud_score(pmap, len(y))
    return scores, y, split_sub, pmap, raw_sub


def _metrics_at_threshold(
    champ,
    scores: np.ndarray,
    y: pd.Series,
    split_sub: pd.DataFrame,
    x_raw: pd.DataFrame,
    pmap: dict[str, np.ndarray],
    thr: float,
    *,
    recipe: dict[str, Any],
) -> dict[str, Any]:
    from packages.eval.fit import _act_threshold

    y_str = y.astype(str).to_numpy()
    y_bin = (y_str != "normal").astype(int)
    normal_mask = y_str == "normal"
    yhat = (scores >= thr).astype(int)
    pred = _pred_family(pmap, champ.classes, len(y))
    rules = load_v0_rules()
    hist, fp_hist = _brake_action_hist(
        x_raw, y, split_sub["payee"], pred, scores, thr, rules,
        iso_model=champ.iso_model if getattr(champ, "isolation_forest_enabled", None) else None,
        pmap=pmap if getattr(champ, "isolation_forest_enabled", None) else None,
    )
    bin_op = _binary_op_metrics(y_bin, scores, yhat)
    n_pos = _n_pos_by_family(y)
    nc = int(recipe.get("n_pos_not_comparable_below", 30))
    return {
        "detect_thr": float(thr),
        "genuine_fp": _genuine_fp_rate(yhat, normal_mask),
        "precision_at_op": bin_op["precision_at_op"],
        "recall_at_op": bin_op["recall_at_op"],
        "binary_ap": bin_op["binary_ap"],
        "ap_by_family": _ap_by_family(y, pmap),
        "n_pos": n_pos,
        "not_comparable": _not_comparable(n_pos, nc),
        "confusion_matrix": bin_op["confusion_matrix"],
        "action_histogram": hist,
        "cost_sketch": _cost_sketch(
            n_total=len(y),
            n_fraud=int(y_bin.sum()),
            n_fn=int(((y_bin == 1) & (yhat == 0)).sum()),
            fp_action_hist=fp_hist,
        ),
        "family_recall_at_op": {
            fam: float(((scores >= thr) & (y_str == fam)).sum() / max(1, (y_str == fam).sum()))
            for fam in sorted(FRAUD_FAMILIES)
        },
    }


def freeze_internal_01pct_fpr(
    *,
    model_run_id: str = DEFAULT_CHAMPION,
    train_run_id: str = THRESHOLD_RUN,
    eval_run_id: str = EVAL_RUN,
    fpr_target: float = FPR_TARGET,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Select threshold on inner_val; evaluate once on G-test eval fold."""
    runs = runs_dir or RUNS_DIR
    champ = load_champion(model_run_id, models_dir=models_dir)
    recipe = champ.recipe

    # --- Threshold selection: inner_val on train world only ---
    paths_tr = run_paths(train_run_id, runs)
    train_df = pd.read_parquet(paths_tr["train"])
    split_df = pd.read_parquet(paths_tr["split"])
    sidecar = json.loads(paths_tr["sidecar"].read_text(encoding="utf-8"))
    packed = folds_from_run(
        train_df, split_df, seed=int(sidecar.get("world_seed", 46)),
        sim_days=int(sidecar["sim_days"]) if sidecar.get("sim_days") else None,
    )
    inner = inner_folds_from_train(split_df.reset_index(drop=True), packed["folds"].reset_index(drop=True))
    train_idx = (packed["folds"].reset_index(drop=True) == "train").to_numpy()
    inner_of_train = inner[train_idx].reset_index(drop=True)
    ival_mask = (inner_of_train == "inner_val").to_numpy()
    global_ival = np.zeros(len(split_df), dtype=bool)
    train_row_idx = np.where(train_idx)[0]
    global_ival[train_row_idx[ival_mask]] = True

    scores_iv, y_iv, split_iv, pmap_iv, raw_iv = _score_fold(champ, train_df, split_df, global_ival)
    y_bin_iv = (y_iv.astype(str) != "normal").astype(int).to_numpy()
    normal_iv = (y_iv.astype(str) == "normal").to_numpy()
    sel = max_recall_at_genuine_fpr(scores_iv, y_bin_iv, normal_iv, fpr_target=fpr_target)

    thr = float(sel["threshold"])
    threshold_selection = {
        "split": THRESHOLD_SPLIT,
        "run_id": train_run_id,
        "fpr_target": fpr_target,
        "n_inner_val": int(ival_mask.sum()),
        "n_normal_inner_val": int(normal_iv.sum()),
        "n_fraud_inner_val": int(y_bin_iv.sum()),
        "selected_threshold": thr,
        "inner_val_recall_at_cap": float(sel["recall"]),
        "inner_val_genuine_fp_at_cap": float(sel["genuine_fp"]),
        "legacy_detect_thr": float(champ.detect_thr or champ.op_threshold or 0),
        "operating_point_fpr_recipe": float(recipe.get("operating_point_fpr", 0.01)),
        "note": "Threshold from inner_val only; never selected on G-test.",
    }

    # --- Single G-test eval (eval fold only, not all_rows) ---
    paths_ev = run_paths(eval_run_id, runs)
    train_ev = pd.read_parquet(paths_ev["train"])
    split_ev = pd.read_parquet(paths_ev["split"])
    side_ev = json.loads(paths_ev["sidecar"].read_text(encoding="utf-8"))
    packed_ev = folds_from_run(
        train_ev, split_ev, seed=int(side_ev.get("world_seed", 48)),
        sim_days=int(side_ev["sim_days"]) if side_ev.get("sim_days") else None,
    )
    eval_mask = (packed_ev["folds"].reset_index(drop=True) == "eval").to_numpy()
    global_eval = np.zeros(len(split_ev), dtype=bool)
    global_eval[np.where(eval_mask)[0]] = True

    scores_te, y_te, split_te, pmap_te, raw_te = _score_fold(champ, train_ev, split_ev, global_eval)

    frozen_op = _metrics_at_threshold(champ, scores_te, y_te, split_te, raw_te, pmap_te, thr, recipe=recipe)
    legacy_thr = float(champ.detect_thr or champ.op_threshold or 0)
    legacy_op = _metrics_at_threshold(champ, scores_te, y_te, split_te, raw_te, pmap_te, legacy_thr, recipe=recipe)

    body: dict[str, Any] = {
        "schema": "internal_fpr_freeze_v1",
        "model_run_id": model_run_id,
        "champion_version": "v1-loopm",
        "fpr_target": fpr_target,
        "threshold_selection": threshold_selection,
        "eval_run_id": eval_run_id,
        "eval_protocol": "time_cut_eval_fold_only",
        "frozen_operating_point": frozen_op,
        "legacy_default_op": {
            "detect_thr": legacy_thr,
            **{k: legacy_op[k] for k in (
                "genuine_fp", "recall_at_op", "precision_at_op", "binary_ap",
                "ap_by_family", "cost_sketch", "action_histogram",
            )},
        },
        "acceptance": {
            "genuine_fpr_le_target": frozen_op["genuine_fp"] <= fpr_target + 1e-9,
            "no_test_threshold_selection": True,
            "no_retrain": True,
            "reference_posthoc_pareto_recall_01pct_g48": 0.9867,
        },
        "disclaimer": "Internal sim performance only. Not SAML-D or external transfer.",
    }
    dest = dest or Path("data/validation/v1/internal_01pct_fpr_freeze.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return body
