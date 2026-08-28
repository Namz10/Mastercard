"""gff.txn.v1 helpers (Plan 08 envelope)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

SCHEMA = "gff.txn.v1"
VID_PREFIX = "VID-SIM"
CURRENCY = "INR"

LabelFamily = Literal[
    "normal",
    "mule",
    "identity_burst",
    "ato",
    "app_fraud",
    "invoice_fraud",
]

LABEL_FAMILIES = frozenset(
    {"normal", "mule", "identity_burst", "ato", "app_fraud", "invoice_fraud"}
)
TECHNIQUE_IDS = frozenset({f"T{i:02d}" for i in range(1, 25)})


def party_id(kind: str, n: int) -> str:
    return f"{VID_PREFIX}-{kind}-{n:06d}"


def event_id(n: int) -> str:
    return f"evt-{n:010d}"


def iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()


def empty_app_flags() -> dict[str, Any]:
    return {
        "call_active_flag": False,
        "copy_paste_payee_flag": False,
        "pause_ms": 0,
        "urgency_pressure": 0.0,
    }


def make_event(
    *,
    seq: int,
    ts: datetime,
    rail: str,
    payer: str,
    payee: str,
    amount_minor: int,
    label_family: LabelFamily,
    features_auth: dict[str, Any],
    economic_class: str | None = None,
    payload: dict[str, Any] | None = None,
    kyc_tier: str | None = None,
) -> dict[str, Any]:
    if label_family in TECHNIQUE_IDS:
        raise ValueError("label_family must not be a technique id")
    if label_family not in LABEL_FAMILIES:
        raise ValueError(f"unknown label_family {label_family}")
    env: dict[str, Any] = {
        "schema": SCHEMA,
        "event_id": event_id(seq),
        "event_ts": iso(ts),
        "rail": rail,
        "party_ids": {"payer": payer, "payee": payee},
        "amount_minor": int(amount_minor),
        "currency": CURRENCY,
        "label_family": label_family,
        "label_ts": iso(ts),
        "economic_class": economic_class,
        "features_auth": features_auth,
    }
    if kyc_tier is not None:
        env["kyc_tier"] = kyc_tier
    if payload:
        env["payload"] = payload
    return env
