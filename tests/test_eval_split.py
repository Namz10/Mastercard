"""Plan 12 Phase A — split artifact, time+entity fold, X leak guards."""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from packages.eval.split import (
    LeakError,
    assign_folds,
    build_matrix,
    calendar_cut,
    folds_from_run,
)
from packages.eval import split as split_mod
from packages.sim.export import (
    SPLIT_COLUMNS,
    TRAIN_ALLOWLIST,
    TRAIN_DENYLIST,
    assert_split_schema,
    assert_train_schema,
    export_run,
)
from packages.sim.ledger import LABEL_FAMILIES, make_event
from packages.sim.runner import run_population


def _ts(day: int, hour: int = 10) -> datetime:
    return datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=day, hours=hour)


def test_export_split_schema_and_not_in_train(tmp_path: Path):
    events = []
    for i in range(6):
        events.append(
            make_event(
                seq=i + 1,
                ts=_ts(i),
                rail="upi_like",
                payer="VID-SIM-C-000001",
                payee="VID-SIM-M-000001",
                amount_minor=50_000,
                label_family="normal",
                features_auth={"fan_in_1h": 0, "kyc_tier": "tier2"},
                kyc_tier="tier2",
            )
        )
    paths = export_run(events, {"run_id": "a"}, "run-a", runs_dir=tmp_path)
    assert_train_schema(paths["parquet_path"])
    assert_split_schema(paths["split_path"])
    train = pd.read_parquet(paths["parquet_path"])
    split = pd.read_parquet(paths["split_path"])
    assert set(split.columns) == set(SPLIT_COLUMNS)
    assert len(train) == len(split) == 6
    for banned in TRAIN_DENYLIST:
        assert banned not in train.columns
        assert banned not in split.columns
    for leak in ("event_ts", "event_id", "payer", "payee"):
        assert leak not in train.columns
    assert train.columns.tolist()  # allowlist only
    assert set(train.columns) <= set(TRAIN_ALLOWLIST)


def test_time_cut_uses_event_ts_not_shuffle():
    src = inspect.getsource(split_mod)
    assert "train_test_split" not in src
    assert "shuffle=True" not in src
    rows = []
    for i in range(9):
        rows.append(
            {
                "event_id": f"evt-{i:010d}",
                "event_ts": _ts(i).isoformat(),
                "payer": "VID-SIM-C-000010",
                "payee": "VID-SIM-M-000001",
                "amount_minor": 1,
                "label_family": "normal",
            }
        )
    split = pd.DataFrame(rows)
    folds = assign_folds(split, seed=42, customer_holdout_frac=0.0, mule_holdout_frac=0.0)
    cut = calendar_cut(split["event_ts"])
    train_ts = pd.to_datetime(split.loc[folds == "train", "event_ts"], utc=True)
    eval_ts = pd.to_datetime(split.loc[folds == "eval", "event_ts"], utc=True)
    assert train_ts.max() < eval_ts.min()
    assert train_ts.max() < cut or train_ts.max() <= cut
    assert (eval_ts >= cut).all()


def test_entity_holdout_mule_payee_goes_to_eval_even_if_early():
    rows = []
    for i in range(10):
        payee = "VID-SIM-U-000001" if i < 3 else "VID-SIM-U-000002"
        if i >= 8:
            payee = "VID-SIM-M-000001"
        payer = "VID-SIM-C-000001"
        rows.append(
            {
                "event_id": f"evt-{i:010d}",
                "event_ts": _ts(i).isoformat(),
                "payer": payer,
                "payee": payee,
                "amount_minor": 1,
                "label_family": "mule" if payee.startswith("VID-SIM-U-") else "normal",
            }
        )
    split = pd.DataFrame(rows)
    folds = assign_folds(split, seed=42, customer_holdout_frac=0.0, mule_holdout_frac=0.5)
    # At least one early mule-payee row is eval because that payee was held out.
    early = pd.to_datetime(split["event_ts"], utc=True)
    cut = calendar_cut(split["event_ts"])
    early_mule = (early < cut) & split["payee"].astype(str).str.startswith("VID-SIM-U-")
    assert early_mule.any()
    held_eval_early = (folds == "eval") & early_mule
    assert held_eval_early.any(), "entity holdout must mark some early mule-payee rows eval"


def test_party_ids_cannot_enter_X(tmp_path: Path):
    events = []
    for i in range(8):
        events.append(
            make_event(
                seq=i + 1,
                ts=_ts(i),
                rail="upi_like",
                payer="VID-SIM-C-000001",
                payee="VID-SIM-M-000001" if i < 6 else "VID-SIM-U-000001",
                amount_minor=20_000,
                label_family="normal" if i < 6 else "mule",
                features_auth={
                    "fan_in_1h": 0 if i < 6 else 9,
                    "kyc_tier": "tier2",
                    "account_age_days": 30,
                    "payee_history_count": 1,
                    "amount_vs_p30": 1.0,
                    "fan_out_1h": 0,
                    "is_new_payee": False,
                    "is_new_device": False,
                    "burst_velocity": 0.0,
                    "call_active_flag": False,
                    "copy_paste_payee_flag": False,
                    "pause_ms": 0,
                    "urgency_pressure": 0.0,
                },
                kyc_tier="tier2",
            )
        )
    paths = export_run(events, {}, "leak", runs_dir=tmp_path)
    train = pd.read_parquet(paths["parquet_path"])
    split = pd.read_parquet(paths["split_path"])
    poisoned = train.copy()
    poisoned["payer"] = split["payer"]
    poisoned["payee"] = split["payee"]
    poisoned["event_ts"] = split["event_ts"]
    folds = assign_folds(split, seed=42, customer_holdout_frac=0.0, mule_holdout_frac=0.0)
    with pytest.raises(LeakError, match="forbidden"):
        build_matrix(poisoned, split, folds, fold="train")

    x, y = build_matrix(train, split, folds, fold="train")
    assert "payer" not in x.columns
    assert "payee" not in x.columns
    assert "event_ts" not in x.columns
    assert "event_id" not in x.columns
    assert "label_family" not in x.columns
    for fam in y.unique():
        assert fam in LABEL_FAMILIES
        assert not str(fam).startswith("T")


def test_population_writes_split_join_safe(tmp_path: Path):
    result = run_population(
        None,
        run_id="pop-split",
        n_customers=16,
        n_merchants=6,
        sim_days=40,
        world_seed=42,
        runs_dir=tmp_path,
        pin=True,
    )
    assert result["split_path"]
    assert_split_schema(result["split_path"])
    train = pd.read_parquet(result["parquet_path"])
    split = pd.read_parquet(result["split_path"])
    packed = folds_from_run(train, split, seed=42)
    assert packed["protocol"] == "time_cut_2_3_plus_entity_holdout"
    assert "payer" not in packed["X_train"].columns
    assert packed["y_train"].isin(LABEL_FAMILIES).all()
    assert (packed["folds"] == "eval").any()
    assert (packed["folds"] == "train").any()
