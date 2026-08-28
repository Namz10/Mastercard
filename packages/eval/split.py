"""Time cut + entity holdout. Split columns never enter model X (Plan 12 Lock 1)."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

from packages.sim.export import TRAIN_ALLOWLIST, TRAIN_DENYLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS

Fold = Literal["train", "eval"]

SPLIT_ONLY_COLUMNS = frozenset(
    {"event_id", "event_ts", "payer", "payee", "amount_minor"}
)
MULE_PAYEE_PREFIXES = ("VID-SIM-U-", "VID-SIM-APP-", "VID-SIM-CHAIN-")
CUSTOMER_PREFIX = "VID-SIM-C-"


class LeakError(AssertionError):
    """Party ids, clock, or denylist columns present in model matrix X."""


def _parse_ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, format="ISO8601")


def calendar_cut(ts: pd.Series) -> pd.Timestamp:
    """First 2/3 of *this run's* calendar → train candidate; last 1/3 → eval."""
    parsed = _parse_ts(ts)
    t0 = parsed.min()
    t1 = parsed.max()
    if pd.isna(t0) or pd.isna(t1):
        raise ValueError("event_ts required for time cut")
    if t0 == t1:
        order = parsed.index.to_numpy()
        cut_i = max(1, int(len(order) * 2 / 3))
        return parsed.iloc[cut_i - 1]
    return t0 + (t1 - t0) * (2.0 / 3.0)


def _mule_payees(payees: pd.Series) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in payees.astype(str):
        if p in seen:
            continue
        if p.startswith(MULE_PAYEE_PREFIXES):
            seen.add(p)
            out.append(p)
    return out


def _customers(parties: pd.Series) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for p in parties.astype(str):
        if p in seen:
            continue
        if p.startswith(CUSTOMER_PREFIX):
            seen.add(p)
            out.append(p)
    return out


def assign_folds(
    split_df: pd.DataFrame,
    *,
    seed: int = 42,
    customer_holdout_frac: float = 0.15,
    mule_holdout_frac: float = 0.30,
) -> pd.Series:
    """
    eval if last 1/3 calendar **or** payer/payee in entity holdout.
    Not sklearn shuffle. Returns Series of 'train' | 'eval' aligned to split_df.
    """
    if "event_ts" not in split_df.columns:
        raise ValueError("split artifact missing event_ts")
    work = split_df.reset_index(drop=True)
    parsed = _parse_ts(work["event_ts"])
    t0, t1 = parsed.min(), parsed.max()
    if pd.isna(t0) or pd.isna(t1):
        raise ValueError("event_ts required for time cut")
    if t0 == t1:
        late = pd.Series(np.arange(len(work)) >= max(1, int(len(work) * 2 / 3)), index=work.index)
    else:
        cut = t0 + (t1 - t0) * (2.0 / 3.0)
        late = parsed >= cut

    rng = np.random.default_rng(seed)
    mule_ids = _mule_payees(work["payee"])
    cust_ids = _customers(pd.concat([work["payer"], work["payee"]], ignore_index=True))

    n_mule_hold = 0
    if len(mule_ids) >= 2:
        n_mule_hold = min(len(mule_ids) - 1, max(1, int(round(len(mule_ids) * mule_holdout_frac))))
    n_cust_hold = 0
    if len(cust_ids) >= 2:
        n_cust_hold = min(len(cust_ids) - 1, max(1, int(round(len(cust_ids) * customer_holdout_frac))))

    hold_mules = set(rng.choice(mule_ids, size=n_mule_hold, replace=False).tolist()) if n_mule_hold else set()
    hold_cust = set(rng.choice(cust_ids, size=n_cust_hold, replace=False).tolist()) if n_cust_hold else set()
    hold = hold_mules | hold_cust

    entity_hit = work["payer"].astype(str).isin(hold) | work["payee"].astype(str).isin(hold)
    is_eval = late | entity_hit
    folds = pd.Series(np.where(is_eval, "eval", "train"), index=work.index, name="fold")
    if not (folds == "train").any():
        raise ValueError("entity+time holdout left an empty train fold")
    if not (folds == "eval").any():
        raise ValueError("time cut produced an empty eval fold")
    return folds


def assert_no_x_leak(columns: list[str] | pd.Index) -> None:
    cols = set(columns)
    leaked = cols & (SPLIT_ONLY_COLUMNS | set(TRAIN_DENYLIST))
    if leaked:
        raise LeakError(f"forbidden columns in X: {sorted(leaked)}")
    if "label_family" in cols:
        raise LeakError("label_family must be y, not a feature")
    extra = cols - set(TRAIN_ALLOWLIST)
    # rule-hit bits (Phase C) may use prefix rule__
    extras_real = {c for c in extra if not str(c).startswith("rule__")}
    if extras_real:
        raise LeakError(f"columns not on train allowlist: {sorted(extras_real)}")


def align_run(train_df: pd.DataFrame, split_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(train_df) != len(split_df):
        raise ValueError(
            f"train/split length mismatch: {len(train_df)} vs {len(split_df)} — export must write both in event order"
        )
    return train_df.reset_index(drop=True), split_df.reset_index(drop=True)


def build_matrix(
    train_df: pd.DataFrame,
    split_df: pd.DataFrame,
    folds: pd.Series,
    *,
    fold: Fold,
) -> tuple[pd.DataFrame, pd.Series]:
    """X = allowlist minus label_family. Split-only columns dropped even if concatenated by mistake."""
    train_df, split_df = align_run(train_df, split_df)
    folds = folds.reset_index(drop=True)
    if len(folds) != len(train_df):
        raise ValueError("folds length mismatch")
    mask = folds == fold
    y = train_df.loc[mask, "label_family"].astype(str)
    for fam in y.unique():
        if fam in TECHNIQUE_IDS:
            raise AssertionError(f"y must be label_family enum, not technique id: {fam}")
        if fam not in LABEL_FAMILIES:
            raise AssertionError(f"unknown label_family in y: {fam}")
    leaked = set(train_df.columns) & (SPLIT_ONLY_COLUMNS | set(TRAIN_DENYLIST))
    if leaked:
        raise LeakError(f"forbidden columns in X: {sorted(leaked)}")
    x = train_df.loc[mask].drop(columns=["label_family"])
    assert_no_x_leak(x.columns)
    return x, y


def folds_from_run(
    train_df: pd.DataFrame,
    split_df: pd.DataFrame,
    *,
    seed: int = 42,
    force_train_event_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    train_df, split_df = align_run(train_df, split_df)
    folds = assign_folds(split_df, seed=seed)
    if force_train_event_ids:
        force = split_df["event_id"].astype(str).isin(force_train_event_ids)
        folds = folds.copy()
        folds.loc[force.to_numpy()] = "train"
        if not (folds == "eval").any():
            raise ValueError("Loop M extra rows consumed the eval fold")
    x_tr, y_tr = build_matrix(train_df, split_df, folds, fold="train")
    x_ev, y_ev = build_matrix(train_df, split_df, folds, fold="eval")
    return {
        "folds": folds,
        "X_train": x_tr,
        "y_train": y_tr,
        "X_eval": x_ev,
        "y_eval": y_ev,
        "protocol": "time_cut_2_3_plus_entity_holdout",
    }
