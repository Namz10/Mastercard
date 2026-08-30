"""Operational Pareto scoring on frozen champion — no retrain (H5d)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import (
    _attach_rule_bits,
    _cost_sketch,
    _encode,
    _fraud_score,
    _genuine_fp_rate,
    _proba_map,
    load_champion,
    run_paths,
)
from packages.eval.fpr_pareto import FRAUD_FAMILIES, max_recall_at_genuine_fpr
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR

DEFAULT_FPR_TARGETS = (0.01, 0.005, 0.001)


def _score_rows(champ, train_df: pd.DataFrame, split_df: pd.DataFrame) -> tuple[np.ndarray, pd.Series]:
    rules = load_v0_rules()
    train_df = _attach_rule_bits(train_df, rules)
    y = split_df["label_family"].astype(str)
    x_raw = train_df.reindex(columns=champ.raw_columns, fill_value=0)
    x, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x)
    if getattr(champ, "pmap_calibrators", None):
        from packages.eval.fit import _apply_pmap_calibrators

        pmap = _apply_pmap_calibrators(pmap, champ.pmap_calibrators, champ.classes)
    scores = _fraud_score(pmap, len(y))
    return scores, y


def score_at_pareto_ops(
    run_id: str,
    model_run_id: str,
    *,
    fpr_targets: tuple[float, ...] = DEFAULT_FPR_TARGETS,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """Metrics at each Pareto operating point on frozen champion (post-hoc threshold)."""
    runs = runs_dir or RUNS_DIR
    champ = load_champion(model_run_id, models_dir=models_dir)
    paths = run_paths(run_id, runs)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    scores, y = _score_rows(champ, train_df, split_df)
    y_str = y.to_numpy(dtype=object)
    y_bin = (y_str != "normal").astype(int)
    normal_mask = y_str == "normal"
    n_norm = int(normal_mask.sum())
    n_fraud = int(y_bin.sum())

    default_thr = float(champ.op_threshold or champ.detect_thr or 0.0)
    default_hit = scores >= default_thr
    default_gfp = _genuine_fp_rate(default_hit.astype(int), normal_mask)
    default_recall = float((default_hit & (y_bin == 1)).sum() / n_fraud) if n_fraud else float("nan")
    default_fn = int(((y_bin == 1) & ~default_hit).sum())
    default_fp_norm = int((default_hit & normal_mask).sum())
    default_cost = _cost_sketch(
        n_total=len(y),
        n_fraud=n_fraud,
        n_fn=default_fn,
        fp_action_hist={"notify": default_fp_norm},
    )

    ops: dict[str, Any] = {}
    for t in fpr_targets:
        pt = max_recall_at_genuine_fpr(scores, y_bin, normal_mask, fpr_target=float(t))
        thr = float(pt["threshold"])
        hit = scores >= thr
        yhat = hit.astype(int)
        gfp = _genuine_fp_rate(yhat, normal_mask)
        rec = float(pt["recall"])
        fn = int(((y_bin == 1) & ~hit).sum())
        fp_norm = int((hit & normal_mask).sum())
        fam_recall: dict[str, float | None] = {}
        for fam in sorted(FRAUD_FAMILIES):
            m = y_str == fam
            n = int(m.sum())
            fam_recall[fam] = None if n == 0 else float((hit & m).sum() / n)
        cost = _cost_sketch(
            n_total=len(y),
            n_fraud=n_fraud,
            n_fn=fn,
            fp_action_hist={"notify": fp_norm},  # simplified FP burden proxy
        )
        ops[f"{t:g}"] = {
            "threshold": thr,
            "genuine_fp": gfp,
            "recall": rec,
            "family_recall": fam_recall,
            "cost_sketch_proxy": cost.get("expected_cost"),
            "n_fp_normal": fp_norm,
            "n_fn_fraud": fn,
        }

    return {
        "run_id": run_id,
        "model_run_id": model_run_id,
        "n_rows": len(scores),
        "n_normal": n_norm,
        "n_fraud": n_fraud,
        "default_op": {
            "detect_thr": default_thr,
            "genuine_fp": default_gfp,
            "recall": default_recall,
            "cost_sketch_proxy": default_cost.get("expected_cost"),
            "n_fp_normal": default_fp_norm,
            "n_fn_fraud": default_fn,
        },
        "pareto_ops": ops,
    }


def write_operational_report(
    *,
    model_run_id: str = "v1-train-46__loopm-train",
    run_ids: tuple[str, ...] = ("v1-gdev-47", "v1-gtest-48", "v1-gtest-49"),
    dest: Path | None = None,
) -> Path:
    dest = dest or Path("data/validation/v1/pareto_operational_v1.json")
    body: dict[str, Any] = {"model_run_id": model_run_id, "worlds": {}}
    for rid in run_ids:
        body["worlds"][rid] = score_at_pareto_ops(rid, model_run_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return dest
