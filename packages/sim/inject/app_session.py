"""app_session — many victims, flags only on APP rows."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.ledger import party_id
from packages.sim.world import Party, WorldResult, append_event, register_party


def inject_app_sessions(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    n_victims: int,
    signals: dict[str, Any],
    after_day: int = 30,
) -> list[dict[str, Any]]:
    n = 1 + sum(1 for p in world.meta if p.startswith("VID-SIM-APP-"))
    mule = Party(
        party_id=party_id("APP", n),
        kind="mule",
        persona=None,
        created_ts=world.t0 + timedelta(days=after_day - 2),
        device_hash=f"dev-app-{n:06d}",
        kyc_tier="tier1",
        opening_balance_minor=1_000_000,
    )
    register_party(world, mule)
    eligible = [world.customers[i] for i in rng.permutation(len(world.customers))]
    start = world.t0 + timedelta(days=after_day, hours=19)
    flags = {
        "call_active_flag": bool(signals.get("call_active_flag", True)),
        "copy_paste_payee_flag": bool(signals.get("copy_paste_payee_flag", True)),
        "pause_ms": int(signals.get("pause_ms", 2400)),
        "urgency_pressure": float(signals.get("urgency_pressure", 0.8)),
    }
    written: list[dict[str, Any]] = []
    for i, victim in enumerate(eligible[: max(3, n_victims)]):
        hist = [
            e["amount_minor"]
            for e in world.events
            if e["party_ids"]["payer"] == victim.party_id and e["label_family"] == "normal"
        ]
        p30 = (sum(hist[-12:]) / max(len(hist[-12:]), 1)) if hist else 50_000
        amount = int(max(p30 * 3.5, 150_000))
        amount = min(amount, world.priors.caps.txn_max_minor)
        ts = start + timedelta(hours=i)
        ev = append_event(
            world,
            ts=ts,
            payer=victim.party_id,
            payee=mule.party_id,
            amount_minor=amount,
            label_family="app_fraud",
            device_hash=victim.device_hash,
            app_flags=flags,
            economic_class="APP",
            payload={"is_authorized_push": True},
        )
        if ev:
            written.append(ev)
    return written
