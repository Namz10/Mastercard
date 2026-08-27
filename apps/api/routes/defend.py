"""Defend API — coverage map, Loop I drafts, miss path."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.db import get_db
from packages.catalog.query import get_spec_by_vector_id
from packages.catalog.status import IllegalStatusTransition, transition_atlas_status
from packages.policy.coverage import build_coverage_map, scout_topics_from_gaps
from packages.policy.loop_i import draft_rule_from_spec
from packages.policy.rules import load_v0_rules

router = APIRouter(prefix="/defend", tags=["defend"])


@router.get("/coverage-map")
def coverage_map(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Loop C: 24 techniques × live_rule | named_gap | case_only."""
    return build_coverage_map(db)


@router.get("/scout-topics")
def defend_scout_topics(
    db: Annotated[Session, Depends(get_db)],
    max_topics: int = 5,
) -> dict:
    """Empty coverage cells → suggested Scout topics for next Identify run."""
    topics = scout_topics_from_gaps(db, max_topics=max_topics)
    return {"count": len(topics), "topics": topics}


@router.get("/rules/v0")
def v0_rules() -> dict:
    rules = load_v0_rules()
    return {
        "count": len(rules),
        "items": [
            {
                "id": r.id,
                "kind": r.kind,
                "applies_to": r.applies_to,
                "when": r.when,
                "min_score": r.min_score,
                "reason": r.reason,
                "technique_ids": list(r.technique_ids),
                "status": r.status,
            }
            for r in rules
        ],
    }


@router.post("/loop-i/draft/{vector_id}")
def loop_i_draft(vector_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """Loop I: draft v0 rule or named gap from one catalog card."""
    spec = get_spec_by_vector_id(db, vector_id)
    if not spec:
        raise HTTPException(status_code=404, detail="vector_id not found")
    return draft_rule_from_spec(spec)


@router.post("/miss/{vector_id}")
def defend_miss(vector_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    """
    Defend miss path: keep catalog row open (not solved).
    Identify never calls AuthGate; this is the catalog handshake from Defend.
    """
    try:
        row = transition_atlas_status(db, vector_id, "open")
    except KeyError:
        raise HTTPException(status_code=404, detail="vector_id not found")
    except IllegalStatusTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {
        "vector_id": vector_id,
        "status": row.status,
        "message": "miss recorded — status remains open for re-generation",
    }
