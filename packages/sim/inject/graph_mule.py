"""graph_mule modes T01–T05 — compute fan_in from edges, never copy YAML."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.ledger import party_id
from packages.sim.world import Party, WorldResult, append_event, register_party


def _new_mule(world: WorldResult, rng: np.random.Generator, created_ts, age_days: int) -> Party:
    n = 1 + sum(1 for p in world.meta if p.startswith("VID-SIM-U-"))
    mule = Party(
        party_id=party_id("U", n),
        kind="mule",
        persona=None,
        created_ts=created_ts,
        device_hash=f"dev-u-{n:06d}",
        kyc_tier="tier1",
        opening_balance_minor=5_000_000,
    )
    register_party(world, mule)
    _ = rng
    _ = age_days
    return mule


def _ensure_sink(world: WorldResult) -> Party:
    pid = party_id("SINK", 1)
    if pid in world.meta:
        m = world.meta[pid]
        return Party(
            party_id=pid,
            kind="sink",
            persona=None,
            created_ts=m["created_ts"],
            device_hash=m["device_hash"],
            kyc_tier=m["kyc_tier"],
            opening_balance_minor=m["opening_balance_minor"],
            category="crypto_offramp",
        )
    sink = Party(
        party_id=pid,
        kind="sink",
        persona=None,
        created_ts=world.t0,
        device_hash="dev-sink-000001",
        kyc_tier="tier2",
        opening_balance_minor=100_000_000,
        category="crypto_offramp",
    )
    register_party(world, sink)
    return sink


def inject_funnel(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    n_inbound: int,
    window_start,
    signals: dict[str, Any],
) -> list[dict[str, Any]]:
    n_inbound = max(16, n_inbound)
    mule = _new_mule(world, rng, window_start - timedelta(days=3), int(signals.get("mule_account_age_days", 3)))
    senders = [world.customers[i] for i in rng.permutation(len(world.customers))]
    written: list[dict[str, Any]] = []
    span_min = 40.0
    for i in range(n_inbound):
        sender = senders[i % len(senders)]
        ts = window_start + timedelta(minutes=span_min * i / max(n_inbound - 1, 1))
        amount = int(world.priors.caps.txn_min_minor * 8 + rng.integers(500, 20_000))
        ev = append_event(
            world,
            ts=ts,
            payer=sender.party_id,
            payee=mule.party_id,
            amount_minor=amount,
            label_family="mule",
            economic_class="mule",
        )
        if ev:
            written.append(ev)
    return written


def inject_cashout(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    mule_id: str,
    start,
    ttl_hours: float,
    n_out: int = 4,
) -> list[dict[str, Any]]:
    sink = _ensure_sink(world)
    written: list[dict[str, Any]] = []
    mule_acc = world.computer.accounts[mule_id]
    chunk = max(world.priors.caps.txn_min_minor, mule_acc.balance_minor // max(n_out, 1))
    for i in range(n_out):
        ts = start + timedelta(hours=float(ttl_hours) * (i + 1) / n_out)
        amount = min(chunk, mule_acc.balance_minor)
        if amount <= 0:
            break
        ev = append_event(
            world,
            ts=ts,
            payer=mule_id,
            payee=sink.party_id,
            amount_minor=amount,
            label_family="mule",
            economic_class="mule",
            payload={"cashout_mcc_or_sink": "crypto_offramp"},
        )
        if ev:
            written.append(ev)
    _ = rng
    return written


def inject_smurf(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    n_inbound: int,
    window_start,
    smurf_cap_ratio: float,
) -> list[dict[str, Any]]:
    mule = _new_mule(world, rng, window_start - timedelta(days=10), 30)
    cap = int(world.priors.caps.txn_max_minor * min(1.0, max(0.01, smurf_cap_ratio)))
    senders = world.customers
    written: list[dict[str, Any]] = []
    for i in range(max(3, n_inbound)):
        sender = senders[i % len(senders)]
        ts = window_start + timedelta(minutes=i * 4)
        ev = append_event(
            world,
            ts=ts,
            payer=sender.party_id,
            payee=mule.party_id,
            amount_minor=cap,
            label_family="mule",
            economic_class="mule",
            payload={"smurf_cap_ratio": smurf_cap_ratio},
        )
        if ev:
            written.append(ev)
    return written


def inject_hop(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    window_start,
) -> list[dict[str, Any]]:
    mule = _new_mule(world, rng, window_start - timedelta(days=5), 45)
    hop = _new_mule(world, rng, window_start - timedelta(days=5), 45)
    sender = world.customers[int(rng.integers(0, len(world.customers)))]
    a1 = int(rng.integers(50_000, 200_000))
    e1 = append_event(
        world,
        ts=window_start,
        payer=sender.party_id,
        payee=mule.party_id,
        amount_minor=a1,
        label_family="mule",
        rail="upi_like",
        economic_class="mule",
    )
    e2 = append_event(
        world,
        ts=window_start + timedelta(minutes=20),
        payer=mule.party_id,
        payee=hop.party_id,
        amount_minor=min(a1, world.computer.accounts[mule.party_id].balance_minor),
        label_family="mule",
        rail="imps",
        economic_class="mule",
        payload={"hop_rails": ["upi_like", "imps"]},
    )
    return [e for e in (e1, e2) if e]


def inject_dust(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    n_out: int,
    window_start,
    mule_id: str | None = None,
) -> list[dict[str, Any]]:
    if mule_id is None:
        mule = _new_mule(world, rng, window_start - timedelta(days=20), 60)
        # fund mule first
        funder = world.customers[0]
        append_event(
            world,
            ts=window_start,
            payer=funder.party_id,
            payee=mule.party_id,
            amount_minor=min(2_000_000, world.computer.accounts[funder.party_id].balance_minor // 8),
            label_family="mule",
            economic_class="mule",
        )
        mule_id = mule.party_id
    dust = world.priors.caps.txn_min_minor
    written: list[dict[str, Any]] = []
    for i in range(max(3, n_out)):
        payee = world.customers[i % len(world.customers)].party_id
        ev = append_event(
            world,
            ts=window_start + timedelta(minutes=i),
            payer=mule_id,
            payee=payee,
            amount_minor=dust,
            label_family="mule",
            economic_class="mule",
        )
        if ev:
            written.append(ev)
    return written
