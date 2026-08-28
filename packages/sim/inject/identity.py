"""identity_trajectory — T11 identity_burst vs T12 ato."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.inject.jitter import clamp_seasoning
from packages.sim.ledger import party_id
from packages.sim.world import Party, WorldResult, append_event, register_party


def _kyc_vendor(world: WorldResult) -> str:
    pid = party_id("KYC", 1)
    if pid not in world.meta:
        register_party(
            world,
            Party(
                party_id=pid,
                kind="kyc",
                persona=None,
                created_ts=world.t0,
                device_hash="dev-kyc-000001",
                kyc_tier="tier2",
                opening_balance_minor=10_000_000,
            ),
        )
    return pid


def inject_identity(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    signals: dict[str, Any],
    sim_days: int,
    burst_family: str,
    n_burst: int,
    pin: bool,
) -> dict[str, Any]:
    seasoning, clamped = clamp_seasoning(int(signals.get("seasoning_days", 30)), sim_days)
    n = 1 + sum(1 for p in world.meta if p.startswith("VID-SIM-F-"))
    created = world.t0 + timedelta(days=1)
    farmed = Party(
        party_id=party_id("F", n),
        kind="farmed",
        persona="young_urban",
        created_ts=created,
        device_hash=f"dev-f-{n:06d}",
        kyc_tier=str(signals.get("kyc_tier", "tier1")),
        opening_balance_minor=25_000_000,
    )
    register_party(world, farmed)
    kyc = _kyc_vendor(world)
    onboard = append_event(
        world,
        ts=created + timedelta(minutes=5),
        payer=farmed.party_id,
        payee=kyc,
        amount_minor=world.priors.caps.txn_min_minor,
        label_family="normal",
        rail="onboarding",
        liveness_score=float(signals.get("liveness_score", 0.4)),
        doc_consistency=float(signals.get("doc_consistency", 0.7)),
        economic_class="ATO",
        debit=True,
    )
    burst_start = created + timedelta(days=seasoning)
    device = farmed.device_hash
    if burst_family == "ato":
        device = f"dev-f-new-{n:06d}"
    written = [onboard] if onboard else []
    merch = world.merchants[int(rng.integers(0, len(world.merchants)))]
    for i in range(max(2, n_burst)):
        ts = burst_start + timedelta(minutes=i * 8)
        ev = append_event(
            world,
            ts=ts,
            payer=farmed.party_id,
            payee=merch.party_id,
            amount_minor=int(rng.integers(80_000, 400_000)),
            label_family=burst_family,  # identity_burst | ato
            device_hash=device,
            economic_class="ATO",
        )
        if ev:
            written.append(ev)
    quiet = [
        e
        for e in world.events
        if e["party_ids"]["payer"] == farmed.party_id and e["label_family"] == "normal"
    ]
    return {
        "seasoning_clamped": clamped,
        "seasoning_days_effective": seasoning,
        "seasoning_txn_count_catalog": int(signals.get("seasoning_txn_count", 0)),
        "seasoning_txn_count_actual": max(0, len(quiet) - 1),
        "burst_count": sum(1 for e in written if e and e["label_family"] == burst_family),
        "farmed_id": farmed.party_id,
        "pin": pin,
        "events": [e for e in written if e],
    }
