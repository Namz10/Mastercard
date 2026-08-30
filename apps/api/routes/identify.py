"""Identify / HITL API routes."""

import uuid
from typing import Annotated, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from apps.api.db import get_db, init_db
from apps.api.models import AtlasRow
from packages.agents.identify_graph import run_identify_graph
from packages.agents.librarian_db import hitl_payload_for_spec
from packages.agents.llm import public_llm_status
from packages.agents.settings import get_identify_settings
from packages.catalog.models import AttackSpec
from packages.catalog.status import IllegalStatusTransition, transition_atlas_status
from packages.osint.settings import get_osint_settings
from packages.osint.vector_store import nearest_catalog_row

router = APIRouter(prefix="/identify", tags=["identify"])


class IdentifyRunRequest(BaseModel):
    topic: str = ""
    run_id: str | None = None


class HitlDecision(BaseModel):
    action: str = Field(description="approve | reject | reject_unsafe | edit")
    spec_patch: dict[str, Any] | None = None

class HitlBatchDecision(BaseModel):
    vector_id: str
    action: str = Field(description="approve | reject | reject_unsafe | edit")
    spec_patch: dict[str, Any] | None = None

class HitlBatchRequest(BaseModel):
    decisions: List[HitlBatchDecision]
    action: str = Field(description="approve | reject | reject_unsafe | edit")
    spec_patch: dict[str, Any] | None = None


@router.get("/config")
def identify_config() -> dict:
    """Safe config snapshot — booleans and profile names, never keys."""
    osint = get_osint_settings()
    identify = get_identify_settings()
    llm = public_llm_status()
    return {
        "identify_live_search": osint.identify_live_search,
        "tavily_configured": bool(osint.tavily_api_key),
        "llm": llm,
        "vector_backend": "pgvector",
        "limits": {
            "identify_max_candidates": identify.identify_max_candidates,
            "identify_max_queries": identify.identify_max_queries,
            "identify_tavily_max_results": identify.identify_tavily_max_results,
            "identify_tavily_max_calls_per_run": identify.identify_tavily_max_calls_per_run,
            "identify_max_docs": identify.identify_max_docs,
            "identify_max_hitl": identify.identify_max_hitl,
            "identify_curator_enabled": identify.identify_curator_enabled,
            "identify_curator_batch_size": identify.identify_curator_batch_size,
            "identify_tavily_enabled": identify.identify_tavily_enabled,
            "identify_rss_enabled": identify.identify_rss_enabled,
            "identify_arxiv_api_enabled": identify.identify_arxiv_api_enabled,
            "identify_gnews_enabled": identify.identify_gnews_enabled,
        },
    }


@router.post("/run")
def identify_run(body: IdentifyRunRequest | None = None) -> dict:
    init_db()
    req = body or IdentifyRunRequest()
    run_id = req.run_id or f"identify-{uuid.uuid4().hex[:12]}"
    result = run_identify_graph(run_id=run_id, topic=req.topic)
    candidates = result.get("candidate_urls") or []
    scout_count = result.get("scout_candidate_count")
    curator_kept = result.get("curator_kept_count")
    if scout_count is None:
        scout_count = len(candidates)
    if curator_kept is None:
        curator_kept = len(candidates)
    return {
        "run_id": result.get("run_id", run_id),
        "scout_candidate_count": scout_count,
        "curator_kept_count": curator_kept,
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
    items = []
    for row in rows:
        spec = dict(row.spec or {})
        nearest = nearest_catalog_row(
            str(spec.get("name") or ""),
            str(spec.get("rail") or ""),
            str(spec.get("technique_id") or ""),
        )
        nearest_spec = None
        if nearest:
            nrow = db.query(AtlasRow).filter(AtlasRow.vector_id == nearest["vector_id"]).one_or_none()
            if nrow and nrow.spec:
                nearest_spec = dict(nrow.spec)
        items.append(
            hitl_payload_for_spec(
                spec,
                nearest_technique=str((nearest_spec or spec).get("technique_id", "")),
                nearest_spec=nearest_spec,
            )
        )
    return {
        "count": len(rows),
        "items": items,
    }
@router.get("/state")
def get_identify_state(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return all proposed vectors with their UI actions."""
    rows = (
        db.query(AtlasRow)
        .filter(AtlasRow.status == "proposed")
        .order_by(AtlasRow.updated_at.desc())
        .all()
    )
    items = []
    for row in rows:
        items.append(
            {
                "vector_id": row.vector_id,
                "ui_action": getattr(row, "ui_action", "pending"),
                "spec": dict(row.spec or {}),
            }
        )
    return {"count": len(rows), "items": items}

@router.post("/hitl")
def bulk_hitl_update(request: HitlBatchRequest, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Bulk update UI actions for multiple vectors."""
    updated = 0
    for decision in request.decisions:
        action = decision.action or request.action
        spec_patch = decision.spec_patch or request.spec_patch
        fake_body = HitlDecision(action=action, spec_patch=spec_patch)
        hitl_decision(decision.vector_id, fake_body, db)
        updated += 1
    return {"updated": updated}

@router.patch("/hitl/{vector_id}")
def patch_vector_ui_action(
    vector_id: str, body: HitlDecision, db: Annotated[Session, Depends(get_db)]
) -> dict:
    """Update ui_action for a single vector."""
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="vector_id not found")
    action = body.action.lower().strip()
    if action not in {"approve", "reject", "reject_unsafe", "edit", "pending"}:
        raise HTTPException(status_code=400, detail=f"invalid action: {action}")
    row.ui_action = action
    db.commit()
    db.refresh(row)
    return {"vector_id": vector_id, "ui_action": row.ui_action}


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
