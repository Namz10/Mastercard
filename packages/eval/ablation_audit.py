"""H9 frozen-champion feature-group ablation audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from packages.eval.fit import (
    _app_ablation,
    _attach_rule_bits,
    _champion_pmap_scores,
    _encode,
    _zero_encoded_columns,
    load_champion,
    run_paths,
)
from packages.policy.rules import load_v0_rules
from packages.sim.ablation import APP_FLAG_COLS
from packages.sim.export import RUNS_DIR

# Static column groups (stamps resolved per-world — see _stamp_cols)
ABLATION_GROUPS: dict[str, list[str]] = {
    "app_flags": list(APP_FLAG_COLS),
    "stamps": [],  # filled dynamically via _stamp_cols
    "velocity": [
        "burst_velocity",
        "txn_velocity_24h",
        "fan_in_1h",
        "fan_out_1h",
        "fan_in_24h",
        "fan_out_24h",
    ],
    "temporal": ["hours_since_prev_txn", "hours_since_payee", "account_age_days"],
    "merchant": ["amount_vs_p30", "amount_vs_7d_mean"],
    "graph": [
        "fan_in_unique_payers_1h",
        "fan_in_unique_payers_24h",
        "payee_fan_out_1h",
        "in_out_asymmetry_24h",
        "unique_payees_7d",
        "payee_history_count",
    ],
}


def _stamp_cols(raw: pd.DataFrame, recipe: dict[str, Any]) -> list[str]:
    """Invoice/rule stamps + is_new_payee — mirrors fit._app_ablation stamp_zero (excludes app flags)."""
    cols = [
        c
        for c in ("beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag")
        if c in raw.columns
    ]
    cols.extend(c for c in raw.columns if str(c).startswith("rule__"))
    if "is_new_payee" in raw.columns:
        cols.append("is_new_payee")
    _ = recipe  # recipe reserved for app_flag_cols parity with fit._app_ablation
    return cols


def _group_cols(group: str, raw: pd.DataFrame, recipe: dict[str, Any]) -> list[str]:
    if group == "stamps":
        return _stamp_cols(raw, recipe)
    return [c for c in ABLATION_GROUPS[group] if c in raw.columns]


def _zero_group(x_ev: np.ndarray, raw_ev: pd.DataFrame, cols: list[str]) -> np.ndarray:
    if not cols:
        return x_ev
    return _zero_encoded_columns(x_ev, raw_ev, cols)


def _binary_ap(champ: Any, x_mod: np.ndarray, y_bin: np.ndarray) -> float:
    if y_bin.min() == y_bin.max():
        return float("nan")
    _, scores = _champion_pmap_scores(champ, x_mod)
    return float(average_precision_score(y_bin, scores))


def _rank_drops(group_blocks: dict[str, Any], *, key: str) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for gname, block in group_blocks.items():
        if not isinstance(block, dict):
            continue
        delta = block.get(key)
        if delta is None or not np.isfinite(delta):
            continue
        ranked.append({"group": gname, key: delta, "binary_ap": block.get("binary_ap")})
    ranked.sort(key=lambda r: r[key])
    return ranked


def audit_frozen_champion(
    model_run_id: str = "v1-train-46__loopm-train",
    run_ids: tuple[str, ...] = ("v1-gdev-47", "v1-gtest-48"),
    *,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Zero feature groups on frozen champion; score binary AP per world (no retrain)."""
    runs = runs_dir or RUNS_DIR
    champ = load_champion(model_run_id, models_dir=models_dir)
    recipe = champ.recipe
    rules = load_v0_rules()
    worlds: dict[str, Any] = {}

    for rid in run_ids:
        paths = run_paths(rid, runs)
        train_df = pd.read_parquet(paths["train"])
        split_df = pd.read_parquet(paths["split"])
        train_df = _attach_rule_bits(train_df, rules)
        y = split_df["label_family"].astype(str)
        x_raw = train_df.reindex(columns=champ.raw_columns, fill_value=0)
        x_ev, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
        y_bin = (y != "normal").to_numpy(dtype=int)

        baseline = _binary_ap(champ, x_ev, y_bin)
        base_ablation = _app_ablation(champ, x_ev, y, x_raw, recipe)
        without_stamps_ap = float(base_ablation["without_stamps"]["average_precision"])

        group_blocks: dict[str, Any] = {}
        for gname in ABLATION_GROUPS:
            cols = _group_cols(gname, x_raw, recipe)
            x_z = _zero_group(x_ev, x_raw, cols)
            ap = _binary_ap(champ, x_z, y_bin)
            group_blocks[gname] = {
                "columns_zeroed": cols,
                "binary_ap": ap,
                "delta_vs_baseline": ap - baseline if np.isfinite(baseline) else None,
                "delta_vs_without_stamps": ap - without_stamps_ap if np.isfinite(without_stamps_ap) else None,
            }
        worlds[rid] = {
            "baseline_binary_ap": baseline,
            "without_stamps": {
                "binary_ap": without_stamps_ap,
                "delta_vs_baseline": without_stamps_ap - baseline if np.isfinite(baseline) else None,
                "source": base_ablation.get("app_ablation_source", "frozen_champion"),
            },
            **group_blocks,
            "largest_drop_vs_baseline": _rank_drops(group_blocks, key="delta_vs_baseline"),
            "largest_drop_vs_without_stamps": _rank_drops(group_blocks, key="delta_vs_without_stamps"),
        }

    body: dict[str, Any] = {
        "model_run_id": model_run_id,
        "run_ids": list(run_ids),
        "groups": list(ABLATION_GROUPS.keys()),
        "ablation_source": "frozen_champion",
        "worlds": worlds,
    }
    dest = out_path or Path("data/validation/v1/h9_ablation_audit.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return body
