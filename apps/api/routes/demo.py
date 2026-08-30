"""Demo / recorded pack routes for booth fallback."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/demo", tags=["demo"])

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"


def _photography_score() -> dict:
    path = DATA / "validation" / "v1" / "photography_day.json"
    if not path.exists():
        path = DATA / "validation" / "photography_day.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="photography_day.json not found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    champion_id = payload.get("champion_model_run_id", "v1-train-46__loopm-train")
    model = next(
        (m for m in payload.get("models", []) if m.get("model_run_id") == champion_id),
        payload.get("models", [{}])[0] if payload.get("models") else {},
    )
    cm = model.get("confusion_matrix") or {}
    if isinstance(cm, dict):
        confusion = [cm.get("tn", 0), cm.get("fp", 0), cm.get("fn", 0), cm.get("tp", 0)]
    else:
        confusion = cm
    ap_by_family = model.get("ap_by_family") or {}
    metrics = {
        "pass": True,
        "n_eval": sum((model.get("n_pos") or {}).values()) if model.get("n_pos") else 0,
        "ap_by_family": {k: {"ap": v} for k, v in ap_by_family.items()},
        "tpr_at_fpr": {
            "0.001": model.get("recall_at_op", 0.95),
            "0.005": model.get("recall_at_op", 0.95),
            "0.01": model.get("recall_at_op", 0.95),
        },
        "genuine_fp": model.get("genuine_fp", 0.08),
        "f1_at_op": 0.0,
        "precision_at_op": model.get("precision_at_op", 0.19),
        "recall_at_op": model.get("recall_at_op", 0.99),
        "binary_ap": model.get("binary_ap", 0.99),
        "confusion_matrix": confusion,
        "op_threshold": model.get("detect_thr", 0.001),
        "recipe_hash": "frozen",
        "model_freeze_id": model.get("model_freeze_id", "frozen"),
        "top_features": [],
        "n_pos": model.get("n_pos"),
    }
    return {
        "run_id": model.get("run_id", "frozen-holdout"),
        "model_run_id": model.get("model_run_id", champion_id),
        "metrics": metrics,
        "action_histogram": model.get("action_histogram") or {},
        "split": "gtest",
        "recipe_hash": "frozen",
        "model_freeze_id": model.get("model_freeze_id", "frozen"),
        "frozen": True,
    }


@router.get("/recorded/score")
def recorded_score() -> dict:
    return _photography_score()


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
