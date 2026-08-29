"""Mix budget — lab oversample 1–3% fraud rows. Mule volume follows alloc."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import numpy as np

from packages.sim.inject.app_session import inject_app_sessions
from packages.sim.inject.doc_beneficiary import inject_invoices
from packages.sim.inject.graph_mule import (
    inject_cashout,
    inject_dust,
    inject_funnel,
    inject_hop,
    inject_smurf,
)
from packages.sim.inject.identity import inject_identity
from packages.sim.inject.jitter import clamp_ts, jitter_signals
from packages.sim.world import WorldResult

DEFAULT_SHARES = {
    "mule": 0.40,
    "identity_burst": 0.25,
    "ato": 0.05,
    "app_fraud": 0.20,
    "invoice_fraud": 0.10,
}

DEFAULT_SIGNALS = {
    "graph_mule": {
        "fan_in_1h": 18,
        "fan_out_ttl_hours": 4.0,
        "smurf_cap_ratio": 0.85,
        "mule_account_age_days": 3,
    },
    "identity_burst": {
        "seasoning_days": 150,
        "seasoning_txn_count": 45,
        "liveness_score": 0.9,
        "doc_consistency": 0.88,
        "kyc_tier": "tier2",
    },
    "ato": {
        "seasoning_days": 90,
        "seasoning_txn_count": 20,
        "liveness_score": 0.75,
        "doc_consistency": 0.9,
        "device_hash_shift": True,
        "kyc_tier": "tier2",
    },
    "app_session": {
        "call_active_flag": True,
        "copy_paste_payee_flag": True,
        "pause_ms": 1800,
        "urgency_pressure": 0.85,
        "new_payee": True,
    },
}


def fraud_row_target(n_normal: int, rate: float) -> int:
    rate = min(0.03, max(0.01, rate))
    return max(8, int(round(n_normal * rate / (1.0 - rate))))


def _mule_rows(world: WorldResult) -> int:
    return sum(1 for e in world.events if e["label_family"] == "mule")


def _inject_mule_budget(
    world: WorldResult,
    rng: np.random.Generator,
    n_target: int,
    mule_sig: dict[str, Any],
) -> dict[str, int]:
    """Honor alloc['mule']. Majority funnel_fast keeps fan_in median > 5; harder variants are a minority."""
    n_target = max(8, n_target)
    tallies = {"n_funnel": 0, "n_cashout": 0, "n_smurf": 0, "n_hop": 0, "n_dust": 0}
    lo = 3
    hi = max(lo + 1, world.sim_days - 5)
    camp = 0
    knob_in = int(mule_sig.get("fan_in_1h", 18))

    def _remaining() -> int:
        return n_target - _mule_rows(world)

    def _one(variant: str, n_inbound: int | None = None) -> None:
        nonlocal camp
        day = int(rng.integers(lo, hi))
        start = clamp_ts(
            world.t0 + timedelta(days=day, hours=int(rng.integers(8, 21))),
            world.t0,
            world.sim_days,
        )
        camp_id = f"mule-camp-{camp}"
        sink_idx = 1 + (camp % 3)
        camp += 1
        if variant == "funnel_fast":
            n_in = int(n_inbound if n_inbound is not None else min(24, max(16, knob_in)))
            funnel = inject_funnel(
                world, rng, n_inbound=n_in, window_start=start, signals=mule_sig, span_minutes=40.0
            )
            for ev in funnel:
                ev["campaign_id"] = camp_id
            tallies["n_funnel"] += len(funnel)
            if funnel:
                cash = inject_cashout(
                    world,
                    rng,
                    mule_id=funnel[-1]["party_ids"]["payee"],
                    start=clamp_ts(start + timedelta(hours=1), world.t0, world.sim_days),
                    ttl_hours=float(mule_sig.get("fan_out_ttl_hours", 4.0)),
                    n_out=int(rng.integers(2, 5)),
                    sink_idx=sink_idx,
                )
                tallies["n_cashout"] += len(cash)
        elif variant == "funnel_slow":
            n_in = int(n_inbound if n_inbound is not None else int(rng.integers(8, 14)))
            funnel = inject_funnel(
                world,
                rng,
                n_inbound=n_in,
                window_start=start,
                signals=mule_sig,
                span_minutes=180.0,
            )
            tallies["n_funnel"] += len(funnel)
            if funnel:
                cash = inject_cashout(
                    world,
                    rng,
                    mule_id=funnel[-1]["party_ids"]["payee"],
                    start=clamp_ts(start + timedelta(hours=8), world.t0, world.sim_days),
                    ttl_hours=12.0,
                    n_out=2,
                    sink_idx=sink_idx,
                )
                tallies["n_cashout"] += len(cash)
        elif variant == "smurf":
            smurf = inject_smurf(
                world,
                rng,
                n_inbound=int(n_inbound if n_inbound is not None else rng.integers(6, 9)),
                window_start=start,
                smurf_cap_ratio=float(mule_sig.get("smurf_cap_ratio", 0.85)),
            )
            tallies["n_smurf"] += len(smurf)
        elif variant == "hop":
            hop = inject_hop(world, rng, window_start=start)
            tallies["n_hop"] += len(hop)
        elif variant == "dust":
            dust = inject_dust(
                world,
                rng,
                n_out=int(n_inbound if n_inbound is not None else rng.integers(3, 8)),
                window_start=start,
            )
            tallies["n_dust"] += len(dust)
        else:
            n_in = int(n_inbound if n_inbound is not None else rng.integers(4, 7))
            funnel = inject_funnel(
                world,
                rng,
                n_inbound=n_in,
                window_start=start,
                signals=mule_sig,
                span_minutes=420.0,
            )
            tallies["n_funnel"] += len(funnel)
            if funnel:
                cash = inject_cashout(
                    world,
                    rng,
                    mule_id=funnel[-1]["party_ids"]["payee"],
                    start=clamp_ts(start + timedelta(days=1), world.t0, world.sim_days),
                    ttl_hours=6.0,
                    n_out=2,
                    sink_idx=sink_idx,
                )
                tallies["n_cashout"] += len(cash)

    core_target = max(8, int(round(0.75 * n_target)))
    while _mule_rows(world) < core_target and camp < 120:
        before = _mule_rows(world)
        left = core_target - before
        n_in = min(24, max(16, left) if left >= 16 else max(2, left))
        _one("funnel_fast", n_in)
        if _mule_rows(world) == before:
            break

    # Coverage pass: one of each harder mode so tests/G-dev see variants, but not enough
    # to pull mule_fan_in_median ≤ 5 (those rows are a minority next to funnel_fast).
    if n_target >= 8:
        for variant in ("smurf", "hop", "dust"):
            _one(variant)
    if n_target >= 80:
        for variant in ("funnel_slow", "low_and_slow"):
            _one(variant)

    while _remaining() > 0 and camp < 200:
        before = _mule_rows(world)
        left = _remaining()
        n_in = min(24, max(16, left) if left >= 16 else max(2, left))
        _one("funnel_fast", n_in)
        if _mule_rows(world) == before:
            break
    return tallies


def _inject_identity_budget(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    family: str,
    n_target: int,
    signals: dict[str, Any],
    pin: bool,
) -> dict[str, Any]:
    n_target = max(2, n_target)
    variants = ("burst", "low_and_slow", "delayed_high", "partial", "multi_merchant")
    n_farms = max(1, min(8, (n_target + 5) // 6))
    per = max(2, n_target // n_farms)
    early_cut = int(0.55 * world.sim_days)
    n_early = max(1, int(round(0.6 * n_farms))) if family == "ato" else 0
    last: dict[str, Any] = {
        "seasoning_clamped": False,
        "seasoning_days_effective": 0,
        "burst_count": 0,
        "farmed_id": None,
    }
    total_burst = 0
    span_lo = 4
    span_hi = max(span_lo + 1, world.sim_days - 3)
    hi_create = max(2, min(world.sim_days // 5, world.sim_days - 16))
    for i in range(n_farms):
        if family == "ato" and i < n_early:
            burst_day = int(rng.integers(14, max(15, early_cut)))
        else:
            burst_day = int(span_lo + (span_hi - span_lo) * (i + 0.5) / n_farms)
        created_day = max(1, min(hi_create, burst_day - 4))
        last = inject_identity(
            world,
            rng,
            signals=signals,
            sim_days=world.sim_days,
            burst_family=family,
            n_burst=per if i < n_farms - 1 else max(2, n_target - total_burst),
            pin=pin,
            created_day=created_day,
            burst_day=burst_day,
            variant=variants[i % len(variants)] if family == "ato" else variants[i % 2],
        )
        total_burst += int(last.get("burst_count") or 0)
        if total_burst >= n_target:
            break
    last["burst_count"] = total_burst
    return last


def apply_mix(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    target_rate: float = 0.02,
    pin: bool = False,
    signals: dict[str, dict[str, Any]] | None = None,
    families: frozenset[str] | None = None,
) -> dict[str, Any]:
    n_normal = sum(1 for e in world.events if e["label_family"] == "normal")
    n_fraud = fraud_row_target(n_normal, target_rate)
    shares = DEFAULT_SHARES
    alloc = {k: max(1, int(round(n_fraud * v))) for k, v in shares.items()}
    while sum(alloc.values()) > n_fraud + 4:
        key = max(alloc, key=alloc.get)
        if alloc[key] > 1:
            alloc[key] -= 1
        else:
            break

    want = families or frozenset(shares)
    sigs = signals or DEFAULT_SIGNALS
    mule_sig = jitter_signals(rng, dict(sigs.get("graph_mule", DEFAULT_SIGNALS["graph_mule"])), pin)
    id_sig = jitter_signals(rng, dict(sigs.get("identity_burst", DEFAULT_SIGNALS["identity_burst"])), pin)
    ato_sig = jitter_signals(rng, dict(sigs.get("ato", DEFAULT_SIGNALS["ato"])), pin)
    app_sig = jitter_signals(rng, dict(sigs.get("app_session", DEFAULT_SIGNALS["app_session"])), pin)

    ident = {
        "seasoning_clamped": False,
        "seasoning_days_effective": 0,
        "burst_count": 0,
        "farmed_id": None,
    }
    ato = dict(ident)
    apps: list = []
    inv: list = []
    mule_tally = {"n_funnel": 0, "n_cashout": 0, "n_smurf": 0, "n_hop": 0, "n_dust": 0}

    if "mule" in want:
        mule_tally = _inject_mule_budget(world, rng, alloc["mule"], mule_sig)
    if "identity_burst" in want:
        ident = _inject_identity_budget(
            world, rng, family="identity_burst", n_target=alloc["identity_burst"], signals=id_sig, pin=pin
        )
    if "ato" in want:
        ato = _inject_identity_budget(
            world, rng, family="ato", n_target=max(2, alloc["ato"]), signals=ato_sig, pin=pin
        )
    if "app_fraud" in want:
        after = 12 if world.sim_days > 20 else max(2, world.sim_days // 3)
        apps = inject_app_sessions(
            world,
            rng,
            n_victims=max(3, alloc["app_fraud"]),
            signals=app_sig,
            after_day=after,
        )
    if "invoice_fraud" in want:
        inv = inject_invoices(world, rng, n_invoices=max(1, alloc["invoice_fraud"]))

    world.rebuild_features()
    counts: dict[str, int] = {}
    for e in world.events:
        counts[e["label_family"]] = counts.get(e["label_family"], 0) + 1
    n = len(world.events)
    fraud = n - counts.get("normal", 0)
    rate = fraud / n if n else 0.0
    return {
        "counts": counts,
        "fraud_rate": rate,
        "alloc": alloc,
        "seasoning": {
            "identity_burst": {
                "clamped": ident["seasoning_clamped"],
                "effective_days": ident["seasoning_days_effective"],
            },
            "ato": {
                "clamped": ato["seasoning_clamped"],
                "effective_days": ato["seasoning_days_effective"],
            },
        },
        "knobs_used": {
            "graph_mule": mule_sig,
            "identity_burst": id_sig,
            "ato": ato_sig,
            "app_session": app_sig,
        },
        "n_funnel": mule_tally["n_funnel"],
        "n_cashout": mule_tally["n_cashout"],
        "n_smurf": mule_tally["n_smurf"],
        "n_hop": mule_tally["n_hop"],
        "n_dust": mule_tally["n_dust"],
        "n_app": len(apps),
        "n_invoice": len(inv),
        "ident_burst": ident["burst_count"],
        "ato_burst": ato["burst_count"],
        "farmed_identity": ident["farmed_id"],
        "farmed_ato": ato["farmed_id"],
    }
