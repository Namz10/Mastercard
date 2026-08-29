"""Hardening: mule alloc, hubs, H(t-), calendar clamp, no stamp labels."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from packages.eval.brake import brake
from packages.policy.rules import evaluate_rules
from packages.sim.features import FeatureComputer
from packages.sim.inject.jitter import clamp_ts
from packages.sim.inject.mix import apply_mix, fraud_row_target
from packages.sim.world import generate_quiet_world


def test_clamp_ts_stays_inside_horizon():
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert clamp_ts(t0 - timedelta(days=3), t0, 90) >= t0
    assert clamp_ts(t0 + timedelta(days=120), t0, 90) < t0 + timedelta(days=90)


def test_mule_row_count_tracks_alloc():
    rng = np.random.default_rng(7)
    world = generate_quiet_world(world_seed=7, n_customers=48, n_merchants=10, sim_days=40)
    n_normal = sum(1 for e in world.events if e["label_family"] == "normal")
    n_fraud = fraud_row_target(n_normal, 0.02)
    report = apply_mix(world, rng, target_rate=0.02, pin=True)
    mule_n = report["counts"].get("mule", 0)
    assert mule_n >= report["alloc"]["mule"]
    assert mule_n > 30 or n_fraud < 40


def test_legitimate_hubs_exist_and_are_normal():
    world = generate_quiet_world(world_seed=3, n_customers=40, n_merchants=8, sim_days=20)
    hubs = [p for p in world.merchants if p.kind == "hub"]
    assert len(hubs) == 3
    hub_ids = {h.party_id for h in hubs}
    to_hub = [e for e in world.events if e["party_ids"]["payee"] in hub_ids]
    assert to_hub
    assert all(e["label_family"] == "normal" for e in to_hub)


def test_genuine_rows_carry_low_session_stamp_noise():
    """H4 — normal rows must sometimes expose sub-fraud APP-shaped stamps (S2)."""
    world = generate_quiet_world(world_seed=11, n_customers=80, n_merchants=12, sim_days=30)
    normals = [e for e in world.events if e["label_family"] == "normal"]
    assert len(normals) > 100
    with_urgency = sum(
        1 for e in normals if float((e.get("features_auth") or {}).get("urgency_pressure") or 0) > 0.05
    )
    with_copy = sum(
        1 for e in normals if (e.get("features_auth") or {}).get("copy_paste_payee_flag")
    )
    assert with_urgency >= 5, "expected genuine stamp noise on normal urgency_pressure"
    assert with_copy >= 5, "expected genuine stamp noise on normal copy_paste"


def test_new_graph_features_are_h_t_minus():
    t0 = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    fc = FeatureComputer()
    fc.ensure("P1", t0, "dev-1", "tier1", 100_000_000)
    fc.ensure("M1", t0, "dev-m", "tier1", 100_000_000)
    f0 = fc.snapshot_and_apply(ts=t0, payer="P1", payee="M1", amount_minor=100, device_hash="dev-1")
    assert f0["fan_in_1h"] == 0
    assert f0["fan_in_24h"] == 0
    assert f0["hours_since_prev_txn"] == 168.0
    assert f0["hours_since_payee"] == 720.0
    f1 = fc.snapshot_and_apply(
        ts=t0 + timedelta(minutes=5), payer="P1", payee="M1", amount_minor=200, device_hash="dev-1"
    )
    assert f1["fan_in_1h"] == 1
    assert f1["txn_velocity_24h"] == 1
    assert f1["payee_fan_out_1h"] == 0
    assert f1["hours_since_prev_txn"] == pytest.approx(5 / 60, rel=0.2)
    assert f1["hours_since_payee"] == pytest.approx(5 / 60, rel=0.2)
    fc.ensure("M2", t0, "dev-m2", "tier1", 100_000_000)
    f2 = fc.snapshot_and_apply(
        ts=t0 + timedelta(minutes=20), payer="P1", payee="M2", amount_minor=150, device_hash="dev-1"
    )
    assert f2["hours_since_payee"] == 720.0
    assert f2["hours_since_prev_txn"] == pytest.approx(15 / 60, rel=0.2)


def test_events_stay_inside_sim_days():
    rng = np.random.default_rng(11)
    world = generate_quiet_world(world_seed=11, n_customers=32, n_merchants=8, sim_days=30)
    apply_mix(world, rng, target_rate=0.02, pin=True)
    end = world.t0 + timedelta(days=world.sim_days)
    for e in world.events:
        ts = datetime.fromisoformat(e["event_ts"])
        assert world.t0 <= ts < end
