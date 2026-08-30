"""Hard-negative mining: high-scoring normals from G-dev → train inner_fit extras (H6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import (
    JSON_BAN,
    assert_no_denylist_payload,
    fit_champion,
    load_champion,
    load_recipe,
    run_paths,
    score_run,
    _attach_rule_bits,
    _encode,
    _fraud_score,
    _proba_map,
)
from packages.eval.split import folds_from_run, inner_folds_from_train
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR, TRAIN_ALLOWLIST

HN_ID_PREFIX = "evt-hn-"


def _hn_config(recipe: dict[str, Any]) -> dict[str, Any]:
    block = dict(recipe.get("hard_negatives") or {})
    loop_m = dict(recipe.get("loop_m") or {})
    return {
        "top_k": int(block.get("top_k", 500)),
        "extra_row_cap_frac": float(
            block.get("extra_row_cap_frac", loop_m.get("extra_row_cap_frac", 0.15))
        ),
        "genuine_fpr_eps": float(loop_m.get("genuine_fpr_eps", 0.02)),
        "other_family_rel_drop_eps": float(loop_m.get("other_family_rel_drop_eps", 0.05)),
    }


def mine_hard_negatives(
    gdev_run_id: str,
    model_run_id: str,
    *,
    top_k: int | None = None,
    min_score: float | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """Score G-dev with a frozen champion; return top normal rows by fraud score."""
    runs = runs_dir or RUNS_DIR
    recipe = load_recipe()
    cfg = _hn_config(recipe)
    k = int(top_k if top_k is not None else cfg["top_k"])
    champ = load_champion(model_run_id, models_dir=models_dir)
    paths = run_paths(gdev_run_id, runs)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    if len(train_df) != len(split_df):
        raise ValueError(f"train/split length mismatch for {gdev_run_id}")
    rules = load_v0_rules()
    train_df = _attach_rule_bits(train_df, rules)
    y = split_df["label_family"].astype(str)
    normal_mask = (y == "normal").to_numpy()
    if not normal_mask.any():
        return {"status": "skipped", "reason": "no_normal_rows", "mined": []}

    x_raw = train_df.drop(columns=["label_family"]).reindex(columns=champ.raw_columns, fill_value=0)
    x, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x)
    scores = _fraud_score(pmap, len(train_df))

    thr = min_score
    if thr is None:
        thr = float(champ.detect_thr if champ.detect_thr is not None else champ.op_threshold)

    normals = train_df.loc[normal_mask].copy()
    normal_scores = scores[normal_mask]
    normals = normals.assign(
        _hn_score=normal_scores,
        event_id=split_df.loc[normal_mask, "event_id"].astype(str).to_numpy(),
        label_family="normal",
    )
    candidates = normals.loc[normals["_hn_score"] >= thr].sort_values("_hn_score", ascending=False)
    if candidates.empty:
        return {
            "status": "skipped",
            "reason": "no_normals_above_min_score",
            "min_score": thr,
            "mined": [],
        }
    picked = candidates.head(k)
    mined = [
        {
            "event_id": str(row["event_id"]),
            "score": float(row["_hn_score"]),
            "label_family": "normal",
        }
        for _, row in picked.iterrows()
    ]
    return {
        "status": "ok",
        "gdev_run_id": gdev_run_id,
        "model_run_id": model_run_id,
        "min_score": thr,
        "top_k": k,
        "n_candidates": int(len(candidates)),
        "n_mined": len(mined),
        "mined": mined,
    }


def augment_train_with_hard_negatives(
    train_run_id: str,
    gdev_run_id: str,
    mined_event_ids: list[str] | frozenset[str],
    *,
    augmented_run_id: str | None = None,
    cap_frac: float | None = None,
    world_seed: int = 46,
    runs_dir: Path | None = None,
    forbidden_gtest_run_ids: tuple[str, ...] = ("v1-gtest-48", "v1-gtest-49"),
) -> tuple[str, int, frozenset[str]]:
    """Append mined normal rows from G-dev onto a train copy; return new run id and hn ids."""
    runs = runs_dir or RUNS_DIR
    recipe = load_recipe()
    cfg = _hn_config(recipe)
    frac = float(cap_frac if cap_frac is not None else cfg["extra_row_cap_frac"])
    aug_id = augmented_run_id or f"{train_run_id}__hn-train"
    id_set = {str(e) for e in mined_event_ids}
    if not id_set:
        raise ValueError("mined_event_ids is empty")

    orig = run_paths(train_run_id, runs)
    gdev = run_paths(gdev_run_id, runs)
    train_df = pd.read_parquet(orig["train"])
    split_df = pd.read_parquet(orig["split"])
    rules = load_v0_rules()
    train_for_fold = _attach_rule_bits(train_df, rules)
    packed_ref = folds_from_run(train_for_fold, split_df, seed=world_seed)
    train_fold_mask = packed_ref["folds"].reset_index(drop=True) == "train"
    ref_split = split_df.loc[train_fold_mask].reset_index(drop=True)
    if ref_split.empty:
        raise ValueError("no train-fold rows to anchor hard-negative timestamps")
    gdev_tr = pd.read_parquet(gdev["train"]).reset_index(drop=True)
    gdev_sp = pd.read_parquet(gdev["split"]).reset_index(drop=True)
    if len(gdev_tr) != len(gdev_sp):
        raise ValueError(f"gdev train/split length mismatch for {gdev_run_id}")
    gdev_sp = gdev_sp.assign(_row_idx=np.arange(len(gdev_sp)))
    pick_sp = gdev_sp.loc[gdev_sp["event_id"].astype(str).isin(id_set)].copy()
    pick_sp = pick_sp.loc[pick_sp["label_family"].astype(str) == "normal"]
    if pick_sp.empty:
        raise ValueError("no normal rows matched mined_event_ids on gdev split")
    gdev_tr = gdev_tr.iloc[pick_sp["_row_idx"].to_numpy()].reset_index(drop=True)
    gdev_sp = pick_sp.drop(columns=["_row_idx"]).reset_index(drop=True)
    if set(gdev_tr.columns) - set(TRAIN_ALLOWLIST):
        raise AssertionError("gdev train cols outside allowlist")

    cap = max(1, int(len(train_df) * frac))
    if len(gdev_tr) > cap:
        gdev_tr = gdev_tr.iloc[:cap].reset_index(drop=True)
        gdev_sp = gdev_sp.iloc[:cap].reset_index(drop=True)

    new_ids = [f"{HN_ID_PREFIX}{i:010d}" for i in range(len(gdev_tr))]
    gdev_sp = gdev_sp.copy()
    gdev_sp["event_id"] = new_ids
    rng = np.random.default_rng(world_seed)
    ref_idx = rng.choice(len(ref_split), size=len(gdev_sp), replace=True)
    ref_rows = ref_split.iloc[ref_idx].reset_index(drop=True)
    gdev_sp["event_ts"] = ref_rows["event_ts"].astype(str).to_numpy()
    gdev_sp["payer"] = ref_rows["payer"].astype(str).to_numpy()
    gdev_sp["payee"] = ref_rows["payee"].astype(str).to_numpy()
    gdev_sp["label_family"] = "normal"

    out_tr = pd.concat([train_df, gdev_tr.reset_index(drop=True)], ignore_index=True)
    out_sp = pd.concat([split_df, gdev_sp], ignore_index=True)
    hn_ids = frozenset(new_ids)

    for gtest_id in forbidden_gtest_run_ids:
        gpath = run_paths(gtest_id, runs)
        if gpath["split"].is_file():
            gtest_ids = set(pd.read_parquet(gpath["split"])["event_id"].astype(str))
            if hn_ids & gtest_ids:
                raise AssertionError(f"hard-negative event_ids overlap {gtest_id}")

    dest = runs / aug_id
    dest.mkdir(parents=True, exist_ok=True)
    out_tr.to_parquet(dest / "train.parquet", index=False)
    out_sp.to_parquet(dest / "split.parquet", index=False)
    (dest / "sidecar.json").write_text(
        json.dumps(
            {
                "run_id": aug_id,
                "mode": "hard_negative_train",
                "source_train_run_id": train_run_id,
                "gdev_run_id": gdev_run_id,
                "n_extra": int(len(gdev_tr)),
                "extra_row_cap_frac": frac,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (dest / "manifest.json").write_text(
        json.dumps({"run_id": aug_id, "row_count": len(out_tr), "n_extra": int(len(gdev_tr))}, indent=2),
        encoding="utf-8",
    )
    (dest / "_DONE").write_text("DONE\n", encoding="utf-8")
    return aug_id, int(len(gdev_tr)), hn_ids


def assert_hn_ids_inner_fit(
    train_run_id: str,
    hn_ids: frozenset[str],
    *,
    world_seed: int,
    runs_dir: Path | None = None,
) -> None:
    """Guard: hard-negative extras must land in inner_fit, not inner_val."""
    runs = runs_dir or RUNS_DIR
    paths = run_paths(train_run_id, runs)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    rules = load_v0_rules()
    train_df = _attach_rule_bits(train_df, rules)
    packed = folds_from_run(train_df, split_df, seed=world_seed)
    inner = inner_folds_from_train(
        split_df.reset_index(drop=True),
        packed["folds"].reset_index(drop=True),
        exclude_event_ids=hn_ids,
    )
    sp = split_df.reset_index(drop=True)
    for eid in hn_ids:
        loc = sp.index[sp["event_id"].astype(str) == eid]
        if len(loc) == 0:
            raise AssertionError(f"hn id missing from split: {eid}")
        if inner.iloc[int(loc[0])] != "inner_fit":
            raise AssertionError(f"hn id {eid} not in inner_fit: {inner.iloc[int(loc[0])]}")


def run_hard_negative_loop(
    train_run_id: str = "v1-train-46",
    gdev_run_id: str = "v1-gdev-47",
    *,
    base_model_run_id: str = "v1-train-46__loopm-train",
    train_seed: int = 46,
    gtest_run_ids: tuple[str, ...] = ("v1-gtest-48", "v1-gtest-49"),
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    """Mine → augment → retrain → score baseline vs HN model on frozen G-tests."""
    runs = runs_dir or RUNS_DIR
    recipe = load_recipe()
    cfg = _hn_config(recipe)
    aug_id = f"{train_run_id}__hn-train"
    hn_model_id = aug_id

    mined_body = mine_hard_negatives(
        gdev_run_id,
        base_model_run_id,
        runs_dir=runs,
        models_dir=models_dir,
    )
    if mined_body.get("status") != "ok":
        return {"status": "skipped", "reason": mined_body.get("reason"), "mine": mined_body}

    mined_ids = [m["event_id"] for m in mined_body["mined"]]
    aug_id, n_extra, hn_ids = augment_train_with_hard_negatives(
        train_run_id,
        gdev_run_id,
        mined_ids,
        augmented_run_id=aug_id,
        world_seed=train_seed,
        runs_dir=runs,
        forbidden_gtest_run_ids=gtest_run_ids,
    )
    assert_hn_ids_inner_fit(aug_id, hn_ids, world_seed=train_seed, runs_dir=runs)

    fit_champion(
        aug_id,
        world_seed=train_seed,
        runs_dir=runs,
        models_dir=models_dir,
        force_train_event_ids=hn_ids,
        dest_run_id=hn_model_id,
    )

    scores: dict[str, Any] = {}
    for gid in gtest_run_ids:
        before = score_run(gid, model_run_id=base_model_run_id, runs_dir=runs, models_dir=models_dir, all_rows=True)
        after = score_run(gid, model_run_id=hn_model_id, runs_dir=runs, models_dir=models_dir, all_rows=True)
        scores[gid] = {
            "genuine_fp_before": before["metrics"].get("genuine_fp"),
            "genuine_fp_after": after["metrics"].get("genuine_fp"),
            "recall_before": before["metrics"].get("recall_at_op"),
            "recall_after": after["metrics"].get("recall_at_op"),
            "cost_before": (before["metrics"].get("cost_sketch") or {}).get("expected_cost_per_row"),
            "cost_after": (after["metrics"].get("cost_sketch") or {}).get("expected_cost_per_row"),
            "metrics_before": before["metrics"],
            "metrics_after": after["metrics"],
        }

    g49 = scores.get("v1-gtest-49") or {}
    fp0, fp1 = g49.get("genuine_fp_before"), g49.get("genuine_fp_after")
    fpr_eps = cfg["genuine_fpr_eps"]
    fp_ok = fp0 is not None and fp1 is not None and fp1 <= fp0 + fpr_eps and fp1 < fp0
    rec0, rec1 = g49.get("recall_before"), g49.get("recall_after")
    rec_ok = True
    if rec0 and rec1 and rec0 > 0:
        rec_ok = rec1 >= rec0 * 0.95

    body: dict[str, Any] = {
        "status": "completed",
        "train_run_id": train_run_id,
        "gdev_run_id": gdev_run_id,
        "augmented_run_id": aug_id,
        "base_model_run_id": base_model_run_id,
        "hn_model_run_id": hn_model_id,
        "n_extra": n_extra,
        "hn_event_ids": sorted(hn_ids),
        "mine": mined_body,
        "genuine_fpr_eps": fpr_eps,
        "comparison": scores,
        "pass": bool(fp_ok and rec_ok),
        "genuine_fp_ok": fp_ok,
        "recall_ok": rec_ok,
    }
    for key in JSON_BAN:
        if key in body:
            raise AssertionError(f"banned key in H6 body: {key}")
    assert_no_denylist_payload(body)

    out = Path("data/validation/v1/h6_hard_negatives.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return body
