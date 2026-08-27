"""Generate API — population + canary_mode handoff from Atlas."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.db import get_db
from packages.catalog.campaigns import CAMPAIGNS
from packages.catalog.query import list_canary_eligible, list_generate_eligible
from packages.sim.runner import run_canary, run_population

router = APIRouter(prefix="/generate", tags=["generate"])


class PopulationRunRequest(BaseModel):
    vector_id: str | None = None
    run_id: str | None = None


class CanaryRunRequest(BaseModel):
    vector_id: str | None = None
    campaign_id: str | None = Field(
        default="fincen-fin-2024-alert004",
        description="Default FinCEN campaign; omit vector_id to use campaign pin",
    )
    run_id: str | None = None


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
        return run_population(db, vector_id=req.vector_id, run_id=req.run_id)
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
        return run_canary(
            db,
            vector_id=req.vector_id,
            campaign_id=req.campaign_id if not req.vector_id else None,
            run_id=req.run_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
