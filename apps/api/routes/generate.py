"""Generate API — population + canary_mode handoff from Atlas."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.db import get_db
from packages.catalog.campaigns import CAMPAIGNS
from packages.catalog.query import list_canary_eligible, list_generate_eligible
from packages.sim.calibrator import (
    CalibratorProposal,
    fixture_path,
    hitl_decide,
    list_fixtures,
    propose_from_path,
)
from packages.sim.runner import run_canary, run_population

router = APIRouter(prefix="/generate", tags=["generate"])


class PopulationRunRequest(BaseModel):
    vector_id: str | None = None
    run_id: str | None = None
    world_seed: int = 42
    n_customers: int | None = None
    n_merchants: int | None = None
    sim_days: int | None = None
    pin: bool = False


class CalibrateWorldRequest(BaseModel):
    fixture_id: str = Field(description="In-repo fixture stem or filename; never a live URL")


class CalibrateHitlRequest(BaseModel):
    action: str = Field(description="approve | reject")
    proposal: dict
    apply_to_seed: bool = False


class CanaryRunRequest(BaseModel):
    vector_id: str | None = None
    campaign_id: str | None = Field(
        default="fincen-fin-2024-alert004",
        description="Default FinCEN campaign; omit vector_id to use campaign pin",
    )
    run_id: str | None = None
    world_seed: int = 42
    n_customers: int | None = None
    n_merchants: int | None = None
    sim_days: int | None = None


@router.get("/eligible")
def generate_eligible(db: Annotated[Session, Depends(get_db)]) -> dict:
    specs = list_generate_eligible(db)
    return {
        "count": len(specs),
        "items": [
            {
                "vector_id": s.vector_id,
                "technique_id": s.technique_id.value,
                "name": s.name,
                "status": s.status.value,
                "injector_id": s.simulator.injector_id if s.simulator else None,
                "canary_eligible": s.canary_eligible,
            }
            for s in specs
        ],
    }


@router.get("/canary-eligible")
def canary_eligible(db: Annotated[Session, Depends(get_db)]) -> dict:
    specs = list_canary_eligible(db)
    return {
        "count": len(specs),
        "campaigns": [
            {
                "campaign_id": c.campaign_id,
                "name": c.name,
                "vector_ids": list(c.vector_ids),
                "primary_vector_id": c.primary_vector_id,
            }
            for c in CAMPAIGNS.values()
        ],
        "items": [
            {
                "vector_id": s.vector_id,
                "technique_id": s.technique_id.value,
                "name": s.name,
            }
            for s in specs
        ],
    }


@router.post("/population")
def generate_population(
    body: PopulationRunRequest | None,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    req = body or PopulationRunRequest()
    try:
        kwargs: dict = {
            "vector_id": req.vector_id,
            "run_id": req.run_id,
            "world_seed": req.world_seed,
            "pin": req.pin,
        }
        if req.n_customers is not None:
            kwargs["n_customers"] = req.n_customers
        if req.n_merchants is not None:
            kwargs["n_merchants"] = req.n_merchants
        if req.sim_days is not None:
            kwargs["sim_days"] = req.sim_days
        return run_population(db, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/canary")
def generate_canary(
    body: CanaryRunRequest | None,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    req = body or CanaryRunRequest()
    try:
        kwargs: dict = {
            "vector_id": req.vector_id,
            "campaign_id": req.campaign_id if not req.vector_id else None,
            "run_id": req.run_id,
            "world_seed": req.world_seed,
        }
        if req.n_customers is not None:
            kwargs["n_customers"] = req.n_customers
        if req.n_merchants is not None:
            kwargs["n_merchants"] = req.n_merchants
        if req.sim_days is not None:
            kwargs["sim_days"] = req.sim_days
        return run_canary(db, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/calibrate-world/fixtures")
def calibrate_world_fixtures() -> dict:
    return {"count": len(list_fixtures()), "items": list_fixtures()}


@router.post("/calibrate-world")
def calibrate_world(body: CalibrateWorldRequest) -> dict:
    """Fixture HTML only. No live NPCI/Tavily. Not Identify Job B."""
    try:
        path = fixture_path(body.fixture_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return propose_from_path(path).model_dump()


@router.post("/calibrate-world/hitl")
def calibrate_world_hitl(body: CalibrateHitlRequest) -> dict:
    action = body.action.strip().lower()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="action must be approve or reject")
    try:
        proposal = CalibratorProposal.model_validate(body.proposal)
        dest = None
        if action == "approve" and body.apply_to_seed:
            from packages.sim.priors import DEFAULT_PRIORS_PATH

            dest = DEFAULT_PRIORS_PATH
        result = hitl_decide(action, proposal, dest_path=dest)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    result["apply_to_seed"] = bool(body.apply_to_seed and action == "approve")
    return result
