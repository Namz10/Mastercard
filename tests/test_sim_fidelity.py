"""Phase D — verifier + PSI + fan_in recompute."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from packages.sim.fidelity import (
    FRAUD_RATE_MAX,
    FRAUD_RATE_MIN,
    PSI_AMOUNT_MAX,
    PSI_HOUR_MAX,
    evaluate_fidelity,
    psi,
    psi_amount_normal,
    recompute_fan_in_1h,
)
from packages.sim.inject.mix import apply_mix
from packages.sim.priors import load_priors
from packages.sim.verifier import reject_reason, verify_events
from packages.sim.world import generate_quiet_world


def test_verifier_rejects_non_positive_amount():
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert reject_reason(amount_minor=0, event_ts=t0, payer_created=t0) == "non_positive_amount"
    assert reject_reason(amount_minor=-1, event_ts=t0, payer_created=t0) == "non_positive_amount"
    assert (
        reject_reason(amount_minor=100, event_ts=t0, payer_created=t0.replace(year=2025))
        == "use_before_create"
    )
    assert reject_reason(amount_minor=100, event_ts=t0, payer_created=t0) is None


def test_psi_uniform_fails_amount_gate():
    priors = load_priors()
    rng = np.random.default_rng(0)
    expected = np.array([800.0, 100, 50, 20, 10, 5, 2])
    uniformish = np.ones(7) * (expected.sum() / 7)
    assert psi(expected, uniformish) > PSI_AMOUNT_MAX
    quiet = generate_quiet_world(world_seed=42, n_customers=30, n_merchants=8, sim_days=12)
    val = psi_amount_normal(quiet.events, priors, rng)
    assert val < PSI_AMOUNT_MAX


def test_fidelity_mix_gates(tmp_path=None):
    rng = np.random.default_rng(42)
    world = generate_quiet_world(world_seed=42, n_customers=56, n_merchants=12, sim_days=36)
    apply_mix(world, rng, target_rate=0.02, pin=True)
    fid = evaluate_fidelity(world.events, world.priors, rng=np.random.default_rng(42), require_mix_rate=True)
    assert FRAUD_RATE_MIN <= fid["fraud_rate"] <= FRAUD_RATE_MAX
    assert fid["mule_fan_in_median"] > 5
    assert fid["fan_in_mismatches"] == 0
    assert fid["psi_amount"] < PSI_AMOUNT_MAX
    assert fid["psi_hour"] < PSI_HOUR_MAX
    assert fid["pass"] is True
    assert not fid["reasons"]
    recomputed = recompute_fan_in_1h(world.events)
    for ev in world.events:
        assert ev["features_auth"]["fan_in_1h"] == recomputed[ev["event_id"]]
    v = verify_events(world.events, world.meta)
    assert v["pass"] is True


def test_fan_in_not_catalog_constant():
    rng = np.random.default_rng(42)
    world = generate_quiet_world(world_seed=42, n_customers=40, n_merchants=10, sim_days=30)
    mix = apply_mix(world, rng, pin=True)
    knob = mix["knobs_used"]["graph_mule"]["fan_in_1h"]
    mule = [
        e["features_auth"]["fan_in_1h"]
        for e in world.events
        if e["label_family"] == "mule" and e["party_ids"]["payee"].startswith("VID-SIM-U-")
    ]
    assert mule
    assert not all(v == knob for v in mule)
