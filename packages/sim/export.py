"""Train Parquet allowlist + sidecar (Plan 08 Phase E)."""

from __future__ import annotations

import json
import os
import time
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
    "fan_in_unique_payers_1h",
    "is_new_payee",
    "is_new_device",
    "burst_velocity",
    "fan_in_24h",
    "fan_out_24h",
    "fan_in_unique_payers_24h",
    "txn_velocity_24h",
    "hours_since_prev_txn",
    "hours_since_payee",
    "amount_vs_7d_mean",
    "unique_payees_7d",
    "payee_fan_out_1h",
    "in_out_asymmetry_24h",
    "call_active_flag",
    "copy_paste_payee_flag",
    "pause_ms",
    "urgency_pressure",
    "beneficiary_changed",
    "gstin_checksum_ok",
    "lookalike_domain_flag",
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
    "campaign_id",
)


def train_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ev in events:
        fa = ev.get("features_auth") or {}
        row = {
            "rail": ev["rail"],
            "kyc_tier": ev.get("kyc_tier") or fa.get("kyc_tier"),
            "account_age_days": fa.get("account_age_days"),
            "payee_history_count": fa.get("payee_history_count"),
            "amount_vs_p30": fa.get("amount_vs_p30"),
            "fan_in_1h": fa.get("fan_in_1h"),
            "fan_out_1h": fa.get("fan_out_1h"),
            "fan_in_unique_payers_1h": fa.get("fan_in_unique_payers_1h", 0),
            "is_new_payee": fa.get("is_new_payee"),
            "is_new_device": fa.get("is_new_device"),
            "burst_velocity": fa.get("burst_velocity"),
            "fan_in_24h": fa.get("fan_in_24h", 0),
            "fan_out_24h": fa.get("fan_out_24h", 0),
            "fan_in_unique_payers_24h": fa.get("fan_in_unique_payers_24h", 0),
            "txn_velocity_24h": fa.get("txn_velocity_24h", 0),
            "hours_since_prev_txn": fa.get("hours_since_prev_txn", 168.0),
            "hours_since_payee": fa.get("hours_since_payee", 720.0),
            "amount_vs_7d_mean": fa.get("amount_vs_7d_mean", 1.0),
            "unique_payees_7d": fa.get("unique_payees_7d", 0),
            "payee_fan_out_1h": fa.get("payee_fan_out_1h", 0),
            "in_out_asymmetry_24h": fa.get("in_out_asymmetry_24h", 0),
            "call_active_flag": bool(fa.get("call_active_flag")),
            "copy_paste_payee_flag": bool(fa.get("copy_paste_payee_flag")),
            "pause_ms": int(fa.get("pause_ms") or 0),
            "urgency_pressure": float(fa.get("urgency_pressure") or 0.0),
            "beneficiary_changed": bool(fa.get("beneficiary_changed", False)),
            "gstin_checksum_ok": bool(fa.get("gstin_checksum_ok", False)),
            "lookalike_domain_flag": bool(fa.get("lookalike_domain_flag", False)),
            "label_family": ev["label_family"],
        }
        rows.append(row)
    if rows:
        assert_train_schema(rows[0].keys())
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
                "campaign_id": ev.get("campaign_id"),
            }
        )
    return rows


def export_run(
    events: list[dict[str, Any]],
    sidecar: dict[str, Any],
    run_id: str,
    runs_dir: Path | None = None,
) -> dict[str, str]:
    t0 = time.perf_counter()
    dest = runs_dir or RUNS_DIR
    dest.mkdir(parents=True, exist_ok=True)
    folder = dest / run_id
    folder.mkdir(parents=True, exist_ok=True)
    tmp_folder = folder / ".tmp"
    tmp_folder.mkdir(parents=True, exist_ok=True)

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

    tmp_parquet = tmp_folder / "train.parquet"
    tmp_split = tmp_folder / "split.parquet"
    tmp_sidecar = tmp_folder / "sidecar.json"
    tmp_manifest = tmp_folder / "manifest.json"

    df.to_parquet(tmp_parquet, index=False)
    sdf.to_parquet(tmp_split, index=False)
    tmp_sidecar.write_text(json.dumps(sidecar, indent=2, default=str), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "world_seed": sidecar.get("world_seed"),
        "n_customers": sidecar.get("n_customers"),
        "n_merchants": sidecar.get("n_merchants"),
        "sim_days": sidecar.get("sim_days"),
        "recipe_hash": sidecar.get("recipe_hash"),
        "wall_clock_seconds": round(time.perf_counter() - t0, 3),
        "row_count": len(df),
    }
    tmp_manifest.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    parquet_path = folder / "train.parquet"
    split_path = folder / "split.parquet"
    sidecar_path = folder / "sidecar.json"
    manifest_path = folder / "manifest.json"
    done_path = folder / "_DONE"

    os.replace(tmp_parquet, parquet_path)
    os.replace(tmp_split, split_path)
    os.replace(tmp_sidecar, sidecar_path)
    os.replace(tmp_manifest, manifest_path)

    try:
        tmp_folder.rmdir()
    except OSError:
        pass

    done_path.write_text("DONE\n", encoding="utf-8")

    return {
        "parquet_path": str(parquet_path),
        "split_path": str(split_path),
        "sidecar_path": str(sidecar_path),
        "manifest_path": str(manifest_path),
        "done_path": str(done_path),
    }


def assert_train_schema(parquet_path_or_cols: str | Path | list[str] | set[str] | Any) -> None:
    if isinstance(parquet_path_or_cols, (str, Path)):
        df = pd.read_parquet(parquet_path_or_cols)
        cols = set(df.columns)
    else:
        cols = set(parquet_path_or_cols)

    allowed = set(TRAIN_ALLOWLIST)
    denied = set(TRAIN_DENYLIST)

    leaked = cols & denied
    if leaked:
        raise ValueError(f"Denied columns in train frame: {leaked}")

    extra = cols - allowed - {c for c in cols if str(c).startswith("rule__")}
    if extra:
        raise ValueError(f"Columns not on TRAIN_ALLOWLIST: {extra}")

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

