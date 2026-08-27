"""Causal O(n) running features — past rows only (Plan 08 Phase B)."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any

from packages.sim.ledger import empty_app_flags

HOUR = timedelta(hours=1)
P30 = timedelta(days=30)


def parse_ts(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


class AccountRuntime:
    __slots__ = (
        "created_ts",
        "device_hash",
        "kyc_tier",
        "balance_minor",
        "payee_count",
        "inbound_ts",
        "outbound_ts",
        "amount_history",
        "txn_count",
    )

    def __init__(
        self,
        created_ts: datetime,
        device_hash: str,
        kyc_tier: str,
        balance_minor: int,
    ) -> None:
        self.created_ts = created_ts
        self.device_hash = device_hash
        self.kyc_tier = kyc_tier
        self.balance_minor = balance_minor
        self.payee_count: dict[str, int] = defaultdict(int)
        self.inbound_ts: deque[datetime] = deque()
        self.outbound_ts: deque[datetime] = deque()
        self.amount_history: deque[tuple[datetime, int]] = deque()
        self.txn_count = 0

    def prune(self, now: datetime) -> None:
        cutoff_h = now - HOUR
        while self.inbound_ts and self.inbound_ts[0] < cutoff_h:
            self.inbound_ts.popleft()
        while self.outbound_ts and self.outbound_ts[0] < cutoff_h:
            self.outbound_ts.popleft()
        cutoff_30 = now - P30
        while self.amount_history and self.amount_history[0][0] < cutoff_30:
            self.amount_history.popleft()


class FeatureComputer:
    """One pass over time-ordered events. updates == n_events (not n^2)."""

    def __init__(self) -> None:
        self.accounts: dict[str, AccountRuntime] = {}
        self.updates = 0

    def ensure(
        self,
        party_id: str,
        created_ts: datetime,
        device_hash: str,
        kyc_tier: str,
        opening_balance_minor: int,
    ) -> AccountRuntime:
        acc = self.accounts.get(party_id)
        if acc is None:
            acc = AccountRuntime(created_ts, device_hash, kyc_tier, opening_balance_minor)
            self.accounts[party_id] = acc
        return acc

    def snapshot_and_apply(
        self,
        *,
        ts: datetime,
        payer: str,
        payee: str,
        amount_minor: int,
        device_hash: str,
        app_flags: dict[str, Any] | None = None,
        liveness_score: float | None = None,
        doc_consistency: float | None = None,
        debit: bool = True,
    ) -> dict[str, Any]:
        self.updates += 1
        payer_acc = self.accounts[payer]
        payee_acc = self.accounts[payee]
        payer_acc.prune(ts)
        payee_acc.prune(ts)

        age_days = max(0, (ts - payer_acc.created_ts).days)
        history = payer_acc.payee_count[payee]
        is_new_payee = history == 0
        p30_vals = [a for _, a in payer_acc.amount_history]
        p30_mean = (sum(p30_vals) / len(p30_vals)) if p30_vals else None
        amount_vs_p30 = (amount_minor / p30_mean) if p30_mean and p30_mean > 0 else 1.0
        fan_in_1h = len(payee_acc.inbound_ts)
        fan_out_1h = len(payer_acc.outbound_ts)
        is_new_device = device_hash != payer_acc.device_hash
        burst_velocity = float(fan_out_1h)

        flags = empty_app_flags() if app_flags is None else {**empty_app_flags(), **app_flags}

        features: dict[str, Any] = {
            "account_age_days": age_days,
            "payee_history_count": history,
            "amount_vs_p30": round(amount_vs_p30, 4),
            "fan_in_1h": fan_in_1h,
            "fan_out_1h": fan_out_1h,
            "is_new_payee": is_new_payee,
            "is_new_device": is_new_device,
            "burst_velocity": burst_velocity,
            "kyc_tier": payer_acc.kyc_tier,
            "device_hash": device_hash,
            "liveness_score": liveness_score,
            "doc_consistency": doc_consistency,
            **flags,
        }

        if debit:
            if amount_minor > payer_acc.balance_minor:
                features["_insufficient_float"] = True
            else:
                payer_acc.balance_minor -= amount_minor
                payee_acc.balance_minor += amount_minor
        payer_acc.payee_count[payee] += 1
        payer_acc.outbound_ts.append(ts)
        payer_acc.amount_history.append((ts, amount_minor))
        payer_acc.txn_count += 1
        payee_acc.inbound_ts.append(ts)
        payee_acc.txn_count += 1
        if is_new_device:
            payer_acc.device_hash = device_hash
        return features


def can_pay(computer: FeatureComputer, payer: str, ts: datetime, amount_minor: int) -> str | None:
    acc = computer.accounts.get(payer)
    if acc is None:
        return "unknown_payer"
    if ts < acc.created_ts:
        return "use_before_create"
    if amount_minor <= 0:
        return "non_positive_amount"
    if amount_minor > acc.balance_minor:
        return "insufficient_float"
    return None


def replay_features(
    events: list[dict[str, Any]],
    meta: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], FeatureComputer]:
    """Time-ordered causal replay. Returns events plus the computer at end-of-ledger."""
    ordered = sorted(events, key=lambda e: (e["event_ts"], e["event_id"]))
    fc = FeatureComputer()
    for pid, m in meta.items():
        created = m["created_ts"]
        if isinstance(created, str):
            created = parse_ts(created)
        fc.ensure(pid, created, m["device_hash"], m["kyc_tier"], int(m["opening_balance_minor"]))

    out: list[dict[str, Any]] = []
    for ev in ordered:
        ts = parse_ts(ev["event_ts"])
        payer = ev["party_ids"]["payer"]
        payee = ev["party_ids"]["payee"]
        for pid in (payer, payee):
            if pid not in fc.accounts:
                m = meta.get(pid) or {
                    "created_ts": ts,
                    "device_hash": f"dev-{pid[-6:]}",
                    "kyc_tier": "tier2",
                    "opening_balance_minor": 50_000_000,
                }
                created = m["created_ts"]
                if isinstance(created, str):
                    created = parse_ts(created)
                fc.ensure(pid, created, m["device_hash"], m["kyc_tier"], int(m["opening_balance_minor"]))
        fa = ev.get("features_auth") or {}
        flags = {
            "call_active_flag": fa.get("call_active_flag", False),
            "copy_paste_payee_flag": fa.get("copy_paste_payee_flag", False),
            "pause_ms": fa.get("pause_ms", 0),
            "urgency_pressure": fa.get("urgency_pressure", 0.0),
        }
        computed = fc.snapshot_and_apply(
            ts=ts,
            payer=payer,
            payee=payee,
            amount_minor=int(ev["amount_minor"]),
            device_hash=str(fa.get("device_hash") or fc.accounts[payer].device_hash),
            app_flags=flags if ev.get("label_family") == "app_fraud" else empty_app_flags(),
            liveness_score=fa.get("liveness_score"),
            doc_consistency=fa.get("doc_consistency"),
            debit=True,
        )
        computed.pop("_insufficient_float", None)
        new_ev = dict(ev)
        new_ev["features_auth"] = computed
        new_ev["kyc_tier"] = computed["kyc_tier"]
        out.append(new_ev)
    return out, fc


def featurize_events(
    events: list[dict[str, Any]],
    meta: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Recompute features_auth in time order. meta[party] has created_ts, device_hash, kyc_tier, opening_balance_minor."""
    replayed, _fc = replay_features(events, meta)
    return replayed
