"""Identify / HITL API routes."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from apps.api.db import get_db, init_db
from apps.api.models import AtlasRow
from packages.agents.identify_graph import run_identify_graph
from packages.agents.librarian_db import hitl_payload_for_spec
from packages.agents.llm import public_llm_status
from packages.catalog.models import AttackSpec
from packages.catalog.status import IllegalStatusTransition, transition_atlas_status
from packages.osint.settings import get_osint_settings

router = APIRouter(prefix="/identify", tags=["identify"])


class IdentifyRunRequest(BaseModel):
    topic: str = ""
    run_id: str | None = None


class HitlDecision(BaseModel):
    action: str = Field(description="approve | reject | reject_unsafe | edit")
    spec_patch: dict[str, Any] | None = None


@router.get("/config")
def identify_config() -> dict:
    """Safe config snapshot — booleans and profile names, never keys."""
    osint = get_osint_settings()
    llm = public_llm_status()
    return {
        "identify_live_search": osint.identify_live_search,
        "tavily_configured": bool(osint.tavily_api_key),
        "llm": llm,
        "vector_backend": "pgvector",
    }


@router.post("/run")
def identify_run(body: IdentifyRunRequest | None = None) -> dict:
    init_db()
    req = body or IdentifyRunRequest()
    run_id = req.run_id or f"identify-{uuid.uuid4().hex[:12]}"
    result = run_identify_graph(run_id=run_id, topic=req.topic)
    return {
        "run_id": result.get("run_id", run_id),
        "candidate_urls": result.get("candidate_urls", []),
        "extracted_docs": result.get("extracted_docs", []),
        "proposed_count": len(result.get("proposed_specs") or []),
        "proposed_specs": result.get("proposed_specs", []),
        "hitl_required": result.get("hitl_required", False),
        "hitl_queue": result.get("hitl_queue", []),
        "errors": result.get("errors", []),
    }


@router.get("/hitl")
def hitl_queue(db: Annotated[Session, Depends(get_db)]) -> dict:
    rows = (
        db.query(AtlasRow)
        .filter(AtlasRow.status == "proposed")
        .order_by(AtlasRow.updated_at.desc())
        .all()
    )
    return {
        "count": len(rows),
        "items": [hitl_payload_for_spec(row.spec) for row in rows],
    }


def _transition(db: Session, vector_id: str, status: str, patch: dict | None = None) -> dict:
    try:
        row = transition_atlas_status(db, vector_id, status, patch, validate_spec=True)
    except KeyError:
        raise HTTPException(status_code=404, detail="vector_id not found")
    except IllegalStatusTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())
    return {"vector_id": vector_id, "status": row.status}


@router.post("/approve/{vector_id}")
def approve_vector(
    vector_id: str,
    db: Annotated[Session, Depends(get_db)],
    body: HitlDecision | None = None,
) -> dict:
    patch = (body.spec_patch if body else None) or {}
    return _transition(db, vector_id, "open", patch)


@router.post("/reject/{vector_id}")
def reject_vector(vector_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    return _transition(db, vector_id, "rejected")


@router.post("/reject-unsafe/{vector_id}")
def reject_unsafe_vector(vector_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    return _transition(db, vector_id, "rejected_unsafe")


@router.post("/decision/{vector_id}")
def hitl_decision(
    vector_id: str,
    body: HitlDecision,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    action = body.action.lower().strip()
    if action == "approve":
        return approve_vector(vector_id, db, body)
    if action == "reject":
        return reject_vector(vector_id, db)
    if action in {"reject_unsafe", "reject-unsafe"}:
        return reject_unsafe_vector(vector_id, db)
    if action == "edit":
        row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="vector_id not found")
        patch = body.spec_patch or {}
        merged = dict(row.spec or {})
        merged.update(patch)
        try:
            AttackSpec.model_validate(merged)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors())
        return _transition(db, vector_id, row.status, patch)
    raise HTTPException(status_code=400, detail=f"unknown action: {action}")
