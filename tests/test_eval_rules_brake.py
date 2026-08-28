"""Plan 12 Phase B — row-value rules + Brake (lock-5 items 5–7)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.eval.brake import brake
from packages.policy.coverage import build_coverage_map
from packages.policy.rules import (
    FORBIDDEN_RULE_FIELDS,
    evaluate_rules,
    load_v0_rules,
    parse_predicate,
)


@pytest.fixture()
def db():
    init_db()
    seed_catalog(reset=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_v0_yaml_has_required_kinds_and_no_forbidden_fields():
    rules = load_v0_rules()
    kinds = {r.kind for r in rules}
    assert {"hard_flag", "nudge", "calm_down"} <= kinds
    for rule in rules:
        for pred in rule.predicates:
            assert pred.field not in FORBIDDEN_RULE_FIELDS
            assert pred.field != "is_authorized_push"


def test_fan_in_fires_on_value_not_key_presence():
    mule_inbound = {
        "fan_in_1h": 6,
        "account_age_days": 400,
        "is_new_payee": True,
        "is_new_device": False,
        "amount_vs_p30": 1.1,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "fan_out_1h": 0,
        "burst_velocity": 0.0,
        "payee_history_count": 0,
    }
    normal = {**mule_inbound, "fan_in_1h": 0, "is_new_payee": False, "amount_vs_p30": 1.0}
    mule_hits = evaluate_rules(mule_inbound)
    normal_hits = evaluate_rules(normal)
    assert any(r.id == "mule-fan-in-burst" for r in mule_hits.hits)
    assert not any(r.id == "mule-fan-in-burst" for r in normal_hits.hits)
    # Key present with zero must not fire (old key-presence bug).
    assert "fan_in_1h" in normal
    key_only = {"fan_in_1h": 0}
    assert not any(r.id == "mule-fan-in-burst" for r in evaluate_rules(key_only).hits)


def test_calm_down_allow_even_if_weak_model_score():
    genuine = {
        "is_new_payee": False,
        "is_new_device": False,
        "amount_vs_p30": 1.05,
        "fan_in_1h": 1,
        "fan_out_1h": 0,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "burst_velocity": 0.0,
        "account_age_days": 200,
        "payee_history_count": 12,
    }
    ev = evaluate_rules(genuine)
    assert any(r.kind == "calm_down" for r in ev.hits)
    assert not any(r.kind == "hard_flag" for r in ev.hits)
    decision = brake(pred_label_family="ato", score=0.42, hits=ev)
    assert decision.policy_action == "allow"
    assert "calm_down" in decision.reason_codes


def test_brake_app_not_decline_ato_may_decline_mule_payee_restricts():
    app_row = {
        "call_active_flag": True,
        "copy_paste_payee_flag": True,
        "is_new_payee": True,
        "is_new_device": False,
        "amount_vs_p30": 3.5,
        "pause_ms": 2400,
        "fan_in_1h": 0,
        "urgency_pressure": 0.8,
    }
    app_ev = evaluate_rules(app_row)
    app_d = brake(pred_label_family="app_fraud", score=0.97, hits=app_ev)
    assert app_d.policy_action != "decline"
    assert app_d.policy_action in {"notify", "hold"}

    ato_row = {
        "is_new_payee": True,
        "is_new_device": True,
        "amount_vs_p30": 3.0,
        "fan_in_1h": 0,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
    }
    ato_ev = evaluate_rules(ato_row)
    ato_d = brake(pred_label_family="ato", score=0.81, hits=ato_ev)
    assert ato_d.policy_action == "decline"

    mule_row = {
        "fan_in_1h": 12,
        "is_new_payee": True,
        "is_new_device": False,
        "amount_vs_p30": 0.9,
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "payee": "VID-SIM-U-000003",
    }
    mule_ev = evaluate_rules(mule_row)
    mule_d = brake(
        pred_label_family="mule",
        score=0.7,
        hits=mule_ev,
        payee="VID-SIM-U-000003",
    )
    assert mule_d.policy_action == "mule_credit_restrict"


def test_invoice_rule_uses_payload_booleans_not_gstin_string():
    event = {
        "rail": "upi_like",
        "label_family": "invoice_fraud",
        "party_ids": {"payer": "VID-SIM-C-000001", "payee": "VID-SIM-BENE-000001"},
        "amount_minor": 500_000,
        "features_auth": {"is_new_payee": True, "fan_in_1h": 0},
        "payload": {
            "beneficiary_changed": True,
            "gstin_checksum_ok": True,
            "gstin": "22AAAAA0000A1Z5",
            "is_authorized_push": True,
        },
    }
    hits = evaluate_rules(event)
    assert any(r.id == "invoice-beneficiary-swap" for r in hits.hits)
    for rule in load_v0_rules():
        for pred in rule.predicates:
            assert pred.field != "gstin"
            assert pred.field != "is_authorized_push"


def test_forbidden_predicate_rejected():
    with pytest.raises(ValueError, match="forbidden"):
        parse_predicate("smurf_cap_ratio >= 0.8")
    with pytest.raises(ValueError, match="forbidden"):
        parse_predicate("mule_account_age_days <= 3")
    with pytest.raises(ValueError, match="forbidden"):
        parse_predicate("is_authorized_push == true")


def test_coverage_map_still_24_and_t13_live(db):
    cmap = build_coverage_map(db)
    assert cmap["technique_count"] == 24
    assert len(cmap["cells"]) == 24
    t13 = next(c for c in cmap["cells"] if c["technique_id"] == "T13")
    assert t13["coverage_status"] in {"live_rule", "draft_rule"}
    assert "call-and-paste-new-payee" in t13["live_rule_ids"]
    t01 = next(c for c in cmap["cells"] if c["technique_id"] == "T01")
    assert t01["coverage_status"] == "live_rule"


def test_yaml_when_is_predicate_list():
    raw = yaml.safe_load(Path("data/rules/v0_rules.yaml").read_text(encoding="utf-8"))
    for row in raw:
        assert isinstance(row["when"], list)
        assert row["when"]
        assert all(isinstance(x, str) for x in row["when"])
