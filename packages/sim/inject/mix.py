"""Mix budget — lab oversample 1–3% fraud rows (Plan 08 Phase C)."""

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
from packages.sim.inject.jitter import jitter_signals
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

    mid = world.t0 + timedelta(days=min(7, max(1, world.sim_days // 6)))
    funnel: list = []
    cash: list = []
    smurf: list = []
    hop: list = []
    dust: list = []
    ident = {
        "seasoning_clamped": False,
        "seasoning_days_effective": 0,
        "burst_count": 0,
        "farmed_id": None,
    }
    ato = dict(ident)
    apps: list = []
    inv: list = []

    if "mule" in want:
        funnel_n = min(24, max(16, int(mule_sig.get("fan_in_1h", 18))))
        funnel = inject_funnel(world, rng, n_inbound=funnel_n, window_start=mid, signals=mule_sig)
        mule_id = funnel[-1]["party_ids"]["payee"] if funnel else None
        cash = (
            inject_cashout(
                world,
                rng,
                mule_id=mule_id or funnel[0]["party_ids"]["payee"],
                start=mid + timedelta(hours=1),
                ttl_hours=float(mule_sig.get("fan_out_ttl_hours", 4.0)),
                n_out=2,
            )
            if funnel
            else []
        )
        smurf = inject_smurf(
            world,
            rng,
            n_inbound=3,
            window_start=mid + timedelta(days=1),
            smurf_cap_ratio=float(mule_sig.get("smurf_cap_ratio", 0.85)),
        )
        hop = inject_hop(world, rng, window_start=mid + timedelta(days=2))
        dust = inject_dust(world, rng, n_out=3, window_start=mid + timedelta(days=3))

    if "identity_burst" in want:
        ident = inject_identity(
            world,
            rng,
            signals=id_sig,
            sim_days=world.sim_days,
            burst_family="identity_burst",
            n_burst=max(2, alloc["identity_burst"]),
            pin=pin,
        )
    if "ato" in want:
        ato = inject_identity(
            world,
            rng,
            signals=ato_sig,
            sim_days=world.sim_days,
            burst_family="ato",
            n_burst=max(2, alloc["ato"]),
            pin=pin,
        )
    if "app_fraud" in want:
        after = 30 if world.sim_days > 32 else max(2, world.sim_days // 3)
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
        "n_funnel": len(funnel),
        "n_cashout": len(cash),
        "n_smurf": len(smurf),
        "n_hop": len(hop),
        "n_dust": len(dust),
        "n_app": len(apps),
        "n_invoice": len(inv),
        "ident_burst": ident["burst_count"],
        "ato_burst": ato["burst_count"],
        "farmed_identity": ident["farmed_id"],
        "farmed_ato": ato["farmed_id"],
    }
