"""Defend API — coverage map, Loop I drafts, miss path, fit/score."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.db import get_db
from packages.catalog.query import get_spec_by_vector_id
from packages.catalog.status import IllegalStatusTransition, transition_atlas_status
from packages.eval.fit import (
    GtestFreezeMismatchError,
    RecipeHashMismatchError,
    fit_champion,
    score_run,
    tune_champion,
)
from packages.eval.loop_m import run_loop_m
from packages.eval.loop_t import mine_fn_rules
from packages.policy.coverage import build_coverage_map, scout_topics_from_gaps
from packages.policy.loop_i import draft_rule_from_spec
from packages.policy.rule_hitl import approve_draft, load_drafts, reject_draft
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
    gtest_seed: int = 48
    family_chosen_from_slice: str = Field(default="gdev44", description="inner_val | diagnostic | gdev44")
    n_customers: int | None = None
    n_merchants: int | None = None
    sim_days: int | None = None
    pin: bool | None = None


class TuneRequest(BaseModel):
    run_id: str
    world_seed: int = 42
    n_trials: int | None = Field(default=None, description="Overrides recipe n_trials (CI uses 10)")
    timeout: float | None = Field(default=None, description="Overrides recipe timeout_seconds")
    dest_run_id: str | None = Field(
        default=None,
        description="Write tuned champion here; required after Stage 1 G-test so Stage 1 freeze is not overwritten",
    )


class LoopTMineRequest(BaseModel):
    train_run_id: str
    gdev_run_id: str
    family: str


class RejectRequest(BaseModel):
    note: str = ""


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
    try:
        from packages.lab.events import emit_lab

        emit_lab(
            "defend",
            "miss_recorded",
            f"miss recorded · vector_id={vector_id} · atlas status=open · Loop M eligible",
            level="info",
            loop="M",
            payload={"vector_id": vector_id, "status": row.status},
        )
    except Exception:
        pass
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
    except RecipeHashMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, AssertionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/score")
def defend_score(body: ScoreRequest) -> dict:
    """Score eval fold. No Atlas vector_id. No knobs / denylist in JSON."""
    try:
        result = score_run(body.run_id, model_run_id=body.model_run_id)
        try:
            from packages.lab.events import emit_lab

            metrics = result.get("metrics") or {}
            n_pos = metrics.get("n_pos") or {}
            recall = float(metrics.get("recall_at_op") or 0)
            for fam, n in n_pos.items():
                if fam == "normal":
                    continue
                est_fn = int(max(0, round(int(n) * (1.0 - recall))))
                emit_lab(
                    "defend",
                    "fn_harvest",
                    f"FN harvest · family={fam} · n_fn≈{est_fn} · queued for Loop M",
                    level="info",
                    loop="M",
                    tech=["AuthGate"],
                    payload={
                        "family": fam,
                        "n_fn": est_fn,
                        "n_pos": int(n),
                        "run_id": body.run_id,
                        "binary_ap": metrics.get("binary_ap"),
                        "genuine_fp": metrics.get("genuine_fp"),
                        "recall_at_op": recall,
                        "ap_by_family": metrics.get("ap_by_family"),
                        "action_histogram": result.get("action_histogram"),
                    },
                )
        except Exception:
            pass
        try:
            from packages.lab.pointers import save_score

            m = result.get("metrics") or {}
            ag = m.get("authgate_ms") or {}
            save_score(
                {
                    "run_id": result.get("run_id") or body.run_id,
                    "model_run_id": result.get("model_run_id") or body.model_run_id,
                    "metrics": {
                        "binary_ap": m.get("binary_ap"),
                        "recall_at_op": m.get("recall_at_op"),
                        "precision_at_op": m.get("precision_at_op"),
                        "genuine_fp": m.get("genuine_fp"),
                        "f1_at_op": m.get("f1_at_op"),
                        "tpr_at_fpr": m.get("tpr_at_fpr") or {},
                        "authgate_ms": {
                            "p50": ag.get("p50") or ag.get("p50_ms") or ag.get("p50_ms_per_row"),
                            "p99": ag.get("p99") or ag.get("p99_ms") or ag.get("p99_ms_per_row"),
                        },
                        "pass": m.get("pass"),
                    },
                }
            )
        except Exception:
            pass
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecipeHashMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except GtestFreezeMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, AssertionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tune")
def defend_tune(body: TuneRequest) -> dict:
    """Ticket 5 — Optuna search on inner_val only; writes best_params.json, refits."""
    try:
        return tune_champion(
            body.run_id,
            world_seed=body.world_seed,
            n_trials=body.n_trials,
            timeout=body.timeout,
            dest_run_id=body.dest_run_id,
        )
    except GtestFreezeMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecipeHashMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (AssertionError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/loop-m")
def defend_loop_m(body: LoopMRequest) -> dict:
    """Miss family extra on train only, then G-test on a new seed. Does not set solved."""
    try:
        result = run_loop_m(
            body.run_id,
            body.miss_family,
            train_seed=body.train_seed,
            gtest_seed=body.gtest_seed,
            family_chosen_from_slice=body.family_chosen_from_slice,
            n_customers=body.n_customers,
            n_merchants=body.n_merchants,
            sim_days=body.sim_days,
            pin=body.pin,
        )
        try:
            from packages.lab.pointers import save_loop_m

            cmp_ = result.get("comparison") or {}
            save_loop_m(
                {
                    "run_id": result.get("run_id") or body.run_id,
                    "miss_family": result.get("miss_family") or body.miss_family,
                    "ap_delta": cmp_.get("ap_delta"),
                    "pass": (result.get("metrics") or {}).get("pass"),
                    "genuine_fp_ok": cmp_.get("genuine_fp_ok"),
                    "ap_verdict": cmp_.get("ap_verdict"),
                }
            )
        except Exception:
            pass
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RecipeHashMismatchError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, AssertionError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/loop-t/mine")
def defend_loop_t_mine(body: LoopTMineRequest) -> dict:
    """Loop T: Mine decision-tree FN rules on G-dev seed 44."""
    try:
        return mine_fn_rules(body.train_run_id, body.gdev_run_id, body.family)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, AssertionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rules/drafts")
def defend_rules_drafts(status: str | None = None) -> dict:
    """List rule drafts. Default view = proposed only (the reviewable queue),
    so orchestrator auto-rejects stay hidden unless ?status=auto_rejected —
    they remain human-approvable via /rules/approve/."""
    drafts = load_drafts()
    if status:
        drafts = [d for d in drafts if d.get("status") == status]
    else:
        drafts = [d for d in drafts if d.get("status") == "proposed"]
    return {"count": len(drafts), "items": drafts}


@router.post("/rules/approve/{draft_id}")
def defend_rules_approve(draft_id: str) -> dict:
    """HITL: Approve a rule draft into live v0_rules.yaml."""
    try:
        return approve_draft(draft_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/rules/reject/{draft_id}")
def defend_rules_reject(draft_id: str, body: RejectRequest | None = None) -> dict:
    """HITL: Reject a rule draft."""
    note = body.note if body else ""
    try:
        return reject_draft(draft_id, note=note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
