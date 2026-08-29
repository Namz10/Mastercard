"""Phase C — four injectors + mix."""

from __future__ import annotations

import numpy as np
import pytest

from packages.sim.inject.gstin import gstin_checksum_ok, make_valid_gstin
from packages.sim.inject.jitter import jitter_signals
from packages.sim.inject.mix import apply_mix
from packages.sim.ledger import TECHNIQUE_IDS
from packages.sim.world import generate_quiet_world


@pytest.fixture(scope="module")
def mixed_world():
    rng = np.random.default_rng(42)
    world = generate_quiet_world(world_seed=42, n_customers=56, n_merchants=12, sim_days=36)
    report = apply_mix(world, rng, target_rate=0.02, pin=True)
    return world, report


def test_gstin_checksum_passes():
    g = make_valid_gstin(42)
    assert len(g) == 15
    assert gstin_checksum_ok(g)


def test_jitter_clamped_and_canary_pin():
    rng = np.random.default_rng(0)
    raw = {"liveness_score": 0.4, "smurf_cap_ratio": 0.9, "fan_in_1h": 10}
    pinned = jitter_signals(rng, raw, pin=True)
    assert pinned == raw
    bounced = [jitter_signals(np.random.default_rng(i), raw, pin=False) for i in range(20)]
    assert all(0.0 <= b["liveness_score"] <= 1.0 for b in bounced)
    assert all(0.01 <= b["smurf_cap_ratio"] <= 1.0 for b in bounced)
    assert any(abs(b["fan_in_1h"] - 10) > 0 for b in bounced)


def test_mix_families_present_and_not_technique_ids(mixed_world):
    world, report = mixed_world
    families = {e["label_family"] for e in world.events}
    for needed in ("normal", "mule", "identity_burst", "ato", "app_fraud", "invoice_fraud"):
        assert needed in families
        assert report["counts"].get(needed, 0) >= 1
    for e in world.events:
        assert e["label_family"] not in TECHNIQUE_IDS


def test_t12_device_shift_is_ato_not_identity_burst(mixed_world):
    world, report = mixed_world
    ato_rows = [e for e in world.events if e["label_family"] == "ato"]
    assert ato_rows
    assert any(e["features_auth"]["is_new_device"] for e in ato_rows)
    farmed = report["farmed_ato"]
    ident = [
        e
        for e in world.events
        if e["label_family"] == "identity_burst" and e["party_ids"]["payer"] == farmed
    ]
    assert not ident


def test_fan_in_computed_not_copied_from_catalog(mixed_world):
    world, report = mixed_world
    knob = report["knobs_used"]["graph_mule"]["fan_in_1h"]
    mule_in = [
        e
        for e in world.events
        if e["label_family"] == "mule" and e["party_ids"]["payee"].startswith("VID-SIM-U-")
    ]
    assert mule_in
    values = [e["features_auth"]["fan_in_1h"] for e in mule_in]
    assert not all(v == knob for v in values)
    assert min(values) == 0
    assert max(values) >= 5


def test_app_inject_does_not_scan_ledger():
    rng = np.random.default_rng(42)
    world = generate_quiet_world(world_seed=42, n_customers=56, n_merchants=12, sim_days=36)
    apply_mix(world, rng, target_rate=0.02, pin=True)
    from packages.sim.inject.app_session import inject_app_sessions

    class NoScan(list):
        def __iter__(self):
            raise AssertionError("APP inject must not iterate world.events")

    world.events = NoScan(world.events)
    written = inject_app_sessions(
        world,
        np.random.default_rng(99),
        n_victims=3,
        signals={
            "call_active_flag": True,
            "copy_paste_payee_flag": True,
            "pause_ms": 1800,
            "urgency_pressure": 0.85,
        },
        after_day=30,
    )
    assert len(written) >= 1


def test_app_flags_only_on_app_rows(mixed_world):
    world, _ = mixed_world
    apps = [e for e in world.events if e["label_family"] == "app_fraud"]
    others = [e for e in world.events if e["label_family"] != "app_fraud"]
    assert len(apps) >= 3
    assert all(e["features_auth"]["call_active_flag"] is True for e in apps)
    assert all(e["features_auth"]["copy_paste_payee_flag"] is True for e in apps)
    assert all(e["features_auth"]["call_active_flag"] is False for e in others)
    assert all(e.get("payload", {}).get("is_authorized_push") is True for e in apps)


def test_liveness_null_after_onboarding(mixed_world):
    world, _ = mixed_world
    onboard = [e for e in world.events if e["rail"] == "onboarding"]
    assert onboard
    assert all(e["features_auth"]["liveness_score"] is not None for e in onboard)
    payers = {o["party_ids"]["payer"] for o in onboard}
    later = [
        e
        for e in world.events
        if e["rail"] != "onboarding" and e["party_ids"]["payer"] in payers
    ]
    assert later
    assert all(e["features_auth"]["liveness_score"] is None for e in later)
    assert all(e["features_auth"]["doc_consistency"] is None for e in later)


