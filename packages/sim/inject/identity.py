"""identity_trajectory — T11 identity_burst vs T12 ato. Multiple farms, real seasoning."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.inject.jitter import clamp_seasoning, clamp_ts
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
    created_day: int | None = None,
    burst_day: int | None = None,
    variant: str = "burst",
) -> dict[str, Any]:
    _, clamped = clamp_seasoning(int(signals.get("seasoning_days", 30)), sim_days)
    hi_create = max(2, min(sim_days // 5, sim_days - 16))
    created_off = int(created_day) if created_day is not None else int(rng.integers(1, hi_create + 1))
    created = clamp_ts(world.t0 + timedelta(days=created_off), world.t0, sim_days)
    n = 1 + sum(1 for p in world.meta if p.startswith("VID-SIM-F-"))
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
        ts=clamp_ts(created + timedelta(minutes=5), world.t0, sim_days),
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
    # Honor seasoning_txn_count: quiet legitimate-looking payments before the burst.
    quiet_n = max(0, int(signals.get("seasoning_txn_count", 0)))
    if variant == "low_and_slow":
        quiet_n = max(quiet_n, 8)
    merch_pool = world.merchants
    lo_burst = created_off + 3
    hi_burst = max(lo_burst + 1, sim_days - 3)
    bday = int(burst_day) if burst_day is not None else int(rng.integers(lo_burst, hi_burst))
    bday = min(max(bday, lo_burst), sim_days - 2)
    burst_start = clamp_ts(world.t0 + timedelta(days=bday, hours=int(rng.integers(9, 21))), world.t0, sim_days)
    quiet_span_days = max(1.0, (burst_start - created).total_seconds() / 86400.0 - 0.5)
    for j in range(quiet_n):
        frac = (j + 1) / (quiet_n + 1)
        ts = clamp_ts(
            created + timedelta(days=frac * quiet_span_days, hours=int(rng.integers(10, 20))),
            world.t0,
            sim_days,
        )
        if ts >= burst_start:
            ts = clamp_ts(burst_start - timedelta(hours=2, minutes=j), world.t0, sim_days)
        merch = merch_pool[int(rng.integers(0, len(merch_pool)))]
        append_event(
            world,
            ts=ts,
            payer=farmed.party_id,
            payee=merch.party_id,
            amount_minor=int(rng.integers(8_000, 80_000)),
            label_family="normal",
            device_hash=farmed.device_hash,
            debit=True,
        )
    written = [onboard] if onboard else []
    n_pay = max(2, n_burst)
    merch = merch_pool[int(rng.integers(0, len(merch_pool)))]
    for i in range(n_pay):
        if variant == "low_and_slow":
            ts = burst_start + timedelta(hours=i * 6)
            amount = int(rng.integers(20_000, 90_000))
        elif variant == "delayed_high" and i == n_pay - 1:
            ts = burst_start + timedelta(days=min(2, max(0, sim_days - bday - 1)), hours=3)
            amount = int(rng.integers(250_000, 800_000))
        else:
            ts = burst_start + timedelta(minutes=i * (8 if variant == "burst" else 25))
            amount = int(rng.integers(80_000, 400_000))
        ts = clamp_ts(ts, world.t0, sim_days)
        device = farmed.device_hash
        if burst_family == "ato":
            # Partial takeover: recon on old device, then some (not all) burst on a new device.
            recon = variant in {"delayed_high", "partial"} and i < max(1, n_pay // 3)
            if not recon and (bool(signals.get("device_hash_shift", True)) and rng.random() < 0.55):
                device = f"dev-f-new-{n:06d}"
        ev = append_event(
            world,
            ts=ts,
            payer=farmed.party_id,
            payee=merch.party_id if variant != "multi_merchant" else merch_pool[i % len(merch_pool)].party_id,
            amount_minor=min(amount, world.priors.caps.txn_max_minor),
            label_family=burst_family,
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
        "seasoning_days_effective": max(1, bday - created_off),
        "seasoning_txn_count_catalog": int(signals.get("seasoning_txn_count", 0)),
        "seasoning_txn_count_actual": max(0, len(quiet) - 1),
        "burst_count": sum(1 for e in written if e and e["label_family"] == burst_family),
        "farmed_id": farmed.party_id,
        "pin": pin,
        "events": [e for e in written if e],
        "variant": variant,
    }
