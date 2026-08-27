"""Step 11 — Defend handoff tests."""

import pytest

from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.catalog.features import derive_features_expected
from packages.catalog.query import get_spec_by_vector_id, set_atlas_status
from packages.policy.coverage import build_coverage_map
from packages.policy.loop_i import draft_rule_from_spec
from packages.policy.rules import load_v0_rules, match_rules_to_features


@pytest.fixture()
def db():
    init_db()
    seed_catalog(reset=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_derive_features_from_app_session():
    feats = derive_features_expected(
        "app_session",
        {
            "call_active_flag": True,
            "copy_paste_payee_flag": True,
            "new_payee": True,
            "urgency_pressure": 0.8,
            "pause_ms": 100,
            "persuasion_labels": ["x"],
        },
        control_bypassed=["human_callback", "otp"],
        economic_class="APP",
    )
    assert "call_active_flag" in feats
    assert "is_new_payee" in feats
    assert "is_authorized_push" in feats


def test_t13_loop_i_draft_or_live_rule(db):
    spec = get_spec_by_vector_id(db, "t13-upi-impersonation-app")
    assert spec is not None
    draft = draft_rule_from_spec(spec)
    # T13 should get call-and-paste draft OR match live v0 rule
    live = match_rules_to_features(spec.features_expected, load_v0_rules())
    assert draft["coverage_status"] in {"draft_rule", "live_rule"} or len(live) >= 1
    if draft["coverage_status"] == "draft_rule":
        assert draft["draft_rule"]["id"] == "call-and-paste-new-payee"


def test_coverage_map_has_24_techniques(db):
    cmap = build_coverage_map(db)
    assert cmap["technique_count"] == 24
    assert len(cmap["cells"]) == 24
    t13 = next(c for c in cmap["cells"] if c["technique_id"] == "T13")
    assert t13["coverage_status"] in {"live_rule", "draft_rule"}
    assert "call_active_flag" in t13["features_expected"]


def test_named_gap_for_t07(db):
    spec = get_spec_by_vector_id(db, "t07-card-testing")
    if spec is None:
        pytest.skip("t07 row not in seed")
    draft = draft_rule_from_spec(spec)
    assert draft["coverage_status"] == "named_gap"


def test_defend_miss_keeps_open(db):
    set_atlas_status(db, "t13-upi-impersonation-app", "defending")
    row = set_atlas_status(db, "t13-upi-impersonation-app", "open")
    assert row.status == "open"
