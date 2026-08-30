"""Lab SSE stream + demo pipeline orchestration."""

from __future__ import annotations

import threading
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.db import SessionLocal
from packages.lab.events import (
    DEFAULT_TRACE,
    emit_lab,
    emit_loop_end,
    emit_loop_start,
    get_lab_bus,
    iter_sse,
    load_replay_trace,
)

router = APIRouter(prefix="/lab", tags=["lab"])


class DemoRunRequest(BaseModel):
    thread_id: str = "demo-1"
    mode: Literal["live", "replay"] = "live"
    skip_identify: bool = False
    skip_generate: bool = False
    skip_defend: bool = False
    skip_evolve: bool = True  # Loop M requires Arms Race approval by default
    topic: str = "deepfake UPI payment fraud"
    world_seed: int = 42
    n_customers: int = 64
    n_merchants: int = 16
    sim_days: int = 20
    miss_family: str | None = None


class ReplayRequest(BaseModel):
    thread_id: str = "demo-1"


def _run_demo_pipeline(req: DemoRunRequest) -> None:
    """Background live demo: Identify → Generate → Defend (Loop M gated elsewhere)."""
    bus = get_lab_bus()
    bus.set_active_thread(req.thread_id)
    emit_lab(
        "system",
        "demo_start",
        f"Demo pipeline start · mode=live · thread_id={req.thread_id}",
        level="info",
        tech=["FastAPI", "PostgreSQL"],
        payload={"thread_id": req.thread_id},
        thread_id=req.thread_id,
    )
    db = SessionLocal()
    run_id: str | None = None
    try:
        if not req.skip_identify:
            from packages.agents.identify_graph import NODE_ORDER, run_identify_graph
            from packages.policy.coverage import scout_topics_from_gaps

            emit_loop_start("C", "scout_topics_from_gaps", phase="identify", thread_id=req.thread_id)
            topics = scout_topics_from_gaps(db, max_topics=3)
            emit_lab(
                "identify",
                "scout_topics",
                f"Loop C scout topics · count={len(topics)}",
                level="loop",
                loop="C",
                tech=["PostgreSQL"],
                payload={"topics": topics},
                thread_id=req.thread_id,
            )
            emit_loop_end("C", phase="identify", pass_=True, payload={"count": len(topics)}, thread_id=req.thread_id)

            emit_lab(
                "identify",
                "graph_start",
                f"Identify LangGraph start · topic={req.topic!r}",
                level="stage",
                tech=["LangGraph", "Tavily", "pgvector", "sentence-transformers"],
                payload={"topic": req.topic},
                thread_id=req.thread_id,
            )
            for node in NODE_ORDER:
                emit_lab(
                    "identify",
                    node,
                    f"Identify node · {node}",
                    level="stage",
                    tech=["LangGraph"],
                    payload={"node": node},
                    thread_id=req.thread_id,
                )
            result = run_identify_graph(run_id=f"lab-{req.thread_id}", topic=req.topic)
            hitl_n = len(result.get("hitl_queue") or result.get("proposed_specs") or [])
            emit_lab(
                "identify",
                "librarian",
                f"Librarian staged HITL queue · proposed={len(result.get('proposed_specs') or [])} · hitl={hitl_n}",
                level="hitl",
                tech=["PostgreSQL", "LangGraph"],
                payload={
                    "run_id": result.get("run_id"),
                    "proposed_count": len(result.get("proposed_specs") or []),
                    "scout_candidate_count": result.get("scout_candidate_count"),
                },
                thread_id=req.thread_id,
            )
            # Auto-approve first proposed if present (demo convenience)
            from apps.api.models import AtlasRow
            from packages.catalog.status import transition_atlas_status

            proposed = (
                db.query(AtlasRow).filter(AtlasRow.status == "proposed").order_by(AtlasRow.vector_id).limit(1).all()
            )
            for row in proposed:
                try:
                    transition_atlas_status(db, row.vector_id, "open")
                    emit_lab(
                        "identify",
                        "hitl_approve",
                        f"HITL approve · vector_id={row.vector_id}",
                        level="hitl",
                        loop="I",
                        payload={"vector_id": row.vector_id, "status": "open"},
                        thread_id=req.thread_id,
                    )
                except Exception as exc:
                    emit_lab(
                        "identify",
                        "hitl_approve",
                        f"HITL skip · {exc}",
                        level="warn",
                        thread_id=req.thread_id,
                    )

            # Loop I draft for a known seed vector
            try:
                from packages.catalog.query import get_spec_by_vector_id
                from packages.policy.loop_i import draft_rule_from_spec

                emit_loop_start("I", "draft_rule_from_spec:t13", phase="defend", thread_id=req.thread_id)
                spec = get_spec_by_vector_id(db, "t13-upi-impersonation-app")
                if spec:
                    draft = draft_rule_from_spec(spec)
                    emit_lab(
                        "defend",
                        "loop_i_draft",
                        f"Loop I draft · vector_id=t13-upi-impersonation-app · status={draft.get('coverage_status')}",
                        level="loop",
                        loop="I",
                        tech=["v0 rules"],
                        payload=draft if isinstance(draft, dict) else {"draft": str(draft)},
                        thread_id=req.thread_id,
                    )
                emit_loop_end("I", phase="defend", pass_=True, thread_id=req.thread_id)
            except Exception as exc:
                emit_lab("defend", "loop_i_draft", f"Loop I skipped · {exc}", level="warn", thread_id=req.thread_id)

        if not req.skip_generate:
            from packages.sim.runner import run_population

            emit_lab(
                "generate",
                "generate_quiet_world",
                f"ShadowRail population · world_seed={req.world_seed} · n_customers={req.n_customers} · sim_days={req.sim_days}",
                level="stage",
                tech=["ShadowRail", "packages/sim"],
                payload={
                    "world_seed": req.world_seed,
                    "n_customers": req.n_customers,
                    "n_merchants": req.n_merchants,
                    "sim_days": req.sim_days,
                },
                thread_id=req.thread_id,
            )
            pop = run_population(
                db,
                run_id=None,
                world_seed=req.world_seed,
                n_customers=req.n_customers,
                n_merchants=req.n_merchants,
                sim_days=req.sim_days,
                pin=True,
            )
            run_id = pop["run_id"]
            emit_lab(
                "generate",
                "export_run",
                f"PyArrow export · row_count={pop.get('event_count')} · run_id={run_id}",
                level="stage",
                tech=["PyArrow Parquet"],
                payload={
                    "run_id": run_id,
                    "event_count": pop.get("event_count"),
                    "fidelity": pop.get("fidelity"),
                    "counts_by_label_family": pop.get("counts_by_label_family"),
                },
                thread_id=req.thread_id,
            )

        if not req.skip_defend and run_id:
            from packages.eval.fit import fit_champion, score_run

            emit_lab(
                "defend",
                "fit_champion",
                f"AuthGate fit_champion · run_id={run_id}",
                level="stage",
                tech=["scikit-learn HistGradientBoostingClassifier", "IsolationForest"],
                payload={"run_id": run_id},
                thread_id=req.thread_id,
            )
            fit = fit_champion(run_id, world_seed=req.world_seed)
            emit_lab(
                "defend",
                "persist",
                f"persist champion · model_freeze_id={fit.get('metrics', {}).get('model_freeze_id')}",
                level="stage",
                tech=["joblib"],
                payload={"run_id": run_id, "model_freeze_id": fit.get("metrics", {}).get("model_freeze_id")},
                thread_id=req.thread_id,
            )
            score = score_run(run_id, model_run_id=run_id)
            metrics = score.get("metrics") or {}
            emit_lab(
                "defend",
                "score_run",
                f"score_run · binary_ap={metrics.get('binary_ap')} · recall_at_op={metrics.get('recall_at_op')} · genuine_fp={metrics.get('genuine_fp')}",
                level="stage",
                tech=["AuthGate", "Brake"],
                payload={
                    "run_id": run_id,
                    "binary_ap": metrics.get("binary_ap"),
                    "recall_at_op": metrics.get("recall_at_op"),
                    "genuine_fp": metrics.get("genuine_fp"),
                    "action_histogram": score.get("action_histogram"),
                    "top_features": metrics.get("top_features"),
                    "ap_by_family": metrics.get("ap_by_family"),
                    "n_pos": metrics.get("n_pos"),
                    "confusion_matrix": metrics.get("confusion_matrix"),
                },
                thread_id=req.thread_id,
            )
            emit_lab(
                "evolve",
                "cat4_roadmap",
                "Cat 4 offline · Oracle Guard · not public API",
                level="info",
                loop="A",
                payload={"status": "roadmap"},
                thread_id=req.thread_id,
            )

        if not req.skip_evolve and run_id and req.miss_family:
            from packages.eval.loop_m import run_loop_m

            emit_loop_start("M", f"miss_family:{req.miss_family}", phase="evolve", thread_id=req.thread_id)
            body = run_loop_m(
                run_id,
                req.miss_family,
                train_seed=42,
                gtest_seed=48,
                family_chosen_from_slice="gdev44",
            )
            emit_loop_end(
                "M",
                phase="evolve",
                pass_=bool(body.get("metrics", {}).get("pass")),
                payload={
                    "ap_delta": (body.get("comparison") or {}).get("ap_delta"),
                    "catalog_solved": False,
                    "genuine_fp_ok": (body.get("comparison") or {}).get("genuine_fp_ok"),
                    "run_id": run_id,
                    "miss_family": req.miss_family,
                },
                thread_id=req.thread_id,
            )

        emit_lab(
            "system",
            "demo_end",
            f"Demo pipeline complete · run_id={run_id}",
            level="info",
            payload={"run_id": run_id, "thread_id": req.thread_id},
            thread_id=req.thread_id,
        )
    except Exception as exc:
        emit_lab(
            "system",
            "demo_error",
            f"Demo pipeline failed: {exc}",
            level="error",
            payload={"error": str(exc)},
            thread_id=req.thread_id,
        )
    finally:
        db.close()


