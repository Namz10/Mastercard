"""Identify / HITL API routes."""

import os

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import AtlasRow
from packages.agents.identify_graph import run_identify_graph
from packages.agents.librarian_db import hitl_payload_for_spec, merge_proposed_spec, set_atlas_status

router = APIRouter(prefix="/identify", tags=["identify"])


class IdentifyRunRequest(BaseModel):
    topic: str = ""
    run_id: str | None = None


class HitlDecision(BaseModel):
    action: str = Field(description="approve | reject | reject_unsafe | edit")
    spec_patch: dict[str, Any] | None = None


@router.get("/config")
def identify_config() -> dict:
    """Which keys are configured (booleans only — for local debugging)."""
    from apps.api.env import env_configured
    from packages.agents.llm import _groq_api_key, _groq_chat_url
    from packages.agents.settings import get_agent_settings
    from packages.osint.settings import get_osint_settings

    osint = get_osint_settings()
    agent = get_agent_settings()
    return {
        "identify_live_search": osint.identify_live_search,
        "tavily_configured": bool(osint.tavily_api_key),
        "groq_configured": bool(_groq_api_key()),
        "groq_disabled": os.getenv("GROQ_DISABLED", "").lower() in {"1", "true", "yes"}
        or agent.groq_disabled,
        "groq_env_var": env_configured("GROQ_API_KEY"),
        "groq_model": agent.groq_model,
        "groq_api_base": agent.groq_api_base,
        "groq_chat_url": _groq_chat_url(),
        "identify_max_docs": int(os.getenv("IDENTIFY_MAX_DOCS", "3")),
        "qdrant_url": os.getenv("QDRANT_URL", "http://localhost:6333"),
        "embeddings_disabled": os.getenv("EMBEDDINGS_DISABLED", "").lower() in {"1", "true", "yes"},
    }


@router.post("/run")
def identify_run(body: IdentifyRunRequest | None = None) -> dict:
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


@router.post("/approve/{vector_id}")
def approve_vector(
    vector_id: str,
    db: Annotated[Session, Depends(get_db)],
    body: HitlDecision | None = None,
) -> dict:
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="vector_id not found")
    patch = (body.spec_patch if body else None) or {}
    patch["status"] = "open"
    set_atlas_status(db, vector_id, "open", patch)
    return {"vector_id": vector_id, "status": "open"}


@router.post("/reject/{vector_id}")
def reject_vector(vector_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        set_atlas_status(db, vector_id, "rejected")
    except KeyError:
        raise HTTPException(status_code=404, detail="vector_id not found")
    return {"vector_id": vector_id, "status": "rejected"}


@router.post("/reject-unsafe/{vector_id}")
def reject_unsafe_vector(vector_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    try:
        set_atlas_status(db, vector_id, "rejected_unsafe")
    except KeyError:
        raise HTTPException(status_code=404, detail="vector_id not found")
    return {"vector_id": vector_id, "status": "rejected_unsafe"}


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
        set_atlas_status(db, vector_id, row.status, patch)
        return {"vector_id": vector_id, "status": row.status, "patched": True}
    raise HTTPException(status_code=400, detail=f"unknown action: {action}")
