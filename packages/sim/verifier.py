"""Ledger invariants (Plan 08 Phase D)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from packages.sim.features import parse_ts


def reject_reason(
    *,
    amount_minor: int,
    event_ts: datetime,
    payer_created: datetime | None,
) -> str | None:
    if amount_minor <= 0:
        return "non_positive_amount"
    if payer_created is not None and event_ts < payer_created:
        return "use_before_create"
    return None


def verify_events(
    events: list[dict[str, Any]],
    meta: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Scan posted events. Reject-rate flood is >20% of rows failing invariants."""
    n = len(events)
    bad: list[str] = []
    for ev in events:
        ts = parse_ts(ev["event_ts"])
        payer = ev["party_ids"]["payer"]
        created = meta.get(payer, {}).get("created_ts")
        if isinstance(created, str):
            created = parse_ts(created)
        reason = reject_reason(
            amount_minor=int(ev["amount_minor"]),
            event_ts=ts,
            payer_created=created,
        )
        if reason:
            bad.append(reason)
    rate = (len(bad) / n) if n else 0.0
    flood = rate > 0.20
    return {
        "n": n,
        "n_reject": len(bad),
        "reject_rate": rate,
        "flood": flood,
        "reasons": bad[:20],
        "pass": not flood and all(int(e["amount_minor"]) > 0 for e in events),
    }
