"""H6 failure forensics — why generic hard negatives collapsed identity_burst."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import run_paths
from packages.sim.ablation import APP_FLAG_COLS

FEATURE_COMPARE = [
    "urgency_pressure",
    "call_active_flag",
    "copy_paste_payee_flag",
    "pause_ms",
    "fan_in_1h",
    "fan_in_24h",
    "is_new_payee",
    "is_new_device",
    "burst_velocity",
    "account_age_days",
]


def diagnose_h6_failure(
    h6_artifact: Path | None = None,
    gdev_run_id: str = "v1-gdev-47",
    runs_dir: Path | None = None,
) -> dict[str, Any]:
    from packages.sim.export import RUNS_DIR

    runs = runs_dir or RUNS_DIR
    art_path = h6_artifact or Path("data/validation/v1/h6_hard_negatives.json")
    art = json.loads(art_path.read_text(encoding="utf-8"))
    mined_ids = {m["event_id"] for m in art.get("mine", {}).get("mined", [])}
    paths = run_paths(gdev_run_id, runs)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    if len(train_df) != len(split_df):
        raise ValueError("train/split length mismatch")
    labels = split_df["label_family"].astype(str)
    idx = split_df["event_id"].astype(str).isin(mined_ids)
    mined_idx = idx.to_numpy()
    normal_mask = (labels == "normal").to_numpy()
    identity_mask = (labels == "identity_burst").to_numpy()

    def _means(mask: np.ndarray) -> dict[str, float]:
        if not mask.any():
            return {}
        sub = train_df.loc[mask]
        out: dict[str, float] = {}
        for col in FEATURE_COMPARE:
            if col in sub.columns:
                out[col] = float(pd.to_numeric(sub[col], errors="coerce").fillna(0).mean())
        return out

    mined_means = _means(mined_idx)
    normal_means = _means(normal_mask)
    identity_means = _means(identity_mask)

    # APP-stamp overlap: fraction of mined with any APP flag active
    app_cols = [c for c in APP_FLAG_COLS if c in train_df.columns]
    mined_app_frac = 0.0
    identity_app_frac = 0.0
    if app_cols and mined_idx.any():
        msub = train_df.loc[mined_idx, app_cols].astype(float)
        mined_app_frac = float((msub.max(axis=1) > 0).mean())
    if app_cols and identity_mask.any():
        isub = train_df.loc[identity_mask, app_cols].astype(float)
        identity_app_frac = float((isub.max(axis=1) > 0).mean())

    # Score stats from mine manifest
    scores = [m["score"] for m in art.get("mine", {}).get("mined", [])]
    score_stats = {
        "min": float(min(scores)) if scores else None,
        "median": float(np.median(scores)) if scores else None,
        "max": float(max(scores)) if scores else None,
        "n_mined": len(scores),
        "min_score_gate": art.get("mine", {}).get("min_score"),
    }

    # H6 outcome on gtest-49
    cmp49 = art.get("comparison", {}).get("v1-gtest-49", {})
    identity_ap_before = (cmp49.get("metrics_before") or {}).get("ap_by_family", {}).get("identity_burst")
    identity_ap_after = (cmp49.get("metrics_after") or {}).get("ap_by_family", {}).get("identity_burst")

    hypotheses = [
        "Mined normals are overwhelmingly new-payee shaped (is_new_payee ~91% vs 5% baseline) with scores 0.91–1.0.",
        "Identity_burst fraud is fan_in/burst-shaped (fan_in_1h ~58) not new-payee-shaped — generic HN targets the wrong failure mode.",
        "Retrain shifts the decision boundary to suppress new-payee highs; identity ranking collateral damage + higher act burden (cost_sketch).",
    ]

    body = {
        "status": "ok",
        "gdev_run_id": gdev_run_id,
        "feature_means": {
            "mined_hard_negatives": mined_means,
            "all_normals": normal_means,
            "identity_burst_fraud": identity_means,
        },
        "app_stamp_active_frac": {
            "mined": mined_app_frac,
            "identity_burst": identity_app_frac,
            "all_normals": float(
                (train_df.loc[normal_mask, app_cols].astype(float).max(axis=1) > 0).mean()
            )
            if app_cols and normal_mask.any()
            else None,
        },
        "mine_score_stats": score_stats,
        "gtest49_identity_ap": {"before": identity_ap_before, "after": identity_ap_after},
        "mechanism_hypotheses": hypotheses,
        "recommended_next": [
            "Exclude is_new_payee=1 normals from mining pool (or cap top_k <= 50)",
            "Mine normals that FP on portable fan_in/burst features only — not APP/new-payee proxies",
            "Family-aware: skip HN round when identity_burst is not the weakest family on gdev",
        ],
    }
    out = Path("data/validation/v1/h6_diagnosis.json")
    out.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return body
