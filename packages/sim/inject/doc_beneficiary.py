"""doc_beneficiary — checksum passes, wrong account."""

from __future__ import annotations

from datetime import timedelta

import numpy as np

from packages.sim.inject.gstin import gstin_checksum_ok, make_valid_gstin
from packages.sim.ledger import party_id
from packages.sim.world import Party, WorldResult, append_event, register_party


def inject_invoices(
    world: WorldResult,
    rng: np.random.Generator,
    *,
    n_invoices: int,
) -> list[dict]:
    biz = [c for c in world.customers if c.persona == "small_biz"] or world.customers
    wrong = Party(
        party_id=party_id("BENE", 1),
        kind="lookalike",
        persona=None,
        created_ts=world.t0,
        device_hash="dev-bene-000001",
        kyc_tier="tier2",
        opening_balance_minor=1_000_000,
    )
    if wrong.party_id not in world.meta:
        register_party(world, wrong)
    written = []
    start = world.t0 + timedelta(days=min(20, max(1, world.sim_days // 3)))
    for i in range(max(1, n_invoices)):
        payer = biz[i % len(biz)]
        gstin = make_valid_gstin(1000 + i)
        assert gstin_checksum_ok(gstin)
        amount = int(rng.integers(200_000, 900_000))
        ev = append_event(
            world,
            ts=start + timedelta(hours=i * 3),
            payer=payer.party_id,
            payee=wrong.party_id,
            amount_minor=amount,
            label_family="invoice_fraud",
            economic_class="BEC",
            payload={
                "beneficiary_changed": True,
                "gstin_checksum_ok": True,
                "gstin": gstin,
                "lookalike_domain_flag": True,
            },
        )
        if ev:
            written.append(ev)
    return written
