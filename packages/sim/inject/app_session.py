"""app_session — mixed variants; flags are noisy, not a family label."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.inject.jitter import clamp_ts
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
        created_ts=clamp_ts(world.t0 + timedelta(days=max(1, after_day - 2)), world.t0, world.sim_days),
        device_hash=f"dev-app-{n:06d}",
        kyc_tier="tier1",
        opening_balance_minor=1_000_000,
    )
    register_party(world, mule)
    eligible = [world.customers[i] for i in rng.permutation(len(world.customers))]
    written: list[dict[str, Any]] = []
    variants = ("classic", "no_flags", "low_amount", "known_hour", "known_payee")
    lo = max(2, min(after_day, world.sim_days - 3))
    hi = max(lo + 1, world.sim_days - 1)
    n_known = max(1, int(round(0.25 * max(3, n_victims))))
    for i, victim in enumerate(eligible[: max(3, n_victims)]):
        variant = variants[i % len(variants)]
        if i < n_known:
            variant = "known_payee"
        day = int(rng.integers(lo, hi))
        hour = 19 if variant == "classic" else int(rng.integers(8, 22))
        ts = clamp_ts(world.t0 + timedelta(days=day, hours=hour, minutes=int(rng.integers(0, 50))), world.t0, world.sim_days)
        acc = world.computer.accounts.get(victim.party_id)
        if acc is not None:
            acc.prune(ts)
            amounts = [a for _, a in acc.amount_history]
        else:
            amounts = []
        p30 = (sum(amounts) / len(amounts)) if amounts else 50_000
        if variant == "classic":
            amount = int(max(p30 * 3.5, 150_000))
            flags = {
                "call_active_flag": bool(signals.get("call_active_flag", True)),
                "copy_paste_payee_flag": bool(signals.get("copy_paste_payee_flag", True)),
                "pause_ms": int(signals.get("pause_ms", 2400)),
                "urgency_pressure": float(signals.get("urgency_pressure", 0.8)),
            }
        elif variant == "no_flags":
            # Adversarial: APP without the SDK stamps the v0 HGB memorized.
            amount = int(max(p30 * 1.15, 40_000))
            flags = {
                "call_active_flag": False,
                "copy_paste_payee_flag": False,
                "pause_ms": 0,
                "urgency_pressure": 0.0,
            }
        elif variant == "low_amount":
            amount = int(max(p30 * 0.9, world.priors.caps.txn_min_minor * 20))
            flags = {
                "call_active_flag": bool(rng.random() < 0.4),
                "copy_paste_payee_flag": True,
                "pause_ms": int(rng.integers(0, 900)),
                "urgency_pressure": float(rng.uniform(0.0, 0.4)),
            }
        elif variant == "known_payee":
            amount = int(max(p30 * 2.2, 90_000))
            flags = {
                "call_active_flag": bool(rng.random() < 0.5),
                "copy_paste_payee_flag": bool(rng.random() < 0.4),
                "pause_ms": int(rng.integers(0, 1200)),
                "urgency_pressure": float(rng.uniform(0.1, 0.5)),
            }
        else:
            amount = int(max(p30 * 2.0, 80_000))
            flags = {
                "call_active_flag": True,
                "copy_paste_payee_flag": bool(rng.random() < 0.5),
                "pause_ms": int(signals.get("pause_ms", 1800)),
                "urgency_pressure": float(signals.get("urgency_pressure", 0.8)),
            }
        amount = min(amount, world.priors.caps.txn_max_minor)
        payee = mule.party_id
        if variant in {"known_hour", "known_payee"} and victim.known_payees:
            merch = [p for p in victim.known_payees if p.startswith("VID-SIM-M-")]
            if merch:
                payee = merch[int(rng.integers(0, len(merch)))]
        ev = append_event(
            world,
            ts=ts,
            payer=victim.party_id,
            payee=payee,
            amount_minor=amount,
            label_family="app_fraud",
            device_hash=victim.device_hash,
            app_flags=flags,
            economic_class="APP",
            payload={"is_authorized_push": True, "app_variant": variant},
        )
        if ev:
            written.append(ev)
    return written
