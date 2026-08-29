"""Genuine-FPR-constrained operating envelope (max recall @ FPR cap)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import (
    _attach_rule_bits,
    _encode,
    _fraud_score,
    _proba_map,
    load_champion,
    run_paths,
)
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR
from packages.sim.ledger import LABEL_FAMILIES

FRAUD_FAMILIES = LABEL_FAMILIES - {"normal"}
DEFAULT_FPR_TARGETS = (0.01, 0.005, 0.001)


def max_recall_at_genuine_fpr(
    scores: np.ndarray,
    y_bin: np.ndarray,
    normal_mask: np.ndarray,
    *,
    fpr_target: float,
) -> dict[str, float]:
    """Maximize recall (fraud detected) subject to FP/n_normal <= fpr_target."""
    scores = np.asarray(scores, dtype=float)
    y_bin = np.asarray(y_bin, dtype=int)
    normal_mask = np.asarray(normal_mask, dtype=bool)
    n_norm = int(normal_mask.sum())
    if n_norm == 0 or y_bin.max() == y_bin.min():
        return {
            "fpr_target": fpr_target,
            "recall": float("nan"),
            "genuine_fp": float("nan"),
            "threshold": 1.0,
        }
    # Sweep thresholds in score order (O(n log n)); normals-only denominator for FPR.
    order = np.argsort(-scores, kind="mergesort")
    fp_norm = 0
    tp = 0
    n_pos = int((y_bin == 1).sum())
    best: dict[str, float] | None = None
    i = 0
    n = len(scores)
    while i < n:
        thr = float(scores[order[i]])
        while i < n and scores[order[i]] >= thr - 1e-15:
            idx = order[i]
            if normal_mask[idx]:
                fp_norm += 1
            elif y_bin[idx] == 1:
                tp += 1
            i += 1
        gfp = fp_norm / n_norm
        if gfp <= fpr_target + 1e-12:
            rec = float(tp / n_pos) if n_pos else 0.0
            if best is None or rec > best["recall"]:
                best = {
                    "fpr_target": fpr_target,
                    "recall": rec,
                    "genuine_fp": gfp,
                    "threshold": thr,
                }
    if best is None:
        return {
            "fpr_target": fpr_target,
            "recall": 0.0,
            "genuine_fp": 1.0,
            "threshold": float(np.max(scores)) if len(scores) else 1.0,
        }
    return best


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


def pareto_envelope(
    run_id: str,
    model_run_id: str,
    *,
    fpr_targets: tuple[float, ...] = DEFAULT_FPR_TARGETS,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """Pareto envelope: max recall @ each genuine-FPR cap + family recall at chosen thr."""
    runs = runs_dir or RUNS_DIR
    champ = load_champion(model_run_id, models_dir=models_dir)
    paths = run_paths(run_id, runs)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    scores, y = _score_rows(champ, train_df, split_df)
    y_str = y.to_numpy(dtype=object)
    y_bin = (y_str != "normal").astype(int)
    normal_mask = y_str == "normal"

    envelope: dict[str, Any] = {}
    family_at_op: dict[str, dict[str, Any]] = {}
    for t in fpr_targets:
        pt = max_recall_at_genuine_fpr(scores, y_bin, normal_mask, fpr_target=float(t))
        key = f"{t:g}"
        envelope[key] = pt
        thr = pt["threshold"]
        hit = scores >= thr
        fam_recall: dict[str, float | None] = {}
        for fam in sorted(FRAUD_FAMILIES):
            m = y_str == fam
            n = int(m.sum())
            fam_recall[fam] = None if n == 0 else float((hit & m).sum() / n)
        family_at_op[key] = fam_recall

    n_fraud = int(y_bin.sum())
    default_thr = float(np.median(scores))
    default_hit = scores >= default_thr
    default_gfp = float((default_hit & normal_mask).sum() / normal_mask.sum()) if normal_mask.any() else float("nan")
    default_recall = float((default_hit & (y_bin == 1)).sum() / n_fraud) if n_fraud else float("nan")
    return {
        "run_id": run_id,
        "model_run_id": model_run_id,
        "fpr_targets": list(fpr_targets),
        "envelope": envelope,
        "family_recall_at_envelope": family_at_op,
        "score_summary": {
            "n_rows": int(len(scores)),
            "n_normal": int(normal_mask.sum()),
            "n_fraud": n_fraud,
            "median_score": default_thr,
            "genuine_fp_at_median_thr": default_gfp,
            "recall_at_median_thr": default_recall,
        },
    }


def write_pareto_report(
    *,
    run_ids: tuple[str, ...] = ("v1-gtest-48", "v1-gtest-49"),
    models: tuple[tuple[str, str], ...] = (
        ("v1-train-46", "Stage1"),
        ("v1-train-46__loopm-train", "LoopM"),
    ),
    dest: Path | None = None,
) -> Path:
    dest = dest or Path("data/validation/v1/pareto_genuine_fpr.json")
    body: dict[str, Any] = {"worlds": {}, "models": [m[0] for m in models]}
    for rid in run_ids:
        body["worlds"][rid] = {}
        for mid, label in models:
            body["worlds"][rid][label] = pareto_envelope(rid, mid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return dest
