"""Event-driven quiet UPI-like world (Plan 08 Phase B)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from packages.sim.features import FeatureComputer, can_pay, replay_features
from packages.sim.ledger import LabelFamily, make_event, party_id
from packages.sim.priors import WorldPriors, load_priors, sample_amount_minor, sample_hour

PERSONAS = ("salaried", "kirana_shopper", "small_biz", "young_urban")

PERSONA_BUCKETS: dict[str, list[str]] = {
    "salaried": ["grocery", "utilities", "telecom", "p2p", "fuel"],
    "kirana_shopper": ["grocery", "grocery", "utilities", "p2p"],
    "small_biz": ["fuel", "telecom", "utilities", "p2p", "grocery"],
    "young_urban": ["fast_food", "telecom", "p2p", "grocery"],
}

MERCHANT_CATEGORIES = ("grocery", "fast_food", "utilities", "fuel", "telecom")


@dataclass
class Party:
    party_id: str
    kind: str
    persona: str | None
    created_ts: datetime
    device_hash: str
    kyc_tier: str
    opening_balance_minor: int
    category: str | None = None
    known_payees: list[str] = field(default_factory=list)


@dataclass
class WorldResult:
    events: list[dict[str, Any]]
    meta: dict[str, dict[str, Any]]
    customers: list[Party]
    merchants: list[Party]
    priors: WorldPriors
    world_seed: int
    sim_days: int
    t0: datetime
    computer: FeatureComputer
    seq: int

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def rebuild_features(self) -> None:
        """Sort by clock and recompute auth features from past rows only."""
        self.events.sort(key=lambda e: (e["event_ts"], e["event_id"]))
        self.events, self.computer = replay_features(self.events, self.meta)


def register_party(world: WorldResult, party: Party) -> None:
    world.meta[party.party_id] = _meta_from_party(party)
    world.computer.ensure(
        party.party_id,
        party.created_ts,
        party.device_hash,
        party.kyc_tier,
        party.opening_balance_minor,
    )


def _meta_from_party(p: Party) -> dict[str, Any]:
    return {
        "created_ts": p.created_ts,
        "device_hash": p.device_hash,
        "kyc_tier": p.kyc_tier,
        "opening_balance_minor": p.opening_balance_minor,
        "persona": p.persona,
        "kind": p.kind,
        "category": p.category,
    }


def _pick_persona(rng: np.random.Generator, priors: WorldPriors) -> str:
    names = list(priors.persona_weights.keys())
    p = np.array([priors.persona_weights[n] for n in names], dtype=np.float64)
    p = p / p.sum()
    return str(rng.choice(names, p=p))


def generate_quiet_world(
    *,
    world_seed: int = 42,
    n_customers: int = 2400,
    n_merchants: int = 120,
    sim_days: int = 90,
    priors: WorldPriors | None = None,
    t0: datetime | None = None,
) -> WorldResult:
    priors = priors or load_priors()
    rng = np.random.default_rng(world_seed)
    start = t0 or datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(days=sim_days)

    merchants: list[Party] = []
    for i in range(n_merchants):
        cat = MERCHANT_CATEGORIES[i % len(MERCHANT_CATEGORIES)]
        merchants.append(
            Party(
                party_id=party_id("M", i + 1),
                kind="merchant",
                persona=None,
                created_ts=start - timedelta(days=int(rng.integers(30, 400))),
                device_hash=f"dev-m-{i + 1:06d}",
                kyc_tier="tier2",
                opening_balance_minor=80_000_000,
                category=cat,
            )
        )
    # Legitimate high-fan-in hubs: payroll / marketplace / bill-pay. Hard negatives for mule.
    hub_specs = (("payroll", "utilities"), ("marketplace", "grocery"), ("billpay", "telecom"))
    for i, (kind, cat) in enumerate(hub_specs, start=1):
        merchants.append(
            Party(
                party_id=party_id("HUB", i),
                kind="hub",
                persona=None,
                created_ts=start - timedelta(days=int(rng.integers(200, 800))),
                device_hash=f"dev-hub-{i:06d}",
                kyc_tier="tier2",
                opening_balance_minor=500_000_000,
                category=cat,
            )
        )
    by_cat: dict[str, list[Party]] = {}
    for m in merchants:
        by_cat.setdefault(m.category or "grocery", []).append(m)

    customers: list[Party] = []
    for i in range(n_customers):
        persona = _pick_persona(rng, priors)
        known: list[str] = []
        for cat in PERSONA_BUCKETS[persona]:
            pool = by_cat.get(cat) or merchants
            known.append(pool[int(rng.integers(0, len(pool)))].party_id)
        friends = [
            party_id("C", int(rng.integers(1, max(n_customers, 2))))
            for _ in range(int(rng.integers(2, 5)))
        ]
        friends = [f for f in friends if f != party_id("C", i + 1)]
        known_list = list(dict.fromkeys(known + friends))
        if rng.random() < 0.45:
            known_list.append(party_id("HUB", int(rng.integers(1, 4))))
        customers.append(
            Party(
                party_id=party_id("C", i + 1),
                kind="customer",
                persona=persona,
                created_ts=start - timedelta(days=int(rng.integers(14, 400))),
                device_hash=f"dev-c-{i + 1:06d}",
                kyc_tier="tier2" if persona != "young_urban" else "tier1",
                opening_balance_minor=int(rng.integers(15_000_000, 40_000_000)),
                known_payees=list(dict.fromkeys(known_list)),
            )
        )

    meta: dict[str, dict[str, Any]] = {}
    for p in customers + merchants:
        meta[p.party_id] = _meta_from_party(p)

    fc = FeatureComputer()
    for pid, m in meta.items():
        fc.ensure(pid, m["created_ts"], m["device_hash"], m["kyc_tier"], m["opening_balance_minor"])

    cust_by_id = {c.party_id: c for c in customers}
    merchants_by_id = {m.party_id: m for m in merchants}
    day_spend: dict[tuple[str, str], int] = {}
    events: list[dict[str, Any]] = []
    seq = 0
    upgrade_day = {
        c.party_id: int(rng.integers(sim_days // 3, max(sim_days // 3 + 1, sim_days - 5)))
        for c in customers
        if rng.random() < 0.04
    }

    for cust in customers:
        lam = float(priors.persona_txn_per_day[cust.persona or "salaried"]) * sim_days
        n_txn = int(rng.poisson(lam))
        n_txn = max(n_txn, 1)
        buckets = PERSONA_BUCKETS[cust.persona or "salaried"]
        for _ in range(n_txn):
            day = int(rng.integers(0, sim_days))
            hour = sample_hour(rng, priors)
            minute = int(rng.integers(0, 60))
            ts = start + timedelta(days=day, hours=hour, minutes=minute)
            if ts < start or ts >= end:
                continue
            if ts < cust.created_ts:
                continue
            p2m = rng.random() < priors.p2m_share
            if p2m and cust.known_payees:
                if rng.random() < 0.08:
                    hubs = [p for p in cust.known_payees if p.startswith("VID-SIM-HUB-")]
                    payee = hubs[int(rng.integers(0, len(hubs)))] if hubs else None
                    if payee is None:
                        merch_ids = [p for p in cust.known_payees if p.startswith("VID-SIM-M-")]
                        payee = merch_ids[int(rng.integers(0, len(merch_ids)))] if merch_ids else cust.known_payees[0]
                else:
                    merch_ids = [p for p in cust.known_payees if p.startswith(("VID-SIM-M-", "VID-SIM-HUB-"))]
                    payee = merch_ids[int(rng.integers(0, len(merch_ids)))] if merch_ids else cust.known_payees[0]
            else:
                p2p = [p for p in cust.known_payees if p.startswith("VID-SIM-C-") and p in cust_by_id]
                payee = p2p[int(rng.integers(0, len(p2p)))] if p2p else merchants[0].party_id
            if payee not in meta:
                continue
            if payee.startswith("VID-SIM-M-") or payee.startswith("VID-SIM-HUB-"):
                merch = merchants_by_id.get(payee)
                cat = (merch.category if merch else None) or "grocery"
            else:
                cat = "p2p"
            amount = sample_amount_minor(rng, priors, cat)
            # Hubs keep the category prior (utilities/grocery/telecom). Ticket-size
            # must stay in the PSI envelope; mule hard-negatives are fan-in, not rupees.
            day_key = (cust.party_id, ts.date().isoformat())
            spent = day_spend.get(day_key, 0)
            if spent + amount > priors.caps.day_max_minor:
                continue
            reason = can_pay(fc, cust.party_id, ts, amount)
            if reason:
                continue
            seq += 1
            device = cust.device_hash
            if cust.party_id in upgrade_day and day >= upgrade_day[cust.party_id]:
                device = f"dev-c-up-{cust.party_id[-6:]}"
            app_flags = None
            payload = None
            # Genuine session-stamp noise (S2): low-level APP-shaped signals on normal rows.
            if rng.random() < 0.02:
                app_flags = {
                    "call_active_flag": bool(rng.random() < 0.15),
                    "copy_paste_payee_flag": bool(rng.random() < 0.25),
                    "pause_ms": int(rng.integers(0, 800)),
                    "urgency_pressure": float(rng.uniform(0.0, 0.35)),
                }
            elif rng.random() < 0.004:
                app_flags = {
                    "call_active_flag": False,
                    "copy_paste_payee_flag": True,
                    "pause_ms": int(rng.integers(200, 1200)),
                    "urgency_pressure": 0.0,
                }
            if cust.persona == "small_biz" and rng.random() < 0.006:
                payload = {
                    "beneficiary_changed": True,
                    "gstin_checksum_ok": True,
                    "lookalike_domain_flag": False,
                }
            feats = fc.snapshot_and_apply(
                ts=ts,
                payer=cust.party_id,
                payee=payee,
                amount_minor=amount,
                device_hash=device,
                app_flags=app_flags,
                liveness_score=None,
                doc_consistency=None,
                debit=True,
            )
            feats.pop("_insufficient_float", None)
            events.append(
                make_event(
                    seq=seq,
                    ts=ts,
                    rail="upi_like",
                    payer=cust.party_id,
                    payee=payee,
                    amount_minor=amount,
                    label_family="normal",
                    features_auth=feats,
                    economic_class=None,
                    payload=payload,
                    kyc_tier=cust.kyc_tier,
                )
            )
            day_spend[day_key] = spent + amount

    world = WorldResult(
        events=events,
        meta=meta,
        customers=customers,
        merchants=merchants,
        priors=priors,
        world_seed=world_seed,
        sim_days=sim_days,
        t0=start,
        computer=fc,
        seq=seq,
    )
    world.rebuild_features()
    return world


def append_event(
    world: WorldResult,
    *,
    ts: datetime,
    payer: str,
    payee: str,
    amount_minor: int,
    label_family: LabelFamily,
    rail: str = "upi_like",
    device_hash: str | None = None,
    app_flags: dict[str, Any] | None = None,
    liveness_score: float | None = None,
    doc_consistency: float | None = None,
    economic_class: str | None = None,
    payload: dict[str, Any] | None = None,
    debit: bool = True,
) -> dict[str, Any] | None:
    reason = can_pay(world.computer, payer, ts, amount_minor)
    if reason and debit:
        return None
    payer_dev = device_hash or world.computer.accounts[payer].device_hash
    feats = world.computer.snapshot_and_apply(
        ts=ts,
        payer=payer,
        payee=payee,
        amount_minor=amount_minor,
        device_hash=payer_dev,
        app_flags=app_flags,
        liveness_score=liveness_score,
        doc_consistency=doc_consistency,
        debit=debit,
    )
    if feats.pop("_insufficient_float", None) and debit:
        return None
    seq = world.next_seq()
    ev = make_event(
        seq=seq,
        ts=ts,
        rail=rail,
        payer=payer,
        payee=payee,
        amount_minor=amount_minor,
        label_family=label_family,
        features_auth=feats,
        economic_class=economic_class,
        payload=payload,
        kyc_tier=world.computer.accounts[payer].kyc_tier,
    )
    world.events.append(ev)
    return ev
