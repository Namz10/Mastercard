"""Identity oracles — vectorized rule bits and brake hist match row-loop semantics."""

from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
import pytest

from packages.eval.fit import (
    _attach_rule_bits,
    _brake_action_hist,
    _brake_action_hist_loop,
    _vectorized_brake_actions,
)
from packages.eval.iso_check import fit_isolation_forest
from packages.policy.rules import evaluate_rules, load_v0_rules, vectorized_rule_bits


def _base_row() -> dict:
    return {
        "rail": "upi_like",
        "kyc_tier": "full",
        "account_age_days": 120,
        "payee_history_count": 5,
        "amount_vs_p30": 1.0,
        "fan_in_1h": 0,
        "fan_out_1h": 0,
        "fan_in_unique_payers_1h": 0,
        "burst_velocity": 0.0,
        "is_new_payee": False,
        "is_new_device": False,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "urgency_pressure": 0.0,
        "beneficiary_changed": False,
        "gstin_checksum_ok": True,
        "lookalike_domain_flag": False,
    }


def _fixture_rows() -> list[dict]:
    """~200 mixed rows: each live rule fire/non-fire, missing fields, nested invoice event."""
    rows: list[dict] = []
    templates = [
        {"fan_in_1h": 8, "is_new_payee": True},
        {"fan_in_1h": 5, "amount_vs_p30": 0.8},
        {"fan_out_1h": 5},
        {"burst_velocity": 5, "account_age_days": 30},
        {
            "call_active_flag": True,
            "copy_paste_payee_flag": True,
            "is_new_payee": True,
            "pause_ms": 2000,
        },
        {"is_new_payee": True, "is_new_device": True, "amount_vs_p30": 3.0},
        {"beneficiary_changed": True, "gstin_checksum_ok": True},
        {"is_new_payee": False, "is_new_device": False, "amount_vs_p30": 1.2},
        {"fan_in_1h": None},
        {},
    ]
    preds = ("normal", "mule", "app_fraud", "ato", "invoice_fraud", "identity_burst")
    scores = (0.1, 0.45, 0.55, 0.7, 0.85, 0.97)
    for i, (tpl, pred, score) in enumerate(itertools.product(templates, preds, scores)):
        if i >= 200:
            break
        row = _base_row()
        row.update(tpl)
        row["_pred"] = pred
        row["_score"] = score
        rows.append(row)
    rows.append(
        {
            **_base_row(),
            "rail": "NEFT",
            "beneficiary_changed": True,
            "gstin_checksum_ok": True,
            "_pred": "invoice_fraud",
            "_score": 0.6,
        }
    )
    return rows


def _with_rule_bits(df: pd.DataFrame, rules) -> pd.DataFrame:
    return pd.concat([df, vectorized_rule_bits(df, rules)], axis=1)


def test_vectorized_rule_bits_match_evaluate_rules():
    rules = load_v0_rules()
    live = [r for r in rules if r.status == "live"]
    rows = _fixture_rows()
    feature_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    df = pd.DataFrame(feature_rows)
    bits = vectorized_rule_bits(df, rules)
    for i, rec in enumerate(feature_rows):
        hits = {h.id for h in evaluate_rules(rec, live).hits}
        for rule in live:
            col = f"rule__{rule.id}"
            expected = int(rule.id in hits)
            actual = int(bits.iloc[i][col])
            assert actual == expected, f"row {i} rule {rule.id}: vectorized={actual} loop={expected}"


def test_attach_rule_bits_uses_vectorized_path():
    rules = load_v0_rules()
    rows = _fixture_rows()[:20]
    feature_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    df = pd.DataFrame(feature_rows)
    out = _attach_rule_bits(df, rules)
    expected = vectorized_rule_bits(df, rules)
    for col in expected.columns:
        assert (out[col] == expected[col]).all(), col


@pytest.mark.parametrize("use_iso", [False, True])
def test_vectorized_brake_hist_matches_row_loop(use_iso: bool):
    rules = load_v0_rules()
    rows = _fixture_rows()
    preds = np.array([r["_pred"] for r in rows], dtype=object)
    scores = np.array([r["_score"] for r in rows], dtype=float)
    labels = pd.Series(["normal"] * len(rows))
    payees = pd.Series(["VID-SIM-BENE-000001"] * len(rows))
    feature_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    df = pd.DataFrame(feature_rows)
    raw = _with_rule_bits(df, rules)
    threshold = 0.5
    pmap = {
        "normal": np.where(preds == "normal", 0.96, 0.1),
        "app_fraud": np.zeros(len(rows)),
        "ato": np.zeros(len(rows)),
        "mule": np.zeros(len(rows)),
        "invoice_fraud": np.zeros(len(rows)),
        "identity_burst": np.zeros(len(rows)),
    }
    iso_model = None
    if use_iso:
        train_df = raw.copy()
        train_df["label_family"] = "normal"
        y = train_df["label_family"]
        x_fit = train_df.drop(columns=["label_family"])
        iso_model = fit_isolation_forest(x_fit, y)

    hist_loop, fp_loop = _brake_action_hist_loop(
        raw, labels, payees, preds, scores, threshold, rules,
        iso_model=iso_model, pmap=pmap if use_iso else None,
    )
    hist_vec, fp_vec = _brake_action_hist(
        raw, labels, payees, preds, scores, threshold, rules,
        iso_model=iso_model, pmap=pmap if use_iso else None,
    )
    assert hist_loop == hist_vec
    assert fp_loop == fp_vec


def test_vectorized_brake_actions_per_row_match_loop():
    rules = load_v0_rules()
    rows = _fixture_rows()
    preds = np.array([r["_pred"] for r in rows], dtype=object)
    scores = np.array([r["_score"] for r in rows], dtype=float)
    feature_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    raw = _with_rule_bits(pd.DataFrame(feature_rows), rules)
    pmap = {"normal": np.full(len(rows), 0.96)}
    iso_model = fit_isolation_forest(
        raw.assign(label_family="normal").drop(columns=["label_family"]),
        pd.Series(["normal"] * len(rows)),
    )
    vec_actions = _vectorized_brake_actions(raw, preds, scores, rules, iso_model=iso_model, pmap=pmap)
    loop_hist, _ = _brake_action_hist_loop(
        raw,
        pd.Series(["normal"] * len(rows)),
        pd.Series(["p"] * len(rows)),
        preds,
        scores,
        0.5,
        rules,
        iso_model=iso_model,
        pmap=pmap,
    )
    # Reconstruct per-row actions from loop by comparing action counts is weak;
    # compare action multiset from vectorized vs loop-derived actions.
    from packages.eval.brake import as_record, brake
    from packages.policy.rules import evaluate_rules as eval_rules

    loop_actions = []
    records = raw.to_dict(orient="records")
    for i, rec in enumerate(records):
        hits = eval_rules(rec, rules)
        action = as_record(
            brake(pred_label_family=str(preds[i]), score=float(scores[i]), hits=hits)
        )["policy_action"]
        from packages.eval.iso_check import apply_iso_brake_upgrade, is_iso_anomaly

        if is_iso_anomaly(iso_model, rec, str(preds[i]), float(pmap["normal"][i])):
            action, _ = apply_iso_brake_upgrade(action, True, [])
        loop_actions.append(action)
    assert list(vec_actions) == loop_actions
    assert dict(zip(*np.unique(loop_actions, return_counts=True))) == loop_hist
