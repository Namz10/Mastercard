"""Train Parquet allowlist + sidecar (Plan 08 Phase E)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = _ROOT / "data" / "runs"

TRAIN_ALLOWLIST = (
    "rail",
    "kyc_tier",
    "account_age_days",
    "payee_history_count",
    "amount_vs_p30",
    "fan_in_1h",
    "fan_out_1h",
    "is_new_payee",
    "is_new_device",
    "burst_velocity",
    "call_active_flag",
    "copy_paste_payee_flag",
    "pause_ms",
    "urgency_pressure",
    "label_family",
)

TRAIN_DENYLIST = (
    "vector_id",
    "injector_id",
    "technique_id",
    "simulatable_signals",
    "persona_type",
    "world_seed",
    "transcripts",
    "is_authorized_push",
    "economic_class",
    "label_class",
    "gstin",
    "payload",
)

# Eval join only — never concatenated into model X (Plan 12 Lock 1).
SPLIT_COLUMNS = (
    "event_id",
    "event_ts",
    "payer",
    "payee",
    "amount_minor",
    "label_family",
)


def train_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in events:
        fa = ev.get("features_auth") or {}
        is_app = ev["label_family"] == "app_fraud"
        row = {
            "rail": ev["rail"],
            "kyc_tier": ev.get("kyc_tier") or fa.get("kyc_tier"),
            "account_age_days": fa.get("account_age_days"),
            "payee_history_count": fa.get("payee_history_count"),
            "amount_vs_p30": fa.get("amount_vs_p30"),
            "fan_in_1h": fa.get("fan_in_1h"),
            "fan_out_1h": fa.get("fan_out_1h"),
            "is_new_payee": fa.get("is_new_payee"),
            "is_new_device": fa.get("is_new_device"),
            "burst_velocity": fa.get("burst_velocity"),
            "call_active_flag": bool(fa.get("call_active_flag")) if is_app else False,
            "copy_paste_payee_flag": bool(fa.get("copy_paste_payee_flag")) if is_app else False,
            "pause_ms": int(fa.get("pause_ms") or 0) if is_app else 0,
            "urgency_pressure": float(fa.get("urgency_pressure") or 0.0) if is_app else 0.0,
            "label_family": ev["label_family"],
        }
        rows.append(row)
    return rows


def split_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in events:
        parties = ev.get("party_ids") or {}
        rows.append(
            {
                "event_id": ev["event_id"],
                "event_ts": ev["event_ts"],
                "payer": parties["payer"],
                "payee": parties["payee"],
                "amount_minor": int(ev["amount_minor"]),
                "label_family": ev["label_family"],
            }
        )
    return rows


def export_run(
    events: list[dict[str, Any]],
    sidecar: dict[str, Any],
    run_id: str,
    runs_dir: Path | None = None,
) -> dict[str, str]:
    dest = runs_dir or RUNS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    folder = dest / run_id
    folder.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(train_rows(events))
    extra = [c for c in df.columns if c not in TRAIN_ALLOWLIST]
    if extra:
        raise ValueError(f"train columns not in allowlist: {extra}")
    sdf = pd.DataFrame(split_rows(events))
    split_extra = [c for c in sdf.columns if c not in SPLIT_COLUMNS]
    if split_extra:
        raise ValueError(f"split columns not in schema: {split_extra}")
    if len(df) != len(sdf):
        raise ValueError("train/split row count mismatch")
    parquet_path = folder / "train.parquet"
    split_path = folder / "split.parquet"
    sidecar_path = folder / "sidecar.json"
    df.to_parquet(parquet_path, index=False)
    sdf.to_parquet(split_path, index=False)
    sidecar_path.write_text(json.dumps(sidecar, indent=2, default=str), encoding="utf-8")
    return {
        "parquet_path": str(parquet_path),
        "split_path": str(split_path),
        "sidecar_path": str(sidecar_path),
    }


def assert_train_schema(parquet_path: str | Path) -> None:
    df = pd.read_parquet(parquet_path)
    cols = set(df.columns)
    if not cols.issubset(TRAIN_ALLOWLIST):
        raise AssertionError(f"unexpected train cols: {cols - set(TRAIN_ALLOWLIST)}")
    for banned in TRAIN_DENYLIST:
        if banned in cols:
            raise AssertionError(f"denylist column present: {banned}")
    for leak in ("event_ts", "event_id", "payer", "payee"):
        if leak in cols:
            raise AssertionError(f"split-only column leaked into train: {leak}")


def assert_split_schema(split_path: str | Path) -> None:
    df = pd.read_parquet(split_path)
    cols = set(df.columns)
    if cols != set(SPLIT_COLUMNS):
        raise AssertionError(f"split schema mismatch: {cols} vs {set(SPLIT_COLUMNS)}")
    for banned in TRAIN_DENYLIST:
        if banned in cols:
            raise AssertionError(f"denylist column present on split: {banned}")
