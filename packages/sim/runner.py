"""Generate modes: population sample vs canary_mode campaign pin."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from packages.catalog.campaigns import CAMPAIGNS, FINCEN_ALERT004_CAMPAIGN, CanaryCampaign
from packages.catalog.models import AttackSpec
from packages.catalog.query import get_spec_by_vector_id, list_generate_eligible
from packages.sim.injectors import run_injector


def run_population(
    db: Session,
    vector_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    Population mode: one open/generating row drives one injector run.
    If vector_id omitted, uses first eligible row.
    """
    rid = run_id or f"pop-{uuid.uuid4().hex[:12]}"
    if vector_id:
        spec = get_spec_by_vector_id(db, vector_id)
        if not spec:
            raise KeyError(f"vector_id not found: {vector_id}")
        if spec.generate_mode.value != "generate":
            raise ValueError(f"{vector_id} is not generate_mode=generate")
    else:
        eligible = list_generate_eligible(db, limit=1)
        if not eligible:
            raise ValueError("no generate-eligible atlas rows")
        spec = eligible[0]

    injection = run_injector(spec)
    return {
        "run_id": rid,
        "mode": "population",
        "vector_id": spec.vector_id,
        "technique_id": spec.technique_id.value,
        "injector_id": spec.simulator.injector_id if spec.simulator else None,
        "simulatable_signals": spec.simulatable_signals,
        "injections": [injection],
        "event_count": 1,
    }


def run_canary(
    db: Session,
    vector_id: str | None = None,
    campaign_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """
    canary_mode: pin all attack parameters to one canary_eligible row or
    FinCEN FIN-2024-Alert004 campaign (T09 → T11 → T13 → T02).
    """
    rid = run_id or f"canary-{uuid.uuid4().hex[:12]}"
    campaign: CanaryCampaign | None = None

    if campaign_id:
        campaign = CAMPAIGNS.get(campaign_id)
        if not campaign:
            raise KeyError(f"unknown campaign_id: {campaign_id}")
    elif not vector_id:
        campaign = FINCEN_ALERT004_CAMPAIGN

    injections: list[dict[str, Any]] = []
    stages_logged: list[dict[str, Any]] = []

    if campaign:
        for vid, stage in zip(campaign.vector_ids, campaign.lifecycle_stages, strict=True):
            spec = get_spec_by_vector_id(db, vid)
            if not spec:
                raise KeyError(f"campaign vector missing from atlas: {vid}")
            if not spec.canary_eligible and vid != campaign.primary_vector_id:
                # Allow chain stages that are open but not individually canary-flagged
                pass
            inj = run_injector(spec, lifecycle_stage=stage)
            injections.append(inj)
            stages_logged.append(
                {
                    "vector_id": vid,
                    "technique_id": spec.technique_id.value,
                    "lifecycle_stage": stage,
                    "injector_id": spec.simulator.injector_id if spec.simulator else None,
                }
            )
        primary = get_spec_by_vector_id(db, campaign.primary_vector_id)
        return {
            "run_id": rid,
            "mode": "canary",
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.name,
            "vector_id": campaign.primary_vector_id,
            "technique_id": primary.technique_id.value if primary else None,
            "injector_id": primary.simulator.injector_id if primary and primary.simulator else None,
            "simulatable_signals": primary.simulatable_signals if primary else {},
            "injections": injections,
            "lifecycle_stages_logged": stages_logged,
            "event_count": len(injections),
        }

    spec = get_spec_by_vector_id(db, vector_id or "")
    if not spec:
        raise KeyError(f"vector_id not found: {vector_id}")
    if not spec.canary_eligible:
        raise ValueError(f"{vector_id} is not canary_eligible")

    inj = run_injector(spec)
    injections.append(inj)
    stages_logged.append(
        {
            "vector_id": spec.vector_id,
            "technique_id": spec.technique_id.value,
            "lifecycle_stage": spec.lifecycle_stage.value,
            "injector_id": spec.simulator.injector_id if spec.simulator else None,
        }
    )
    return {
        "run_id": rid,
        "mode": "canary",
        "vector_id": spec.vector_id,
        "technique_id": spec.technique_id.value,
        "injector_id": spec.simulator.injector_id if spec.simulator else None,
        "simulatable_signals": spec.simulatable_signals,
        "injections": injections,
        "lifecycle_stages_logged": stages_logged,
        "event_count": 1,
    }