def test_invoice_checksum_pass_wrong_account(mixed_world):
    world, _ = mixed_world
    inv = [e for e in world.events if e["label_family"] == "invoice_fraud"]
    assert inv
    for e in inv:
        assert e["payload"]["gstin_checksum_ok"] is True
        assert e["payload"]["beneficiary_changed"] is True
        assert gstin_checksum_ok(e["payload"]["gstin"])
        assert e["party_ids"]["payee"].startswith("VID-SIM-BENE-")


def test_mix_rate_in_band_small_seeded_run(mixed_world):
    _world, report = mixed_world
    rate = report["fraud_rate"]
    assert 0.01 <= rate <= 0.03
    assert report["ident_burst"] >= 1
    assert report["ato_burst"] >= 1
    assert report["n_app"] >= 3
    assert report["n_hop"] >= 1
    assert report["n_smurf"] >= 1
    assert report["n_dust"] >= 1


def test_seasoning_clamped_on_short_calendar(mixed_world):
    _, report = mixed_world
    ident = report["seasoning"]["identity_burst"]
    assert ident["clamped"] is True
    assert ident["effective_days"] == 36 - 14


def test_replay_copies_invoice_payload_booleans():
    from datetime import datetime, timezone
    from packages.sim.features import replay_features
    from packages.sim.ledger import make_event
    t0 = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    payer = "VID-SIM-C-000001"
    payee = "VID-SIM-BENE-000001"
    meta = {
        payer: {"created_ts": t0, "device_hash": "dev-a", "kyc_tier": "tier1", "opening_balance_minor": 100_000_000},
        payee: {"created_ts": t0, "device_hash": "dev-b", "kyc_tier": "tier1", "opening_balance_minor": 100_000_000},
    }
    ev = make_event(
        seq=1,
        ts=t0,
        rail="NEFT",
        payer=payer,
        payee=payee,
        amount_minor=500000,
        label_family="invoice_fraud",
        features_auth={},
        payload={"beneficiary_changed": True, "gstin_checksum_ok": True, "lookalike_domain_flag": True},
    )
    [out], _ = replay_features([ev], meta)
    fa = out["features_auth"]
    assert fa["beneficiary_changed"] is True
    assert fa["gstin_checksum_ok"] is True
    assert fa["lookalike_domain_flag"] is True


def test_genuine_invoice_flags_false_after_replay():
    from datetime import datetime, timezone
    from packages.sim.features import replay_features
    from packages.sim.ledger import make_event
    t0 = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    payer = "VID-SIM-C-000001"
    payee = "VID-SIM-M-000001"
    meta = {
        payer: {"created_ts": t0, "device_hash": "dev-a", "kyc_tier": "tier1", "opening_balance_minor": 100_000_000},
        payee: {"created_ts": t0, "device_hash": "dev-b", "kyc_tier": "tier1", "opening_balance_minor": 100_000_000},
    }
    ev = make_event(
        seq=1,
        ts=t0,
        rail="UPI",
        payer=payer,
        payee=payee,
        amount_minor=500,
        label_family="normal",
        features_auth={},
    )
    [out], _ = replay_features([ev], meta)
    fa = out["features_auth"]
    assert fa["beneficiary_changed"] is False
    assert fa["gstin_checksum_ok"] is False
    assert fa["lookalike_domain_flag"] is False


def test_fan_in_unique_same_payer_twice():
    from datetime import datetime, timedelta, timezone
    from packages.sim.features import FeatureComputer
    t0 = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    fc = FeatureComputer()
    fc.ensure("P1", t0, "dev-1", "tier1", 100_000_000)
    fc.ensure("M1", t0, "dev-m", "tier1", 100_000_000)
    
    fc.snapshot_and_apply(ts=t0, payer="P1", payee="M1", amount_minor=100, device_hash="dev-1")
    f2 = fc.snapshot_and_apply(ts=t0 + timedelta(minutes=5), payer="P1", payee="M1", amount_minor=200, device_hash="dev-1")
    
    assert f2["fan_in_1h"] == 1
    f3 = fc.snapshot_and_apply(ts=t0 + timedelta(minutes=10), payer="P1", payee="M1", amount_minor=300, device_hash="dev-1")
    assert f3["fan_in_1h"] == 2
    assert f3["fan_in_unique_payers_1h"] == 1


def test_burst_velocity_unique_outbound_not_event_count():
    from datetime import datetime, timedelta, timezone
    from packages.sim.features import FeatureComputer
    t0 = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    fc = FeatureComputer()
    fc.ensure("P1", t0, "dev-1", "tier1", 100_000_000)
    fc.ensure("M1", t0, "dev-m", "tier1", 100_000_000)
    
    fc.snapshot_and_apply(ts=t0, payer="P1", payee="M1", amount_minor=100, device_hash="dev-1")
    fc.snapshot_and_apply(ts=t0 + timedelta(minutes=1), payer="P1", payee="M1", amount_minor=100, device_hash="dev-1")
    f3 = fc.snapshot_and_apply(ts=t0 + timedelta(minutes=2), payer="P1", payee="M1", amount_minor=100, device_hash="dev-1")
    
    assert f3["fan_out_1h"] == 2
    assert f3["burst_velocity"] == 1.0

