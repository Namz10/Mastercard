"""FinCEN canary: T09 → T11 → T13 → T02 on one shared VID-SIM chain account."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.inject.graph_mule import inject_cashout
from packages.sim.inject.identity import _kyc_vendor
from packages.sim.inject.jitter import clamp_seasoning
from packages.sim.ledger import party_id
from packages.sim.world import Party, WorldResult, append_event, register_party


def inject_fincen_chain(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    signals_by_stage: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Pin catalog knobs. Shared farmed/mule party for all four stages."""
    t09 = signals_by_stage["t09"]
    t11 = signals_by_stage["t11"]
    t13 = signals_by_stage["t13"]
    t02 = signals_by_stage["t02"]
    seasoning, clamped = clamp_seasoning(int(t11.get("seasoning_days", 150)), world.sim_days)
    created = world.t0 + timedelta(days=1)
    chain = Party(
        party_id=party_id("CHAIN", 1),
        kind="farmed",
        persona="young_urban",
        created_ts=created,
        device_hash="dev-chain-000001",
        kyc_tier=str(t09.get("kyc_tier", "tier2")),
        opening_balance_minor=40_000_000,
    )
    register_party(world, chain)
    kyc = _kyc_vendor(world)
    stages: list[dict[str, Any]] = []

    e09 = append_event(
        world,
        ts=created + timedelta(minutes=5),
        payer=chain.party_id,
        payee=kyc,
        amount_minor=world.priors.caps.txn_min_minor,
        label_family="normal",
        rail="onboarding",
        liveness_score=float(t09["liveness_score"]),
        doc_consistency=float(t09.get("doc_consistency", 0.8)),
        economic_class="ATO",
    )
    stages.append(
        {
            "vector_id": "t09-deepfake-vkyc",
            "technique_id": "T09",
            "lifecycle_stage": "onboarding_kyc",
            "event_id": e09["event_id"] if e09 else None,
            "party_id": chain.party_id,
        }
    )

    merch = world.merchants[0]
    n_quiet = 4
    for i in range(n_quiet):
        append_event(
            world,
            ts=created + timedelta(days=max(2, seasoning * (i + 1) // (n_quiet + 1))),
            payer=chain.party_id,
            payee=merch.party_id,
            amount_minor=int(rng.integers(8_000, 40_000)),
            label_family="normal",
            economic_class=None,
        )
    stages.append(
        {
            "vector_id": "t11-identity-farming",
            "technique_id": "T11",
            "lifecycle_stage": "account_access_ato",
            "event_id": None,
            "party_id": chain.party_id,
            "seasoning_days_effective": seasoning,
            "seasoning_clamped": clamped,
        }
    )

    victim = world.customers[int(rng.integers(0, len(world.customers)))]
    app_ts = created + timedelta(days=seasoning + 2, hours=19)
    flags = {
        "call_active_flag": bool(t13.get("call_active_flag", True)),
        "copy_paste_payee_flag": bool(t13.get("copy_paste_payee_flag", True)),
        "pause_ms": int(t13.get("pause_ms", 1800)),
        "urgency_pressure": float(t13.get("urgency_pressure", 0.8)),
    }
    hist = [
        e["amount_minor"]
        for e in world.events
        if e["party_ids"]["payer"] == victim.party_id and e["label_family"] == "normal"
    ]
    p30 = (sum(hist[-8:]) / max(len(hist[-8:]), 1)) if hist else 50_000
    app_amt = int(max(p30 * 4, 200_000))
    e13 = append_event(
        world,
        ts=app_ts,
        payer=victim.party_id,
        payee=chain.party_id,
        amount_minor=min(app_amt, world.priors.caps.txn_max_minor),
        label_family="app_fraud",
        device_hash=victim.device_hash,
        app_flags=flags,
        economic_class="APP",
        payload={"is_authorized_push": True},
    )
    stages.append(
        {
            "vector_id": "t13-upi-impersonation-app",
            "technique_id": "T13",
            "lifecycle_stage": "payment_initiation",
            "event_id": e13["event_id"] if e13 else None,
            "party_id": chain.party_id,
            "victim_id": victim.party_id,
        }
    )

    ttl = float(t02.get("fan_out_ttl_hours", 1.5))
    cash = inject_cashout(
        world,
        rng,
        mule_id=chain.party_id,
        start=app_ts + timedelta(hours=ttl),
        ttl_hours=ttl,
        n_out=3,
    )
    stages.append(
        {
            "vector_id": "t02-mule-fan-out",
            "technique_id": "T02",
            "lifecycle_stage": "disbursement_mule",
            "event_id": cash[0]["event_id"] if cash else None,
            "party_id": chain.party_id,
        }
    )
    _ = rng
    world.rebuild_features()
    return {
        "chain_id": chain.party_id,
        "seasoning_clamped": clamped,
        "seasoning_days_effective": seasoning,
        "lifecycle_stages_logged": stages,
        "pinned_liveness": float(t09["liveness_score"]),
        "n_cashout": len(cash),
    }
