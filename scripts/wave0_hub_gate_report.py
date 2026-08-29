#!/usr/bin/env python3
"""Wave 0.4 — report-only hub gate on v1-gtest-48 (no Brake edits)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.eval.fit import (  # noqa: E402
    _attach_rule_bits,
    _encode,
    _fraud_score,
    _pred_family,
    _proba_map,
    _rule_hit_masks,
    _vectorized_brake_actions,
    load_champion,
)
from packages.policy.rules import load_v0_rules

GTEST_RUN = "v1-gtest-48"
CHAMPION = "v1-train-46__loopm-train"
OUT = ROOT / "data" / "validation" / "v1" / "hub_gate_report.json"
HUB_PREFIX = "VID-SIM-HUB-"


def main() -> dict:
    run_dir = ROOT / "data" / "runs" / GTEST_RUN
    train = pd.read_parquet(run_dir / "train.parquet")
    split = pd.read_parquet(run_dir / "split.parquet")
    if "event_id" in train.columns and "event_id" in split.columns:
        meta = split[["event_id", "payee", "payer"]]
        payee = meta.set_index("event_id").loc[train["event_id"], "payee"].astype(str).to_numpy()
        payer = meta.set_index("event_id").loc[train["event_id"], "payer"].astype(str).to_numpy()
    else:
        payee = split["payee"].astype(str).to_numpy()
        payer = split["payer"].astype(str).to_numpy()

    rules = load_v0_rules()
    train_scored = _attach_rule_bits(train, rules)
    champ = load_champion(CHAMPION)
    x_raw = train_scored.drop(columns=["label_family"]).reindex(columns=champ.raw_columns, fill_value=0)
    x, _ = _encode(x_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    raw_pmap = _proba_map(champ.model, x)
    if getattr(champ, "pmap_calibrators", None):
        from packages.eval.fit import _apply_pmap_calibrators

        pmap = _apply_pmap_calibrators(raw_pmap, champ.pmap_calibrators, champ.classes)
    else:
        pmap = raw_pmap
    scores = _fraud_score(pmap, len(train_scored))
    pred = _pred_family(pmap, champ.classes, len(train_scored))
    payee_s = pd.Series(payee)
    actions = _vectorized_brake_actions(x_raw, pred, scores, rules, payees=payee_s)
    hard, _, applies = _rule_hit_masks(x_raw, rules, scores=scores)

    hub_mask = payee_s.str.startswith(HUB_PREFIX).to_numpy()
    hub_df = train_scored.loc[hub_mask].copy()
    hub_actions = pd.Series(actions)[hub_mask]
    hub_hard = hard[hub_mask]
    hub_mule_rule = applies.get("mule", np.zeros(len(train_scored), dtype=bool))[hub_mask]
    fan = hub_df["fan_in_1h"].fillna(0).astype(int)

    fan_ge6 = int((fan >= 6).sum())
    restrict = int((hub_actions == "mule_credit_restrict").sum())
    hard_n = int(hub_hard.sum())
    mule_rule_n = int(hub_mule_rule.sum())

    body = {
        "run_id": GTEST_RUN,
        "model_run_id": CHAMPION,
        "hub_payee_prefix": HUB_PREFIX,
        "n_hub_rows": int(hub_mask.sum()),
        "n_unique_hub_payees": int(payee_s[hub_mask].nunique()),
        "fan_in_1h": {
            "min": int(fan.min()) if len(fan) else 0,
            "p50": float(fan.quantile(0.5)) if len(fan) else 0.0,
            "p90": float(fan.quantile(0.9)) if len(fan) else 0.0,
            "max": int(fan.max()) if len(fan) else 0,
            "ge_6": fan_ge6,
        },
        "hub_actions": hub_actions.value_counts().to_dict(),
        "hub_mule_credit_restrict": restrict,
        "hub_hard_flag_rows": hard_n,
        "hub_mule_rule_rows": mule_rule_n,
        "hub_fan_in_ge6_with_restrict": int(
            ((fan >= 6) & (hub_actions == "mule_credit_restrict").to_numpy()).sum()
        ),
        "hub_fan_in_ge6_with_hard_flag": int(((fan >= 6) & hub_hard).sum()),
        "wave1_gate_spec": "any hub with fan_in_1h>=6 hard-flagged as mule → fail (measure only in Wave 0)",
        "note": "Report-only; Brake unchanged in Wave 0.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(body, indent=2))
    return body


if __name__ == "__main__":
    main()
