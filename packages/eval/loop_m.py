"""Loop M once: miss family extra on train only, G-test on a new seed (Plan 12 Phase E)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.eval.fit import (
    JSON_BAN,
    assert_no_denylist_payload,
    fit_champion,
    load_recipe,
    run_paths,
    score_run,
)
from packages.sim.export import RUNS_DIR, TRAIN_ALLOWLIST
from packages.sim.ledger import LABEL_FAMILIES
from packages.sim.runner import run_population

FRAUD_FAMILIES = LABEL_FAMILIES - {"normal"}


def _sidecar(run_id: str, runs_dir: Path) -> dict[str, Any]:
    path = run_paths(run_id, runs_dir)["sidecar"]
    if not path.is_file():
        raise FileNotFoundError(f"missing sidecar for run_id={run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _ap(metrics: dict[str, Any], family: str) -> float | None:
    block = metrics.get("ap_by_family") or {}
    val = block.get(family)
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(num):
        return None
    return num


def _fpr(metrics: dict[str, Any]) -> float | None:
    val = metrics.get("genuine_fp")
    if val is None:
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(num):
        return None
    return num


def _ap_verdict(before: float | None, after: float | None, eps: float) -> str:
    if before is None or after is None:
        return "not_comparable"
    if after >= before - eps:
        return "improved" if after > before else "equal"
    return "regressed"


def _scale(
    sidecar: dict[str, Any],
    *,
    n_customers: int | None,
    n_merchants: int | None,
    sim_days: int | None,
    pin: bool | None,
) -> dict[str, Any]:
    nc = n_customers if n_customers is not None else sidecar.get("n_customers")
    nm = n_merchants if n_merchants is not None else sidecar.get("n_merchants")
    days = sim_days if sim_days is not None else sidecar.get("sim_days")
    pinned = sidecar.get("pin") if pin is None else pin
    if nc is None or nm is None or days is None:
        raise ValueError(
            "Loop M needs n_customers, n_merchants, sim_days on the train sidecar "
            "or on the request (same engine scale as G-test)"
        )
    return {
        "n_customers": int(nc),
        "n_merchants": int(nm),
        "sim_days": int(days),
        "pin": bool(pinned) if pinned is not None else False,
    }


def _write_augmented(
    *,
    train_id: str,
    augmented_id: str,
    family: str,
    extra_id: str,
    cap_frac: float,
    runs_dir: Path,
) -> tuple[int, int, frozenset[str]]:
    orig = run_paths(train_id, runs_dir)
    extra = run_paths(extra_id, runs_dir)
    train_df = pd.read_parquet(orig["train"])
    split_df = pd.read_parquet(orig["split"])
    extra_tr = pd.read_parquet(extra["train"])
    extra_sp = pd.read_parquet(extra["split"])
    if set(extra_tr.columns) - set(TRAIN_ALLOWLIST):
        raise AssertionError("extra train cols outside allowlist")
    mask = extra_tr["label_family"].astype(str) == family
    extra_tr = extra_tr.loc[mask].reset_index(drop=True)
    extra_sp = extra_sp.loc[mask].reset_index(drop=True)
    if extra_tr.empty:
        raise ValueError(f"extra mix produced zero {family} rows")
    cap = max(1, int(len(train_df) * cap_frac))
    if len(extra_tr) > cap:
        extra_tr = extra_tr.iloc[:cap].reset_index(drop=True)
        extra_sp = extra_sp.iloc[:cap].reset_index(drop=True)
    new_ids = [f"evt-lm-{i:010d}" for i in range(len(extra_tr))]
    extra_sp = extra_sp.copy()
    extra_sp["event_id"] = new_ids
    t0 = pd.to_datetime(split_df["event_ts"], utc=True, format="ISO8601").min()
    shifted = t0 + pd.to_timedelta(np.arange(len(extra_sp)), unit="s")
    extra_sp["event_ts"] = [ts.isoformat() for ts in shifted]
    out_tr = pd.concat([train_df, extra_tr], ignore_index=True)
    out_sp = pd.concat([split_df, extra_sp], ignore_index=True)
    dest = runs_dir / augmented_id
    dest.mkdir(parents=True, exist_ok=True)
    out_tr.to_parquet(dest / "train.parquet", index=False)
    out_sp.to_parquet(dest / "split.parquet", index=False)
    (dest / "sidecar.json").write_text(
        json.dumps(
            {
                "run_id": augmented_id,
                "mode": "loop_m_train",
                "source_run_id": train_id,
                "miss_family": family,
                "n_extra": int(len(extra_tr)),
                "extra_row_cap_frac": cap_frac,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (dest / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": augmented_id,
                "row_count": len(out_tr),
                "n_extra": int(len(extra_tr)),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (dest / "_DONE").write_text("DONE\n", encoding="utf-8")
    return int(len(extra_tr)), cap, frozenset(new_ids)


def run_loop_m(
    run_id: str,
    miss_family: str,
    *,
    train_seed: int = 42,
    gtest_seed: int = 43,
    family_chosen_from_slice: str = "gdev44",
    n_customers: int | None = None,
    n_merchants: int | None = None,
    sim_days: int | None = None,
    pin: bool | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
) -> dict[str, Any]:
    family = str(miss_family)
    if family not in FRAUD_FAMILIES:
        raise ValueError(f"miss_family must be a fraud label_family, got {family}")
    if gtest_seed == train_seed:
        raise ValueError("G-test seed must differ from train seed")
    slice_choice = str(family_chosen_from_slice or "").strip().lower()
    if "gtest" in slice_choice or "43" in slice_choice:
        raise ValueError(f"Forbidden slice for miss family selection: {family_chosen_from_slice}. Must be inner_val | diagnostic | gdev44.")
    if slice_choice not in {"inner_val", "diagnostic", "gdev44"}:
        raise ValueError(f"family_chosen_from_slice must be one of: inner_val, diagnostic, gdev44; got {family_chosen_from_slice!r}")

    runs = runs_dir or RUNS_DIR
    recipe = load_recipe()
    loop_cfg = dict(recipe.get("loop_m") or {})
    ap_eps = float(loop_cfg.get("ap_equal_eps", 0.05))
    fpr_eps = float(loop_cfg.get("genuine_fpr_eps", 0.02))
    cap_frac = float(loop_cfg.get("extra_row_cap_frac", 0.15))
    sidecar = _sidecar(run_id, runs)
    scale = _scale(
        sidecar,
        n_customers=n_customers,
        n_merchants=n_merchants,
        sim_days=sim_days,
        pin=pin,
    )
    extra_seed = train_seed + 10_007
    extra_id = f"{run_id}__extra-{family}"
    gtest_id = f"{run_id}__gtest"
    aug_id = f"{run_id}__loopm-train"

    run_population(
        None,
        run_id=extra_id,
        world_seed=extra_seed,
        n_customers=scale["n_customers"],
        n_merchants=scale["n_merchants"],
        sim_days=scale["sim_days"],
        pin=scale["pin"],
        runs_dir=runs,
        families=frozenset({family}),
    )
    n_extra, cap, extra_ids = _write_augmented(
        train_id=run_id,
        augmented_id=aug_id,
        family=family,
        extra_id=extra_id,
        cap_frac=cap_frac,
        runs_dir=runs,
    )
    run_population(
        None,
        run_id=gtest_id,
        world_seed=gtest_seed,
        n_customers=scale["n_customers"],
        n_merchants=scale["n_merchants"],
        sim_days=scale["sim_days"],
        pin=scale["pin"],
        runs_dir=runs,
        families=None,
    )
    gtest_split = pd.read_parquet(run_paths(gtest_id, runs)["split"])
    if set(gtest_split["event_id"].astype(str)) & extra_ids:
        raise AssertionError("Loop M extra event_ids leaked onto G-test")

    fit_champion(run_id, world_seed=train_seed, runs_dir=runs, models_dir=models_dir)
    fit_champion(
        aug_id,
        world_seed=train_seed,
        runs_dir=runs,
        models_dir=models_dir,
        force_train_event_ids=extra_ids,
    )
    before = score_run(
        gtest_id, model_run_id=run_id, runs_dir=runs, models_dir=models_dir, all_rows=True
    )
    after = score_run(
        gtest_id, model_run_id=aug_id, runs_dir=runs, models_dir=models_dir, all_rows=True
    )
    ap0 = _ap(before["metrics"], family)
    ap1 = _ap(after["metrics"], family)
    fpr0 = _fpr(before["metrics"])
    fpr1 = _fpr(after["metrics"])
    ap_v = _ap_verdict(ap0, ap1, ap_eps)
    if fpr0 is None or fpr1 is None:
        fpr_ok = False
        fpr_note = "genuine FPR not comparable"
    else:
        fpr_ok = fpr1 <= fpr0 + fpr_eps
        fpr_note = (
            "genuine FPR not worse beyond frozen epsilon"
            if fpr_ok
            else "genuine FPR worsened beyond epsilon"
        )
    loop_pass = ap_v in {"improved", "equal"} and fpr_ok
    body = {
        "run_id": run_id,
        "miss_family": family,
        "catalog_solved": False,
        "catalog_status": "open",
        "train_seed": train_seed,
        "gtest_seed": gtest_seed,
        "extra_seed": extra_seed,
        "n_extra": n_extra,
        "extra_row_cap": cap,
        "extra_row_cap_frac": cap_frac,
        "ap_equal_eps": ap_eps,
        "genuine_fpr_eps": fpr_eps,
        "comparison": {
            "family": family,
            "family_chosen_from_slice": family_chosen_from_slice,
            "ap_before": ap0,
            "ap_after": ap1,
            "ap_delta": None if ap0 is None or ap1 is None else ap1 - ap0,
            "ap_verdict": ap_v,
            "genuine_fp_before": fpr0,
            "genuine_fp_after": fpr1,
            "genuine_fp_ok": fpr_ok,
            "genuine_fp_note": fpr_note,
            "n_pos_before": before["metrics"].get("n_pos", {}),
            "n_pos_after": after["metrics"].get("n_pos", {}),
        },
        "metrics": {
            "pass": loop_pass,
            "protocol": "g_test_new_seed",
            "gtest_before": before["metrics"],
            "gtest_after": after["metrics"],
        },
        "model_run_id_before": run_id,
        "model_run_id_after": aug_id,
        "gtest_run_id": gtest_id,
        "note": (
            "Extra miss-family rows appended to a train copy only; G-test is a new "
            "population at gtest_seed. AP is reported even if it drops. solved is not auto-set."
        ),
    }
    for key in JSON_BAN:
        if key in body:
            raise AssertionError(f"banned key in Loop M body: {key}")
    assert_no_denylist_payload(body)
    return body
