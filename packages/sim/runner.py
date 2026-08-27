"""Population + canary_mode on the real ShadowRail world (Plan 08 Phase E)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from packages.catalog.campaigns import CAMPAIGNS, FINCEN_ALERT004_CAMPAIGN
from packages.catalog.models import AttackSpec
from packages.catalog.query import get_spec_by_vector_id, list_generate_eligible
from packages.sim.export import export_run
from packages.sim.fidelity import evaluate_fidelity
from packages.sim.inject.canary import inject_fincen_chain
from packages.sim.inject.mix import DEFAULT_SIGNALS, apply_mix
from packages.sim.verifier import verify_events
from packages.sim.world import generate_quiet_world

FAST_CUSTOMERS = 20
FAST_MERCHANTS = 8


def _families_for_spec(spec: AttackSpec) -> frozenset[str]:
    inj = spec.simulator.injector_id if spec.simulator else ""
    tid = spec.technique_id.value
    if inj == "app_session":
        return frozenset({"app_fraud"})
    if inj == "graph_mule":
        return frozenset({"mule"})
    if inj == "doc_beneficiary":
        return frozenset({"invoice_fraud"})
    if inj == "identity_trajectory":
        if tid == "T12":
            return frozenset({"ato"})
        return frozenset({"identity_burst"})
    return frozenset()


def _counts(events: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in events:
        out[e["label_family"]] = out.get(e["label_family"], 0) + 1
    return out


def _public_payload(
    *,
    run_id: str,
    mode: str,
    paths: dict[str, str],
    fidelity: dict[str, Any],
    verify: dict[str, Any],
    counts: dict[str, int],
    extra: dict[str, Any],
) -> dict[str, Any]:
    body = {
        "run_id": run_id,
        "mode": mode,
        "parquet_path": paths["parquet_path"],
        "sidecar_path": paths["sidecar_path"],
        "fidelity": {
            "pass": bool(fidelity.get("pass") and verify.get("pass")),
            "psi_amount": fidelity.get("psi_amount"),
            "psi_hour": fidelity.get("psi_hour"),
            "fraud_rate": fidelity.get("fraud_rate"),
            "mule_fan_in_median": fidelity.get("mule_fan_in_median"),
            "reasons": list(fidelity.get("reasons") or []) + list(verify.get("reasons") or []),
        },
        "counts_by_label_family": counts,
        "event_count": sum(counts.values()),
    }
    body.update(extra)
    if "simulatable_signals" in body:
        raise RuntimeError("HTTP/train payload must not include simulatable_signals")
    return body


def run_population(
    db: Session | None = None,
    vector_id: str | None = None,
    run_id: str | None = None,
    *,
    world_seed: int = 42,
    n_customers: int = 800,
    n_merchants: int = 80,
    sim_days: int = 90,
    pin: bool = False,
    runs_dir: Path | None = None,
) -> dict[str, Any]:
    rid = run_id or f"pop-{uuid.uuid4().hex[:12]}"
    families: frozenset[str] | None = None
    spec: AttackSpec | None = None
    if vector_id:
        if db is None:
            raise ValueError("vector_id filter requires catalog db")
        spec = get_spec_by_vector_id(db, vector_id)
        if not spec:
            raise KeyError(f"vector_id not found: {vector_id}")
        if spec.generate_mode.value != "generate":
            raise ValueError(f"{vector_id} is not generate_mode=generate")
        families = _families_for_spec(spec)
    elif db is not None:
        eligible = list_generate_eligible(db, limit=1)
        if not eligible:
            raise ValueError("no generate-eligible atlas rows")

    world = generate_quiet_world(
        world_seed=world_seed,
        n_customers=n_customers,
        n_merchants=n_merchants,
        sim_days=sim_days,
    )
    rng = np.random.default_rng(world_seed + 1)
    mix_signals = dict(DEFAULT_SIGNALS)
    if spec and spec.simulator:
        inj = spec.simulator.injector_id
        blob = dict(spec.simulatable_signals or {})
        if inj == "graph_mule":
            mix_signals["graph_mule"] = blob
        elif inj == "app_session":
            mix_signals["app_session"] = blob
        elif inj == "identity_trajectory" and spec.technique_id.value == "T12":
            mix_signals["ato"] = blob
        elif inj == "identity_trajectory":
            mix_signals["identity_burst"] = blob
    mix = apply_mix(world, rng, pin=pin, families=families, signals=mix_signals)
    verify = verify_events(world.events, world.meta)
    require_rate = families is None
    fidelity = evaluate_fidelity(
        world.events, world.priors, rng=np.random.default_rng(world_seed), require_mix_rate=require_rate
    )
    sidecar = {
        "run_id": rid,
        "mode": "population",
        "world_seed": world_seed,
        "sim_days": sim_days,
        "vector_id": vector_id,
        "technique_id": spec.technique_id.value if spec else None,
        "injector_id": spec.simulator.injector_id if spec and spec.simulator else None,
        "seasoning_clamped": mix["seasoning"]["identity_burst"]["clamped"],
        "seasoning_days_effective": mix["seasoning"]["identity_burst"]["effective_days"],
        "knobs_used": mix["knobs_used"],
        "mix": {k: mix[k] for k in ("n_app", "n_funnel", "ident_burst", "ato_burst") if k in mix},
    }
    paths = export_run(world.events, sidecar, rid, runs_dir=runs_dir)
    extra = {
        "vector_id": vector_id,
        "sim_days": sim_days,
        "world_seed": world_seed,
        "seasoning_clamped": sidecar["seasoning_clamped"],
        "seasoning_days_effective": sidecar["seasoning_days_effective"],
        "injector_id": sidecar["injector_id"],
    }
    return _public_payload(
        run_id=rid,
        mode="population",
        paths=paths,
        fidelity=fidelity,
        verify=verify,
        counts=_counts(world.events),
        extra=extra,
    )


def run_canary(
    db: Session | None = None,
    vector_id: str | None = None,
    campaign_id: str | None = None,
    run_id: str | None = None,
    *,
    world_seed: int = 42,
    n_customers: int = 800,
    n_merchants: int = 80,
    sim_days: int = 180,
    runs_dir: Path | None = None,
) -> dict[str, Any]:
    rid = run_id or f"canary-{uuid.uuid4().hex[:12]}"
    campaign = None
    if campaign_id:
        campaign = CAMPAIGNS.get(campaign_id)
        if not campaign:
            raise KeyError(f"unknown campaign_id: {campaign_id}")
    elif not vector_id:
        campaign = FINCEN_ALERT004_CAMPAIGN

    if campaign is None:
        if db is None or not vector_id:
            raise ValueError("single-vector canary requires db + vector_id")
        spec = get_spec_by_vector_id(db, vector_id)
        if not spec:
            raise KeyError(f"vector_id not found: {vector_id}")
        if not spec.canary_eligible:
            raise ValueError(f"{vector_id} is not canary_eligible")
        # Single-vector canary still needs a world; reuse population filter.
        return run_population(
            db,
            vector_id=vector_id,
            run_id=rid,
            world_seed=world_seed,
            n_customers=n_customers,
            n_merchants=n_merchants,
            sim_days=sim_days,
            pin=True,
            runs_dir=runs_dir,
        )

    signals_by_stage = {
        "t09": {
            **DEFAULT_SIGNALS["identity_burst"],
            "liveness_score": 0.35,
            "doc_consistency": 0.8,
            "kyc_tier": "tier2",
            "seasoning_days": 0,
        },
        "t11": dict(DEFAULT_SIGNALS["identity_burst"]),
        "t13": dict(DEFAULT_SIGNALS["app_session"]),
        "t02": dict(DEFAULT_SIGNALS["graph_mule"]),
    }
    if db is not None:
        for vid, key in (
            ("t09-deepfake-vkyc", "t09"),
            ("t11-identity-farming", "t11"),
            ("t13-upi-impersonation-app", "t13"),
            ("t02-mule-fan-out", "t02"),
        ):
            spec = get_spec_by_vector_id(db, vid)
            if spec and spec.simulatable_signals:
                signals_by_stage[key] = dict(spec.simulatable_signals)

    world = generate_quiet_world(
        world_seed=world_seed,
        n_customers=n_customers,
        n_merchants=n_merchants,
        sim_days=sim_days,
    )
    rng = np.random.default_rng(world_seed + 7)
    chain = inject_fincen_chain(world, rng, signals_by_stage=signals_by_stage)
    verify = verify_events(world.events, world.meta)
    fidelity = evaluate_fidelity(
        world.events, world.priors, rng=np.random.default_rng(world_seed), require_mix_rate=False
    )
    sidecar = {
        "run_id": rid,
        "mode": "canary",
        "campaign_id": campaign.campaign_id,
        "world_seed": world_seed,
        "sim_days": sim_days,
        "chain_id": chain["chain_id"],
        "seasoning_clamped": chain["seasoning_clamped"],
        "seasoning_days_effective": chain["seasoning_days_effective"],
        "pinned_liveness": chain["pinned_liveness"],
        "lifecycle_stages_logged": chain["lifecycle_stages_logged"],
        "knobs_pinned": signals_by_stage,
    }
    paths = export_run(world.events, sidecar, rid, runs_dir=runs_dir)
    extra = {
        "campaign_id": campaign.campaign_id,
        "campaign_name": campaign.name,
        "vector_id": campaign.primary_vector_id,
        "sim_days": sim_days,
        "world_seed": world_seed,
        "chain_id": chain["chain_id"],
        "lifecycle_stages_logged": chain["lifecycle_stages_logged"],
        "seasoning_clamped": chain["seasoning_clamped"],
        "seasoning_days_effective": chain["seasoning_days_effective"],
    }
    return _public_payload(
        run_id=rid,
        mode="canary",
        paths=paths,
        fidelity=fidelity,
        verify=verify,
        counts=_counts(world.events),
        extra=extra,
    )
