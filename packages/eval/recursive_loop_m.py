"""H7 round-1 weakness diagnostic on G-dev only — no gtest promote loop."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import (
    _apply_pmap_calibrators,
    _attach_rule_bits,
    _encode,
    _fraud_score,
    _proba_map,
    load_champion,
    load_recipe,
    run_paths,
    score_run,
)
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR
from packages.sim.ledger import LABEL_FAMILIES

MAX_ROUNDS = 3
HN_EXCLUDE_NEW_PAYEE = True
BORDERLINE_FRAC = 0.2  # score within ±20% of detect_thr

FRAUD_FAMILIES = sorted(LABEL_FAMILIES - {"normal"})


def _detect_thr(champ: Any, metrics: dict[str, Any]) -> float:
    val = getattr(champ, "detect_thr", None)
    if val is not None:
        return float(val)
    val = metrics.get("detect_thr")
    if val is not None:
        return float(val)
    return float(champ.op_threshold)


def _pick_weakest_family(
    ap_by: dict[str, Any],
    n_pos: dict[str, Any],
    *,
    n_pos_floor: int,
) -> tuple[str, str]:
    comparable = [f for f in FRAUD_FAMILIES if int(n_pos.get(f) or 0) >= n_pos_floor]
    if comparable:
        reason = f"lowest gdev AP among families with n_pos>={n_pos_floor}"
    else:
        comparable = [f for f in FRAUD_FAMILIES if int(n_pos.get(f) or 0) > 0]
        reason = f"no family with n_pos>={n_pos_floor}; fallback lowest AP among n_pos>0 families"
    if not comparable:
        comparable = list(FRAUD_FAMILIES)
        reason = "fallback lowest AP among all fraud families"
    weakest = min(comparable, key=lambda f: float(ap_by.get(f) or 0.0))
    return weakest, reason


def _intervention_for(weakest: str) -> list[str]:
    if weakest == "identity_burst":
        return [
            "Loop M: append identity_burst positives from extra seed (train only)",
            "Hard negatives: fan_in/burst-shaped normals only; exclude is_new_payee=1 (H6-D)",
            "Skip generic top-k HN mining",
        ]
    if weakest == "ato":
        return [
            "Loop M: append ato positives from extra seed (train only)",
            "Hard negatives: device/session-shaped normals; exclude is_new_payee=1 (H6-D)",
        ]
    return [
        f"Loop M: append {weakest} positives from extra seed (train only)",
        "Family-filtered hard negatives; exclude is_new_payee=1 (H6-D)",
        "Promote/reject on gdev-47 only; gtest-49 once after max rounds",
    ]


def diagnose_weakness(
    run_id: str = "v1-gdev-47",
    model_run_id: str = "v1-train-46__loopm-train",
    *,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    """Weakest family + mistake buckets on G-dev for targeted Loop M round 1.

    Read-only diagnostic — no retrain, no blind top-k HN mining, no gtest scoring.
    H6-D: hard-negative pool excludes ``is_new_payee=1`` normals.
    """
    runs = runs_dir or RUNS_DIR
    recipe = load_recipe()
    n_pos_floor = int(recipe.get("n_pos_not_comparable_below", 30))

    scored = score_run(
        run_id, model_run_id=model_run_id, runs_dir=runs, models_dir=models_dir, all_rows=True
    )
    metrics = scored["metrics"]
    ap_by = metrics.get("ap_by_family") or {}
    n_pos = metrics.get("n_pos") or {}

    weakest, pick_reason = _pick_weakest_family(ap_by, n_pos, n_pos_floor=n_pos_floor)

    paths = run_paths(run_id, runs)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    if len(train_df) != len(split_df):
        raise ValueError(f"train/split length mismatch for {run_id}")

    champ = load_champion(model_run_id, models_dir=models_dir)
    thr = _detect_thr(champ, metrics)
    lo, hi = thr * (1.0 - BORDERLINE_FRAC), thr * (1.0 + BORDERLINE_FRAC)

    train_df = _attach_rule_bits(train_df, rules=load_v0_rules())
    labels = split_df["label_family"].astype(str)
    x_raw = train_df.drop(columns=["label_family"], errors="ignore").reindex(
        columns=champ.raw_columns, fill_value=0
    )
    x, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x)
    if getattr(champ, "pmap_calibrators", None):
        pmap = _apply_pmap_calibrators(pmap, champ.pmap_calibrators, champ.classes)
    scores = _fraud_score(pmap, len(labels))
    pred = scores >= thr

    normal_mask = labels == "normal"
    fp_all = normal_mask & pred
    new_payee = pd.Series(False, index=labels.index)
    if "is_new_payee" in train_df.columns:
        new_payee = pd.to_numeric(train_df["is_new_payee"], errors="coerce").fillna(0) > 0
    fp_new_payee_only = fp_all & new_payee
    fp_excl_new_payee = fp_all & ~new_payee if HN_EXCLUDE_NEW_PAYEE else fp_all

    fn_by_family: dict[str, int] = {}
    borderline_by_family: dict[str, int] = {}
    for fam in FRAUD_FAMILIES:
        fam_mask = labels == fam
        fn_by_family[fam] = int((fam_mask & ~pred).sum())
        borderline_by_family[fam] = int((fam_mask & (scores >= lo) & (scores < hi)).sum())

    borderline_mask = (scores >= lo) & (scores < hi)
    borderline_all = int(borderline_mask.sum())
    borderline_normals = normal_mask & borderline_mask
    borderline_normals_excl_new_payee = int((borderline_normals & ~new_payee).sum())

    body: dict[str, Any] = {
        "status": "ok",
        "round": 1,
        "run_id": run_id,
        "model_run_id": model_run_id,
        "max_rounds": MAX_ROUNDS,
        "promote_gate": "gdev_only",
        "confirmatory_run_id": "v1-gtest-49",
        "forbidden_promote_run_ids": ["v1-gtest-48", "v1-gtest-49"],
        "weakest_family": weakest,
        "pick_reason": pick_reason,
        "detect_thr": thr,
        "borderline_band": {"lo": lo, "hi": hi, "frac": BORDERLINE_FRAC},
        "ap_by_family": {k: ap_by.get(k) for k in FRAUD_FAMILIES},
        "n_pos": {k: int(n_pos.get(k) or 0) for k in FRAUD_FAMILIES},
        "mistake_buckets": {
            "fp_normals_all": int(fp_all.sum()),
            "fp_normals_excl_new_payee": int(fp_excl_new_payee.sum()),
            "fp_normals_new_payee_only": int(fp_new_payee_only.sum()),
            "fn_by_family": fn_by_family,
            "fn_weakest_family": fn_by_family.get(weakest, 0),
            "borderline_near_thr_all": borderline_all,
            "borderline_by_family": borderline_by_family,
            "borderline_normals_excl_new_payee": borderline_normals_excl_new_payee,
        },
        "h6_d_filters": {
            "hn_pool_excludes_is_new_payee": HN_EXCLUDE_NEW_PAYEE,
            "no_blind_top_k_mining": True,
        },
        "recommended_intervention": _intervention_for(weakest),
    }
    out = artifact_path or Path("data/validation/v1/h7_round1_diagnosis.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return body
