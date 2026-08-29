"""Time cut + entity holdout. Split columns never enter model X (Plan 12 Lock 1)."""

from __future__ import annotations

from typing import Any, Literal
import logging

import numpy as np
import pandas as pd

from packages.sim.export import TRAIN_ALLOWLIST, TRAIN_DENYLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS

Fold = Literal["train", "eval"]

_LOG = logging.getLogger(__name__)

SPLIT_ONLY_COLUMNS = frozenset(
    {"event_id", "event_ts", "payer", "payee", "amount_minor", "campaign_id"}
)
MULE_PAYEE_PREFIXES = ("VID-SIM-U-", "VID-SIM-APP-", "VID-SIM-CHAIN-")
CUSTOMER_PREFIX = "VID-SIM-C-"
INNER_FOLD_FLOOR = 15


class LeakError(AssertionError):
    """Party ids, clock, or denylist columns present in model matrix X."""


def _parse_ts(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, format="ISO8601")


def calendar_cut(
    ts: pd.Series,
    *,
    horizon_end: pd.Timestamp | None = None,
    sim_days: int | None = None,
    t0: pd.Timestamp | None = None,
) -> pd.Timestamp:
    """First 2/3 of the configured horizon → train candidate; last 1/3 → eval."""
    parsed = _parse_ts(ts)
    t0_val = t0 if t0 is not None else parsed.min()
    if sim_days is not None and not pd.isna(t0_val):
        horizon_end = t0_val + pd.Timedelta(days=float(sim_days))
    elif horizon_end is None:
        t1 = parsed.max()
        if pd.isna(t0_val) or pd.isna(t1):
            raise ValueError("event_ts required for time cut")
        if t0_val == t1:
            order = parsed.index.to_numpy()
            cut_i = max(1, int(len(order) * 2 / 3))
            return parsed.iloc[cut_i - 1]
        horizon_end = t1
    if pd.isna(t0_val) or horizon_end is None or pd.isna(horizon_end):
        raise ValueError("event_ts required for time cut")
    return t0_val + (horizon_end - t0_val) * (2.0 / 3.0)


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
    sim_days: int | None = None,
) -> pd.Series:
    """
    eval if last 1/3 calendar **or** payer/payee in entity holdout.
    Not sklearn shuffle. Returns Series of 'train' | 'eval' aligned to split_df.
    """
    if "event_ts" not in split_df.columns:
        raise ValueError("split artifact missing event_ts")
    work = split_df.reset_index(drop=True)
    parsed = _parse_ts(work["event_ts"])
    t0 = parsed.min()
    if sim_days is not None:
        cut = calendar_cut(parsed, sim_days=sim_days, t0=t0)
        late = parsed >= cut
    else:
        t1 = parsed.max()
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
    if len(mule_ids) >= 20:
        n_mule_hold = min(len(mule_ids) - 1, max(1, int(round(len(mule_ids) * mule_holdout_frac))))
    elif len(mule_ids) >= 2:
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


def inner_folds_from_train(
    split_df: pd.DataFrame,
    folds: pd.Series,
    *,
    fraction: float = 0.20,
    exclude_event_ids: frozenset[str] | None = None,
) -> pd.Series:
    """Carve inner_fit / inner_val from outer train by last 20% of calendar span.

    Never shuffled — deterministic calendar cut identical in style to
    :func:`calendar_cut` but measured from the *end* of the span.

    ``exclude_event_ids`` (Loop M extras forced into train) are ignored when
    measuring the calendar span and always assigned ``inner_fit`` so they
    cannot turn inner_val into a single-family slice.
    """
    mask = (folds == "train").to_numpy()
    if not mask.any():
        raise ValueError("outer train fold is empty; cannot create inner folds")
    extra = np.zeros(len(split_df), dtype=bool)
    if exclude_event_ids:
        extra = split_df["event_id"].astype(str).isin(exclude_event_ids).to_numpy()
    span_mask = mask & ~extra
    if not span_mask.any():
        raise ValueError("outer train fold is empty after excluding extra event_ids")
    ts = _parse_ts(split_df.loc[span_mask, "event_ts"])
    t0, t1 = ts.min(), ts.max()
    if pd.isna(t0) or pd.isna(t1):
        raise ValueError("event_ts required for inner fold calendar cut")
    cut = t1 - (t1 - t0) * fraction   # last `fraction` of calendar span
    inner = pd.Series("inner_fit", index=folds.index, name="inner_fold")
    inner.loc[mask & (_parse_ts(split_df["event_ts"]) >= cut).to_numpy()] = "inner_val"
    inner.loc[~mask] = "outer_eval"
    if extra.any():
        inner.loc[extra & mask] = "inner_fit"
    # Guard: both inner folds must be non-empty
    if not (inner == "inner_val").any():
        raise ValueError(
            "inner_val is empty after calendar cut — calendar span too short "
            f"(t0={t0}, t1={t1}, fraction={fraction})"
        )
    if not (inner == "inner_fit").any():
        raise ValueError(
            "inner_fit is empty after calendar cut — all train rows fall in inner_val "
            f"(t0={t0}, t1={t1}, fraction={fraction})"
        )
    _LOG.info(
        "inner_folds_from_train",
        extra={
            "inner_fit_n": int((inner == "inner_fit").sum()),
            "inner_val_n": int((inner == "inner_val").sum()),
            "cut_ts": str(cut),
        },
    )
    return inner


