"""Post-G43 Brake invariants — write before / verify after E1b semantics."""

from __future__ import annotations

from packages.eval.brake import brake
from packages.eval.fit import apply_iso_brake_upgrade
from packages.policy.rules import evaluate_rules


def test_app_never_decline():
    row = {
        "call_active_flag": True,
        "copy_paste_payee_flag": True,
        "is_new_payee": True,
        "is_new_device": False,
        "amount_vs_p30": 4.0,
        "pause_ms": 3000,
        "urgency_pressure": 0.9,
        "fan_in_1h": 0,
    }
    ev = evaluate_rules(row)
    d = brake(pred_label_family="app_fraud", score=0.99, hits=ev)
    assert d.policy_action != "decline"


def test_iso_never_downgrades_mule_hold_decline():
    for locked in ("mule_credit_restrict", "hold", "decline"):
        action, reasons = apply_iso_brake_upgrade(locked, True, [])
        assert action == locked
        assert "iso_anomaly" not in reasons


def test_min_score_gates_hard_flag():
    row = {
        "fan_in_1h": 6,
        "amount_vs_p30": 0.8,
        "fan_out_1h": 0,
        "is_new_payee": False,
        "is_new_device": False,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "burst_velocity": 0.0,
        "account_age_days": 200,
        "payee_history_count": 3,
    }
    ev = evaluate_rules(row)
    low = brake(pred_label_family="normal", score=0.05, hits=ev)
    high = brake(pred_label_family="normal", score=0.95, hits=ev)
    assert low.policy_action != "mule_credit_restrict"
    assert high.policy_action == "mule_credit_restrict"


def test_mule_nudge_does_not_restrict_at_low_score():
    row = {
        "fan_in_1h": 4,
        "amount_vs_p30": 0.8,
        "fan_out_1h": 4,
        "is_new_payee": False,
        "is_new_device": False,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "burst_velocity": 0.0,
        "account_age_days": 200,
        "payee_history_count": 3,
    }
    ev = evaluate_rules(row)
    d = brake(pred_label_family="normal", score=0.05, hits=ev)
    assert d.policy_action != "mule_credit_restrict"


def test_hub_shaped_row_fan_in_normal_not_restricted_without_hard_flag():
    row = {
        "fan_in_1h": 8,
        "amount_vs_p30": 1.0,
        "fan_out_1h": 0,
        "is_new_payee": False,
        "is_new_device": False,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "burst_velocity": 0.0,
        "account_age_days": 400,
        "payee_history_count": 20,
    }
    ev = evaluate_rules(row)
    d = brake(pred_label_family="normal", score=0.2, hits=ev)
    assert d.policy_action != "mule_credit_restrict"


def test_pred_mule_low_score_not_restricted_without_hard_flag():
    d = brake(pred_label_family="mule", score=0.1, hits=[])
    assert d.policy_action != "mule_credit_restrict"
