"""doc_beneficiary — checksum often passes; stamps are not a 3-bit label."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from packages.sim.inject.gstin import gstin_checksum_ok, make_valid_gstin
from packages.sim.inject.jitter import clamp_ts
from packages.sim.ledger import party_id
from packages.sim.world import Party, WorldResult, append_event, register_party


def inject_invoices(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    n_invoices: int,
) -> list[dict]:
    biz = [c for c in world.customers if c.persona == "small_biz"] or world.customers
    written = []
    start_day = min(8, max(2, world.sim_days // 6))
    for i in range(max(1, n_invoices)):
        bene_n = 1 + (i % 4)
        wrong = Party(
            party_id=party_id("BENE", bene_n),
            kind="lookalike",
            persona=None,
            created_ts=world.t0,
            device_hash=f"dev-bene-{bene_n:06d}",
            kyc_tier="tier2",
            opening_balance_minor=1_000_000,
        )
        if wrong.party_id not in world.meta:
            register_party(world, wrong)
        payer = biz[i % len(biz)]
        gstin = make_valid_gstin(1000 + i)
        assert gstin_checksum_ok(gstin)
        variant = ("full_stamp", "checksum_only", "change_only", "gradual")[i % 4]
        if variant == "full_stamp":
            payload = {
                "beneficiary_changed": True,
                "gstin_checksum_ok": True,
                "gstin": gstin,
                "lookalike_domain_flag": True,
            }
            amount = int(rng.integers(200_000, 900_000))
        elif variant == "checksum_only":
            payload = {
                "beneficiary_changed": False,
                "gstin_checksum_ok": True,
                "gstin": gstin,
                "lookalike_domain_flag": False,
            }
            amount = int(rng.integers(150_000, 600_000))
        elif variant == "change_only":
            payload = {
                "beneficiary_changed": True,
                "gstin_checksum_ok": False,
                "gstin": gstin,
                "lookalike_domain_flag": True,
            }
            amount = int(rng.integers(80_000, 400_000))
        else:
            payload = {
                "beneficiary_changed": True,
                "gstin_checksum_ok": True,
                "gstin": gstin,
                "lookalike_domain_flag": False,
            }
            amount = int(rng.integers(50_000, 250_000))
        day = start_day + int(rng.integers(0, max(1, world.sim_days - start_day - 2)))
        ts = clamp_ts(world.t0 + timedelta(days=day, hours=int(rng.integers(9, 17))), world.t0, world.sim_days)
        ev = append_event(
            world,
            ts=ts,
            payer=payer.party_id,
            payee=wrong.party_id,
            amount_minor=amount,
            label_family="invoice_fraud",
            economic_class="BEC",
            payload=payload,
        )
        if ev:
            written.append(ev)
    return written