@router.get("/stream")
def lab_stream(thread_id: str = Query("demo-1")) -> StreamingResponse:
    """SSE lab event stream for Simulation Console."""
    return StreamingResponse(
        iter_sse(thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
def lab_history(thread_id: str = Query("demo-1")) -> dict[str, Any]:
    events = [e.to_dict() for e in get_lab_bus().history(thread_id)]
    return {"thread_id": thread_id, "count": len(events), "events": events}


@router.post("/replay")
def lab_replay(body: ReplayRequest) -> dict[str, Any]:
    """Push fixture trace onto the bus for offline demo (Plan 03 resilience)."""
    bus = get_lab_bus()
    bus.set_active_thread(body.thread_id)
    bus.clear(body.thread_id)
    events = load_replay_trace(DEFAULT_TRACE)
    if not events:
        raise HTTPException(status_code=404, detail=f"No replay fixture at {DEFAULT_TRACE}")
    for ev in events:
        ev.thread_id = body.thread_id
        bus.emit(ev)
    return {"thread_id": body.thread_id, "replayed": len(events), "path": str(DEFAULT_TRACE)}


@router.post("/demo")
def lab_demo(body: DemoRunRequest) -> dict[str, Any]:
    """Start live (or replay) demo pipeline. Stream via GET /lab/stream."""
    bus = get_lab_bus()
    bus.set_active_thread(body.thread_id)
    bus.clear(body.thread_id)
    if body.mode == "replay":
        return lab_replay(ReplayRequest(thread_id=body.thread_id))

    t = threading.Thread(target=_run_demo_pipeline, args=(body,), daemon=True)
    t.start()
    return {
        "thread_id": body.thread_id,
        "stream_url": f"/lab/stream?thread_id={body.thread_id}",
        "status": "started",
        "skip_evolve": body.skip_evolve,
    }


@router.get("/ready-check")
def lab_ready() -> dict[str, str]:
    return {"status": "ok", "bus": "ready"}