def split_inner_val_ab(
    split_df: pd.DataFrame,
    inner_val_mask: pd.Series | np.ndarray,
    *,
    mode: str = "calendar_50_50",
) -> tuple[np.ndarray, np.ndarray]:
    """Split inner_val into disjoint A (objective) and B (FPR constraint) slices."""
    if mode != "calendar_50_50":
        raise ValueError(f"unsupported inner_val A/B mode: {mode}")
    mask = np.asarray(inner_val_mask, dtype=bool)
    if not mask.any():
        raise ValueError("inner_val mask is empty")
    ts = _parse_ts(split_df.loc[mask, "event_ts"])
    t0, t1 = ts.min(), ts.max()
    if pd.isna(t0) or pd.isna(t1) or t0 == t1:
        order = np.where(mask)[0]
        mid = max(1, len(order) // 2)
        a = np.zeros(len(split_df), dtype=bool)
        b = np.zeros(len(split_df), dtype=bool)
        a[order[:mid]] = True
        b[order[mid:]] = True
        return a, b
    cut = t0 + (t1 - t0) * 0.5
    late = (_parse_ts(split_df["event_ts"]) >= cut).to_numpy()
    a = mask & ~late
    b = mask & late
    if not a.any() or not b.any():
        order = np.where(mask)[0]
        mid = max(1, len(order) // 2)
        a = np.zeros(len(split_df), dtype=bool)
        b = np.zeros(len(split_df), dtype=bool)
        a[order[:mid]] = True
        b[order[mid:]] = True
    return a, b


def assert_fold_n_pos(
    y: pd.Series,
    folds: pd.Series,
    inner: pd.Series,
    *,
    min_n: int = INNER_FOLD_FLOOR,
    strict: bool = False,
) -> None:
    """Check inner_fit/inner_val/eval fraud positives per family."""
    y = y.reset_index(drop=True)
    folds = folds.reset_index(drop=True)
    inner = inner.reset_index(drop=True)
    if not (len(y) == len(folds) == len(inner)):
        raise ValueError(
            f"assert_fold_n_pos length mismatch: y={len(y)} folds={len(folds)} inner={len(inner)} "
            "(pass full-run labels, not train-only y)"
        )
    slices = {
        "inner_fit": inner == "inner_fit",
        "inner_val": inner == "inner_val",
        "eval": folds == "eval",
    }
    fraud_fams = sorted(LABEL_FAMILIES - {"normal"})
    shortfalls: list[str] = []
    for slice_name, mask in slices.items():
        sub = y.loc[mask]
        for fam in fraud_fams:
            n = int((sub.astype(str) == fam).sum())
            if n < min_n:
                shortfalls.append(f"{slice_name}.{fam}={n}<{min_n}")
    if shortfalls:
        msg = (
            "fold n_pos floor not met (generator/calendar may need E1/E2 fixes): "
            + ", ".join(shortfalls)
        )
        if strict:
            raise ValueError(msg)
        else:
            _LOG.warning("fold_n_pos_shortfall: %s", msg)


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
    sim_days: int | None = None,
) -> dict[str, Any]:
    train_df, split_df = align_run(train_df, split_df)
    folds = assign_folds(split_df, seed=seed, sim_days=sim_days)
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
