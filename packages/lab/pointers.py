"""Durable last-run pointers for Command Center. Fail-soft — never raise to callers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[2]
LAB_STATE_DIR = _ROOT / "data" / "lab"
LAST_IDENTIFY = LAB_STATE_DIR / "last_identify.json"
LAST_SCORE = LAB_STATE_DIR / "last_score.json"
LAST_LOOP_M = LAB_STATE_DIR / "last_loop_m.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        LAB_STATE_DIR.mkdir(parents=True, exist_ok=True)
        body = {**payload, "saved_at": _now()}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def save_identify(payload: dict[str, Any]) -> None:
    write_json(LAST_IDENTIFY, payload)


def save_score(payload: dict[str, Any]) -> None:
    write_json(LAST_SCORE, payload)


def save_loop_m(payload: dict[str, Any]) -> None:
    write_json(LAST_LOOP_M, payload)


def load_identify() -> dict[str, Any] | None:
    return read_json(LAST_IDENTIFY)


def load_score() -> dict[str, Any] | None:
    return read_json(LAST_SCORE)


def load_loop_m() -> dict[str, Any] | None:
    return read_json(LAST_LOOP_M)
