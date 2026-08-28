"""Phase B — quiet world + causal features."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.sim.features import FeatureComputer, featurize_events
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS, VID_PREFIX
from packages.sim.world import generate_quiet_world


def test_quiet_world_all_normal_and_envelope():
    world = generate_quiet_world(world_seed=42, n_customers=24, n_merchants=8, sim_days=10)
    assert len(world.events) >= 50
    for ev in world.events:
        assert ev["schema"] == "gff.txn.v1"
        assert ev["label_family"] == "normal"
        assert ev["label_family"] not in TECHNIQUE_IDS
        assert ev["label_family"] in LABEL_FAMILIES
        assert ev["party_ids"]["payer"].startswith(VID_PREFIX)
        assert ev["party_ids"]["payee"].startswith(VID_PREFIX)
        assert isinstance(ev["amount_minor"], int)
        assert ev["amount_minor"] > 0
        fa = ev["features_auth"]
        assert fa["liveness_score"] is None
        assert fa["doc_consistency"] is None
        assert fa["call_active_flag"] is False


def test_never_pay_before_create():
    world = generate_quiet_world(world_seed=1, n_customers=16, n_merchants=6, sim_days=8)
    created = {p.party_id: p.created_ts for p in world.customers}
    for ev in world.events:
        payer = ev["party_ids"]["payer"]
        ts = datetime.fromisoformat(ev["event_ts"])
        if payer in created:
            assert ts >= created[payer]


def test_causal_payee_history_ignores_future():
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    payer = "VID-SIM-C-000001"
    payee = "VID-SIM-M-000001"
    meta = {
        payer: {
            "created_ts": t0 - timedelta(days=10),
            "device_hash": "dev-a",
            "kyc_tier": "tier2",
            "opening_balance_minor": 50_000_000,
        },
        payee: {
            "created_ts": t0 - timedelta(days=30),
            "device_hash": "dev-m",
            "kyc_tier": "tier2",
            "opening_balance_minor": 50_000_000,
        },
    }
    raw = [
        {
            "event_id": "evt-0000000002",
            "event_ts": (t0 + timedelta(days=2)).isoformat(),
            "party_ids": {"payer": payer, "payee": payee},
            "amount_minor": 5000,
            "label_family": "normal",
            "features_auth": {"device_hash": "dev-a"},
        },
        {
            "event_id": "evt-0000000001",
            "event_ts": t0.isoformat(),
            "party_ids": {"payer": payer, "payee": payee},
            "amount_minor": 2000,
            "label_family": "normal",
            "features_auth": {"device_hash": "dev-a"},
        },
        {
            "event_id": "evt-0000000003",
            "event_ts": (t0 + timedelta(days=5)).isoformat(),
            "party_ids": {"payer": payer, "payee": payee},
            "amount_minor": 8000,
            "label_family": "normal",
            "features_auth": {"device_hash": "dev-a"},
        },
    ]
    out = featurize_events(raw, meta)
    assert out[0]["features_auth"]["is_new_payee"] is True
    assert out[0]["features_auth"]["payee_history_count"] == 0
    assert out[1]["features_auth"]["is_new_payee"] is False
    assert out[1]["features_auth"]["payee_history_count"] == 1
    assert out[2]["features_auth"]["payee_history_count"] == 2


def test_feature_computer_is_linear_not_n_squared():
    world = generate_quiet_world(world_seed=42, n_customers=40, n_merchants=10, sim_days=12)
    n = len(world.events)
    assert n >= 200
    assert world.computer.updates == n
    fc = FeatureComputer()
    assert fc.updates == 0
