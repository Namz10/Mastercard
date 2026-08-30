"""Command Center — aggregated lab snapshot for Analyst Copilot."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import AtlasRow
from packages.agents.llm.config import LlmConfigurationError, load_provider_config, public_llm_status
from packages.lab.events import get_lab_bus
from packages.lab.pointers import load_identify, load_loop_m, load_score
from packages.osint.settings import get_osint_settings
from packages.policy.coverage import build_coverage_map
from packages.policy.rule_hitl import load_drafts
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR

router = APIRouter(prefix="/command-center", tags=["command-center"])

_ROOT = Path(__file__).resolve().parents[3]
_MODELS_DIR = _ROOT / "models"

LOOPS: dict[str, dict[str, str]] = {
    "I": {"name": "Catalog ↔ draft rules", "status": "live", "evidence": "loop-i drafts"},
    "C": {"name": "Coverage → scout topics", "status": "live", "evidence": "scout-topics"},
    "M": {"name": "Miss → retrain", "status": "live", "evidence": "loop-m + user approval"},
    "T": {"name": "FN → tree rules", "status": "partial", "evidence": "loop-t/mine"},
    "R": {"name": "Analyser flags", "status": "roadmap", "evidence": "—"},
    "A": {"name": "Cat 4 red/blue", "status": "offline", "evidence": "taxonomy only"},
    "F": {"name": "Lab vs public", "status": "roadmap", "evidence": "—"},
    "G": {"name": "Generate knob search", "status": "roadmap", "evidence": "—"},
    "H": {"name": "Human overrides", "status": "writeup", "evidence": "—"},
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ready_blob() -> dict[str, Any]:
    from sqlalchemy import text

    from apps.api.db import engine

    postgres_ok = False
    pgvector_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            postgres_ok = True
            row = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
            pgvector_ok = row is not None
    except Exception:
        pass
    osint = get_osint_settings()
    llm = public_llm_status()
    return {
        "status": "ok" if postgres_ok and pgvector_ok else "degraded",
        "postgres": postgres_ok,
        "pgvector": pgvector_ok,
        "identify_live_search": osint.identify_live_search,
        "tavily_configured": bool(osint.tavily_api_key),
        "llm": llm,
    }


def _latest_run_dir() -> Path | None:
    if not RUNS_DIR.is_dir():
        return None
    dirs = [p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "_DONE").exists()]
    if not dirs:
        dirs = [p for p in RUNS_DIR.iterdir() if p.is_dir() and (p / "manifest.json").exists()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _latest_metrics() -> tuple[str | None, dict[str, Any] | None]:
    if not _MODELS_DIR.is_dir():
        return None, None
    best: tuple[float, Path] | None = None
    for p in _MODELS_DIR.iterdir():
        if not p.is_dir():
            continue
        m = p / "metrics.json"
        if m.is_file():
            mt = m.stat().st_mtime
            if best is None or mt > best[0]:
                best = (mt, m)
    if not best:
        return None, None
    metrics = _read_json(best[1])
    return best[1].parent.name, metrics


def _fidelity_from_lab(events: list[dict[str, Any]]) -> dict[str, Any]:
    for ev in reversed(events):
        if ev.get("stage") == "evaluate_fidelity":
            payload = ev.get("payload") or {}
            fid = payload.get("fidelity")
            if isinstance(fid, dict):
                return fid
    return {}


def _phase_status_from_events(events: list[dict[str, Any]]) -> dict[str, str]:
    phases = ("identify", "generate", "defend", "evolve")
    status = {p: "idle" for p in phases}
    for ev in events:
        phase = str(ev.get("phase") or "")
        if phase not in status:
            continue
        level = str(ev.get("level") or "")
        msg = str(ev.get("message") or "").upper()
        if "ERROR" in msg or level == "error":
            status[phase] = "error"
        elif status[phase] != "error":
            status[phase] = "complete"
    # Mark last non-system phase as running if recent end missing
    for ev in reversed(events[-20:]):
        phase = str(ev.get("phase") or "")
        if phase in status and status[phase] != "error":
            msg = str(ev.get("message") or "")
            if "START" in msg.upper() or ev.get("level") == "stage":
                # keep complete unless clearly mid-run — leave as complete for snapshot
                break
    return status


def build_snapshot(db: Session, thread_id: str = "demo-1") -> dict[str, Any]:
    system = _ready_blob()
    coverage = build_coverage_map(db)
    status_counts = dict(coverage.get("status_counts") or {})

    rows = db.query(AtlasRow).all()
    techniques = {r.technique_id for r in rows if r.technique_id}
    by_status: dict[str, int] = {}
    by_mode: dict[str, int] = {}
    for r in rows:
        by_status[str(r.status)] = by_status.get(str(r.status), 0) + 1
        gm = str(r.generate_mode or "unknown")
        by_mode[gm] = by_mode.get(gm, 0) + 1

    hitl_rows = (
        db.query(AtlasRow)
        .filter(AtlasRow.status == "proposed")
        .order_by(AtlasRow.updated_at.desc())
        .all()
    )
    hitl_pending = len(hitl_rows)
    last_topic = None
    if hitl_rows:
        spec = dict(hitl_rows[0].spec or {})
        last_topic = spec.get("name") or hitl_rows[0].name

    last_identify = load_identify() or {}
    if last_identify.get("topic"):
        last_topic = last_identify.get("topic") or last_topic

    drafts = [d for d in load_drafts() if d.get("status") == "proposed"]
    v0 = load_v0_rules()

    run_dir = _latest_run_dir()
    generate_last: dict[str, Any] = {}
    fidelity: dict[str, Any] = {}
    if run_dir:
        manifest = _read_json(run_dir / "manifest.json") or {}
        sidecar = _read_json(run_dir / "sidecar.json") or {}
        generate_last = {
            "run_id": run_dir.name,
            "mode": sidecar.get("mode") or ("canary" if run_dir.name.startswith("canary") else "population"),
            "world_seed": sidecar.get("world_seed") or manifest.get("world_seed"),
            "n_customers": sidecar.get("n_customers") or manifest.get("n_customers"),
            "n_merchants": sidecar.get("n_merchants") or manifest.get("n_merchants"),
            "sim_days": sidecar.get("sim_days") or manifest.get("sim_days"),
            "row_count": manifest.get("row_count"),
            "mix": sidecar.get("mix") or {},
        }

    model_run_id, metrics = _latest_metrics()
    defend: dict[str, Any] = {
        "champion_run_id": model_run_id,
        "metrics": {},
        "drafts_pending": len(drafts),
        "v0_rule_count": len(v0),
    }
    if metrics:
        ag = metrics.get("authgate_ms") or {}
        app_ab = metrics.get("app_ablation") or {}
        with_ap = None
        without_ap = None
        if isinstance(app_ab.get("with_app_flags"), dict):
            with_ap = app_ab["with_app_flags"].get("average_precision")
        if isinstance(app_ab.get("without_app_flags"), dict):
            without_ap = app_ab["without_app_flags"].get("average_precision")
        delta = None
        if isinstance(with_ap, (int, float)) and isinstance(without_ap, (int, float)):
            delta = float(with_ap) - float(without_ap)
        defend["metrics"] = {
            "binary_ap": metrics.get("binary_ap"),
            "recall_at_op": metrics.get("recall_at_op"),
            "precision_at_op": metrics.get("precision_at_op"),
            "genuine_fp": metrics.get("genuine_fp"),
            "f1_at_op": metrics.get("f1_at_op"),
            "tpr_at_fpr": metrics.get("tpr_at_fpr") or {},
            "authgate_ms": {
                "p50": ag.get("p50") or ag.get("p50_ms") or ag.get("p50_ms_per_row"),
                "p99": ag.get("p99") or ag.get("p99_ms") or ag.get("p99_ms_per_row"),
            },
            "app_ablation": {
                "with_flags_ap": with_ap or app_ab.get("with_flags_ap"),
                "without_flags_ap": without_ap or app_ab.get("without_flags_ap"),
                "delta": delta if delta is not None else app_ab.get("delta") or app_ab.get("ap_delta"),
            },
            "pass": metrics.get("pass"),
        }

    events = [e.to_dict() for e in get_lab_bus().history(thread_id)]
    lab_events = events[-8:]
    if not fidelity:
        fidelity = _fidelity_from_lab(events)
    if fidelity:
        generate_last["fidelity"] = {
            "pass": fidelity.get("pass"),
            "psi_amount": fidelity.get("psi_amount"),
            "psi_hour": fidelity.get("psi_hour"),
            "fraud_rate": fidelity.get("fraud_rate"),
            "mule_fan_in_median": fidelity.get("mule_fan_in_median"),
            "reasons": fidelity.get("reasons") or [],
        }

    # Loop M delta from gtest_score.json if present next to metrics
    loop_m_last: dict[str, Any] = {}
    if model_run_id:
        gtest = _read_json(_MODELS_DIR / model_run_id / "gtest_score.json")
        if gtest:
            loop_m_last = {
                "run_id": model_run_id,
                "ap_delta": (gtest.get("comparison") or {}).get("ap_delta") or gtest.get("ap_delta"),
                "pass": (gtest.get("metrics") or {}).get("pass") or gtest.get("pass"),
                "genuine_fp_ok": (gtest.get("comparison") or {}).get("genuine_fp_ok"),
            }

    # Prefer last score_run / Loop M pointers when present (shared across browsers)
    last_score = load_score()
    if last_score:
        if last_score.get("model_run_id") or last_score.get("run_id"):
            defend["champion_run_id"] = (
                last_score.get("model_run_id") or last_score.get("run_id") or defend["champion_run_id"]
            )
        sm = last_score.get("metrics") or {}
        if sm:
            merged = dict(defend["metrics"] or {})
            for k, v in sm.items():
                if v is not None:
                    merged[k] = v
            defend["metrics"] = merged

    ptr_m = load_loop_m()
    if ptr_m:
        loop_m_last = {
            "run_id": ptr_m.get("run_id") or loop_m_last.get("run_id"),
            "ap_delta": ptr_m.get("ap_delta") if ptr_m.get("ap_delta") is not None else loop_m_last.get("ap_delta"),
            "pass": ptr_m.get("pass") if ptr_m.get("pass") is not None else loop_m_last.get("pass"),
            "genuine_fp_ok": ptr_m.get("genuine_fp_ok")
            if ptr_m.get("genuine_fp_ok") is not None
            else loop_m_last.get("genuine_fp_ok"),
        }

    phase_status = _phase_status_from_events(events)

    kpis = {
        "atlas_techniques": f"{len(techniques)} / 24" if techniques else "0 / 24",
        "atlas_count": len(techniques),
        "live_rules": status_counts.get("live_rule", 0),
        "hitl_pending": hitl_pending,
        "loop_m_ap_delta": loop_m_last.get("ap_delta"),
        "genuine_fpr": defend["metrics"].get("genuine_fp"),
        "authgate_p50_ms": (defend["metrics"].get("authgate_ms") or {}).get("p50"),
    }

    return {
        "generated_at": _iso_now(),
        "thread_id": thread_id,
        "system": system,
        "kpis": kpis,
        "atlas": {
            "techniques": len(techniques),
            "by_status": by_status,
            "by_generate_mode": by_mode,
        },
        "coverage": {
            "technique_count": coverage.get("technique_count"),
            "cells": coverage.get("cells"),
            "status_counts": status_counts,
            "scout_topics_for_gaps": (coverage.get("scout_topics_for_gaps") or [])[:5],
            "generate_eligible": sum(
                1
                for c in (coverage.get("cells") or [])
                if c.get("generate_mode") in {"population", "canary", "population_or_canary"}
            ),
        },
        "identify": {
            "hitl_pending": hitl_pending,
            "hitl_approved": by_status.get("open", 0) + by_status.get("approved", 0),
            "hitl_rejected": by_status.get("rejected", 0),
            "last_topic": last_topic,
            "last_run": {
                "run_id": last_identify.get("run_id"),
                "topic": last_identify.get("topic"),
                "scout_candidate_count": last_identify.get("scout_candidate_count"),
                "curator_kept_count": last_identify.get("curator_kept_count"),
                "proposed_count": last_identify.get("proposed_count"),
                "hitl_required": last_identify.get("hitl_required"),
            }
            if last_identify.get("run_id")
            else {},
        },
        "generate": {
            "last_run": generate_last,
            "fidelity": generate_last.get("fidelity") or {},
        },
        "defend": defend,
        "evolve": {
            "generation": 1 if loop_m_last else 0,
            "loop_m_last": loop_m_last,
            "retrain_queue": [],  # client merges localStorage queue
            "catalog_solved": False,
        },
        "loops": LOOPS,
        "phase_status": phase_status,
        "lab_events": lab_events,
        "ethics": {
            "synthetic_only": True,
            "catalog_solved": False,
            "cat4_public_api": False,
            "llm_not_detector": True,
        },
    }


class BriefRequest(BaseModel):
    thread_id: str = "demo-1"
    snapshot: dict[str, Any] | None = Field(
        default=None,
        description="Optional client-merged snapshot; server rebuilds if omitted",
    )


def _static_brief(snapshot: dict[str, Any]) -> str:
    k = snapshot.get("kpis") or {}
    g = (snapshot.get("generate") or {}).get("last_run") or {}
    ident = snapshot.get("identify") or {}
    ident_run = ident.get("last_run") or {}
    d = (snapshot.get("defend") or {}).get("metrics") or {}
    evo = (snapshot.get("evolve") or {}).get("loop_m_last") or {}
    fid = (g.get("fidelity") or {})
    p50 = ((d.get("authgate_ms") or {}).get("p50"))
    delta = evo.get("ap_delta")
    delta_s = "—" if delta is None else f"{float(delta):+.4f}"
    return (
        f"AegisLoop is a synthetic payment-fraud lab closed loop: Identify (LangGraph · Tavily · "
        f"pgvector HITL) → Generate (ShadowRail · PyArrow) → Defend (HistGradientBoostingClassifier · "
        f"AuthGate · Brake) → Evolve (Loop M with analyst approval). Atlas shows {k.get('atlas_techniques', '—')} "
        f"techniques with {k.get('live_rules', 0)} live_rule cells; HITL queue has {k.get('hitl_pending', 0)} pending. "
        f"Last Identify run {ident_run.get('run_id') or '—'} topic={ident_run.get('topic') or ident.get('last_topic') or '—'} "
        f"proposed={ident_run.get('proposed_count', '—')}.\n\n"
        f"Latest generate run {g.get('run_id', '—')} exported {g.get('row_count', '—')} rows; fidelity.pass="
        f"{fid.get('pass', 'unknown')}. AuthGate headline metrics (lab eval): "
        f"binary_ap={d.get('binary_ap', '—')}, genuine_fp={d.get('genuine_fp', '—')}, "
        f"p50={p50 if p50 is not None else '—'}ms. Last Loop M ΔAP={delta_s}; catalog_solved remains false.\n\n"
        f"Honest gaps: Cat 4 adversarial AI stays offline (no public attack API); Loops R/F/G are roadmap; "
        f"Loop T is partial. The LLM here only summarizes verified lab JSON — AuthGate + Brake score payments, "
        f"never the language model."
    )


def _llm_brief(snapshot: dict[str, Any]) -> tuple[str, str]:
    """Returns (text, source) where source is llm|static."""
    try:
        cfg = load_provider_config()
    except LlmConfigurationError:
        return _static_brief(snapshot), "static"

    import httpx

    system = (
        "Summarize lab state in 3 short paragraphs for a Mastercard judge: pillars, closed loop, "
        "headline metrics, honest gaps. Use only provided numbers. State LLM is not the detector. "
        "Mention synthetic-only constraint. No PAN/VPA. No invented metrics."
    )
    # Strip cells (large) for prompt
    slim = {k: v for k, v in snapshot.items() if k != "coverage"}
    cov = snapshot.get("coverage") or {}
    slim["coverage"] = {
        "technique_count": cov.get("technique_count"),
        "status_counts": cov.get("status_counts"),
        "generate_eligible": cov.get("generate_eligible"),
    }
    user = json.dumps(slim, default=str)[:12000]
    headers = {"Content-Type": "application/json"}
    if cfg.auth_mode == "bearer" and cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    body = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 600,
    }
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    try:
        with httpx.Client(timeout=45.0) as client:
            r = client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"].strip()
            if text:
                return text, "llm"
    except Exception:
        pass
    return _static_brief(snapshot), "static"


@router.get("/snapshot")
def command_center_snapshot(
    db: Annotated[Session, Depends(get_db)],
    thread_id: str = "demo-1",
) -> dict[str, Any]:
    return build_snapshot(db, thread_id=thread_id)


@router.post("/brief")
def command_center_brief(
    body: BriefRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    snap = body.snapshot if isinstance(body.snapshot, dict) and body.snapshot else build_snapshot(
        db, thread_id=body.thread_id
    )
    # Never accept client ethics overrides that claim solved/cat4
    ethics = dict(snap.get("ethics") or {})
    ethics.update({"synthetic_only": True, "catalog_solved": False, "cat4_public_api": False, "llm_not_detector": True})
    snap["ethics"] = ethics
    text, source = _llm_brief(snap)
    return {
        "generated_at": _iso_now(),
        "source": source,
        "text": text,
        "disclaimer": "LLM summarizes lab state from verified metrics. AuthGate + Brake score payments.",
    }
