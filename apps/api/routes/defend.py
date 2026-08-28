"""Defend API — coverage map, Loop I drafts, miss path, fit/score."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.db import get_db
from packages.catalog.query import get_spec_by_vector_id
from packages.catalog.status import IllegalStatusTransition, transition_atlas_status
from packages.eval.fit import fit_champion, score_run
from packages.eval.loop_m import run_loop_m
from packages.policy.coverage import build_coverage_map, scout_topics_from_gaps
from packages.policy.loop_i import draft_rule_from_spec
from packages.policy.rules import load_v0_rules

router = APIRouter(prefix="/defend", tags=["defend"])


class FitRequest(BaseModel):
    run_id: str
    world_seed: int = 42


class ScoreRequest(BaseModel):
    run_id: str
    model_run_id: str | None = Field(default=None, description="Defaults to run_id")


class LoopMRequest(BaseModel):
    run_id: str
    miss_family: str
    train_seed: int = 42
    gtest_seed: int = 43
    n_customers: int | None = None
    n_merchants: int | None = None
    sim_days: int | None = None
    pin: bool | None = None


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
                "when": list(r.when),
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


@router.post("/fit")
def defend_fit(body: FitRequest) -> dict:
    """Fit champion on an existing Generate run. Sync, demo-sized."""
    try:
        return fit_champion(body.run_id, world_seed=body.world_seed)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, AssertionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/score")
def defend_score(body: ScoreRequest) -> dict:
    """Score eval fold. No Atlas vector_id. No knobs / denylist in JSON."""
    try:
        return score_run(body.run_id, model_run_id=body.model_run_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, AssertionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/loop-m")
def defend_loop_m(body: LoopMRequest) -> dict:
    """Miss family extra on train only, then G-test on a new seed. Does not set solved."""
    try:
        return run_loop_m(
            body.run_id,
            body.miss_family,
            train_seed=body.train_seed,
            gtest_seed=body.gtest_seed,
            n_customers=body.n_customers,
            n_merchants=body.n_merchants,
            sim_days=body.sim_days,
            pin=body.pin,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, AssertionError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
