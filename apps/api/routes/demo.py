"""Demo / recorded pack routes for booth fallback."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/demo", tags=["demo"])
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"


def _read_tpr(entry: object) -> float | None:
    if entry is None:
        return None
    if isinstance(entry, (int, float)):
        return float(entry)
    if isinstance(entry, dict) and "tpr" in entry:
        return float(entry["tpr"])
    return None


def _tpr_curve_from_pareto(pareto: dict) -> dict[str, float | dict[str, float]]:
    out: dict[str, float | dict[str, float]] = {}
    for key, entry in pareto.items():
        if not isinstance(entry, dict):
            continue
        tpr = _read_tpr(entry.get("tpr"))
        if tpr is not None:
            out[str(key)] = {"tpr": tpr, "fpr_target": float(key)}
    return out


def _freeze_score() -> dict:
    """Champion metrics from internal_01pct_fpr_freeze + pareto curves (LoopM)."""
    freeze_path = DATA / "validation" / "v1" / "internal_01pct_fpr_freeze.json"
    if not freeze_path.exists():
        raise HTTPException(status_code=404, detail="internal_01pct_fpr_freeze.json not found")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    op = freeze["frozen_operating_point"]
    model_run_id = freeze.get("model_run_id", "v1-train-46__loopm-train")

    tpr_at_fpr: dict[str, float | dict[str, float]] = {}

    pareto_path = DATA / "validation" / "v1" / "pareto_gtest48.json"
    if pareto_path.exists():
        pareto_doc = json.loads(pareto_path.read_text(encoding="utf-8"))
        loopm = pareto_doc.get("models", {}).get("LoopM", {}).get("pareto", {})
        tpr_at_fpr = _tpr_curve_from_pareto(loopm)

    genuine_path = DATA / "validation" / "v1" / "pareto_genuine_fpr.json"
    if genuine_path.exists():
        genuine_doc = json.loads(genuine_path.read_text(encoding="utf-8"))
        loopm_g = genuine_doc.get("worlds", {}).get("v1-gtest-48", {}).get("LoopM", {}).get("envelope", {})
        for key, entry in loopm_g.items():
            if not isinstance(entry, dict):
                continue
            recall_pt = entry.get("recall")
            if recall_pt is not None:
                tpr_at_fpr[str(key)] = {"tpr": float(recall_pt), "fpr_target": float(key)}

    # Protocol freeze: ~98.52% recall @ ~0.032% genuine FPR (threshold from inner_val only).
    gf = float(op["genuine_fp"])
    recall = float(op["recall_at_op"])
    tpr_at_fpr[f"{gf:.6g}"] = {"tpr": recall, "fpr_target": gf}

    # Reference post-hoc point: ~98.67% @ 0.1% FPR on gtest-48 (not the protocol threshold).
    ref_recall = freeze.get("acceptance", {}).get("reference_posthoc_pareto_recall_01pct_g48")
    if ref_recall is not None:
        tpr_at_fpr["0.001"] = {"tpr": float(ref_recall), "fpr_target": 0.001}

    n_pos = op.get("n_pos") or {}
    n_eval = sum(int(v) for v in n_pos.values()) if n_pos else 0
    cm = op.get("confusion_matrix") or {}
    if isinstance(cm, dict):
        confusion = [cm.get("tn", 0), cm.get("fp", 0), cm.get("fn", 0), cm.get("tp", 0)]
    else:
        confusion = cm

    ap_by_family = op.get("ap_by_family") or {}
    metrics = {
        "pass": True,
        "n_eval": n_eval,
        "ap_by_family": {k: {"ap": v} for k, v in ap_by_family.items()},
        "tpr_at_fpr": tpr_at_fpr,
        "genuine_fp": gf,
        "f1_at_op": 0.0,
        "precision_at_op": float(op.get("precision_at_op", 0.9857)),
        "recall_at_op": recall,
        "binary_ap": float(op.get("binary_ap", 0.9985)),
        "confusion_matrix": confusion,
        "op_threshold": float(op.get("detect_thr", 0.915)),
        "recipe_hash": "frozen",
        "model_freeze_id": "frozen",
        "top_features": [],
        "n_pos": n_pos,
    }
    return {
        "run_id": freeze.get("eval_run_id", "v1-gtest-48"),
        "model_run_id": model_run_id,
        "metrics": metrics,
        "action_histogram": op.get("action_histogram") or {},
        "split": "gtest",
        "recipe_hash": "frozen",
        "model_freeze_id": "frozen",
        "frozen": True,
    }


@router.get("/recorded/score")
def recorded_score() -> dict:
    logger.info("demo recorded/score served reason=defend_bootstrap_or_fallback")
    return _freeze_score()


@router.get("/recorded/loop")
def recorded_loop() -> dict:
    path = DATA / "validation" / "v1" / "loop_m_result.json"
    if not path.exists():
        path = DATA / "validation" / "stage3" / "loop_m_result.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="loop_m_result.json not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/recorded/identify")
def recorded_identify() -> dict:
    """Fixture timeline for paced Identify playback."""
    logger.info("demo recorded/identify served reason=frontend_recorded_playback")
    fixtures = DATA / "osint" / "fixtures"
    urls = []
    if fixtures.exists():
        for p in sorted(fixtures.glob("*.json"))[:6]:
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
                url = doc.get("url") or doc.get("source_url") or p.stem
                urls.append(str(url))
            except Exception:
                urls.append(p.stem)
    if not urls:
        urls = ["fincen.gov", "rbi.org.in", "reuters.com"]
    return {
        "run_id": "recorded-identify",
        "events": [
            {"t": 0, "verb": "COLLECT", "body": "Collect started", "status": "started"},
            {"t": 800, "verb": "COLLECT", "body": f"Source {urls[0]}", "status": "ok", "artifacts": {"urls": [urls[0]]}},
            {"t": 3000, "verb": "COLLECT", "body": f"Source {urls[1] if len(urls) > 1 else urls[0]}", "status": "ok"},
            {"t": 6000, "verb": "EXTRACT", "body": "Reading articles", "status": "ok"},
            {"t": 9000, "verb": "RANK", "body": "Ranking sources", "status": "ok"},
            {"t": 11000, "verb": "GROUND", "body": "Matching to the catalog", "status": "ok"},
            {"t": 14000, "verb": "PROPOSE", "body": "Proposing attacks for review", "status": "ok"},
            {"t": 15000, "verb": "REPLAY", "body": "Playback complete", "status": "done"},
        ],
        "candidate_urls": urls,
        "fallback": "recorded",
    }
