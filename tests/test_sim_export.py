"""Phase E — population / canary / train parquet (Plan 08 lock 5 items 1–10)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from packages.sim.export import TRAIN_ALLOWLIST, TRAIN_DENYLIST, assert_split_schema, assert_train_schema
from packages.sim.inject.mix import apply_mix
from packages.sim.ledger import TECHNIQUE_IDS
from packages.sim.runner import run_canary, run_population
from packages.sim.world import generate_quiet_world


@pytest.fixture()
def runs(tmp_path: Path) -> Path:
    return tmp_path / "runs"


def test_population_t13_filter_many_app_victims():
    world = generate_quiet_world(world_seed=42, n_customers=28, n_merchants=8, sim_days=40)
    apply_mix(world, np.random.default_rng(43), pin=True, families=frozenset({"app_fraud"}))
    families = {e["label_family"] for e in world.events}
    assert "normal" in families
    assert "app_fraud" in families
    assert families <= {"normal", "app_fraud"}
    apps = [e for e in world.events if e["label_family"] == "app_fraud"]
    victims = {e["party_ids"]["payer"] for e in apps}
    assert len(apps) >= 3
    assert len(victims) >= 3


def test_population_full_mix_parquet_and_seasoning(runs: Path):
    result = run_population(
        None,
        run_id="pop-full",
        n_customers=24,
        n_merchants=8,
        sim_days=90,
        world_seed=42,
        runs_dir=runs,
        pin=True,
    )
    assert result["mode"] == "population"
    assert result["event_count"] > 1
    assert "simulatable_signals" not in result
    assert_train_schema(result["parquet_path"])
    assert_split_schema(result["split_path"])
    df = pd.read_parquet(result["parquet_path"])
    split = pd.read_parquet(result["split_path"])
    assert len(df) == len(split)
    assert "event_ts" in split.columns
    assert "payer" in split.columns and "payee" in split.columns
    assert "event_ts" not in df.columns
    assert set(df.columns) <= set(TRAIN_ALLOWLIST)
    for banned in TRAIN_DENYLIST:
        assert banned not in df.columns
    for fam in df["label_family"].unique():
        assert fam not in TECHNIQUE_IDS
    assert result["seasoning_clamped"] is True
    assert result["seasoning_days_effective"] == 90 - 14
    assert result["fidelity"]["pass"] is True, result["fidelity"]
    families = set(df["label_family"].unique())
    for needed in ("normal", "mule", "identity_burst", "ato", "app_fraud", "invoice_fraud"):
        assert needed in families
    apps = df["label_family"] == "app_fraud"
    assert apps.sum() >= 3
    assert (df.loc[~apps, "call_active_flag"] == False).all()
    assert (df.loc[apps, "call_active_flag"] == True).all()
    assert "is_authorized_push" not in df.columns
    sidecar = Path(result["sidecar_path"]).read_text(encoding="utf-8")
    assert "technique_id" in sidecar or '"knobs_used"' in sidecar
    assert "fan_in_1h" in sidecar


def test_canary_shared_chain_180d_pinned(runs: Path):
    result = run_canary(
        None,
        campaign_id="fincen-fin-2024-alert004",
        run_id="canary-chain",
        n_customers=12,
        n_merchants=6,
        sim_days=180,
        world_seed=42,
        runs_dir=runs,
    )
    assert result["mode"] == "canary"
    assert result["sim_days"] == 180
    assert result["seasoning_clamped"] is False
    assert result["seasoning_days_effective"] == 150
    stages = result["lifecycle_stages_logged"]
    assert [s["lifecycle_stage"] for s in stages] == [
        "onboarding_kyc",
        "account_access_ato",
        "payment_initiation",
        "disbursement_mule",
    ]
    ids = {s["party_id"] for s in stages}
    assert len(ids) == 1
    assert next(iter(ids)).startswith("VID-SIM-CHAIN-")
    assert "simulatable_signals" not in result
    assert result["event_count"] > 4
    assert_train_schema(result["parquet_path"])
    assert '"pinned_liveness": 0.35' in Path(result["sidecar_path"]).read_text(encoding="utf-8")
