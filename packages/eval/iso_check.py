"""Isolation Forest anomaly detector for stamp-free organic feature signals (Phase 6 / Ticket 8)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ISO_STAMP_FREE_FEATURES = (
    "account_age_days",
    "payee_history_count",
    "amount_vs_p30",
    "fan_in_1h",
    "fan_out_1h",
    "fan_in_unique_payers_1h",
    "burst_velocity",
    "is_new_payee",
    "is_new_device",
)


def fit_isolation_forest(
    x_inner_fit_df: pd.DataFrame,
    y_inner_fit: pd.Series,
) -> IsolationForest:
    """Train Isolation Forest on inner_fit rows where label_family == 'normal' only."""
    normal_mask = (y_inner_fit.astype(str) == "normal").to_numpy()
    normal_df = x_inner_fit_df.loc[normal_mask, list(ISO_STAMP_FREE_FEATURES)].copy()

    for col in ISO_STAMP_FREE_FEATURES:
        if normal_df[col].dtype == bool:
            normal_df[col] = normal_df[col].astype(int)
        else:
            normal_df[col] = pd.to_numeric(normal_df[col], errors="coerce").fillna(0)

    model = IsolationForest(n_estimators=100, random_state=42, contamination=0.05)
    if not normal_df.empty:
        model.fit(normal_df.to_numpy())
    return model


def check_iso_genuine_notify_rate(
    iso_model: IsolationForest,
    x_inner_val_df: pd.DataFrame,
    y_inner_val: pd.Series,
) -> float:
    """Check notification rate of Isolation Forest on genuine inner_val rows."""
    normal_mask = (y_inner_val.astype(str) == "normal").to_numpy()
    normal_df = x_inner_val_df.loc[normal_mask, list(ISO_STAMP_FREE_FEATURES)].copy()

    if normal_df.empty:
        return 0.0

    for col in ISO_STAMP_FREE_FEATURES:
        if normal_df[col].dtype == bool:
            normal_df[col] = normal_df[col].astype(int)
        else:
            normal_df[col] = pd.to_numeric(normal_df[col], errors="coerce").fillna(0)

    preds = iso_model.predict(normal_df.to_numpy())  # -1 = anomaly, 1 = normal
    notify_count = (preds == -1).sum()
    return float(notify_count / len(normal_df))


def is_iso_anomaly(
    iso_model: IsolationForest,
    row: dict[str, Any] | pd.Series,
    pred_family: str,
    pmap_normal: float,
    iso_p_normal_floor: float = 0.95,
) -> bool:
    """Only run IF if pred_family == 'normal' and pmap['normal'] >= 0.95."""
    if pred_family != "normal" or pmap_normal < iso_p_normal_floor:
        return False

    vec = []
    for col in ISO_STAMP_FREE_FEATURES:
        val = row.get(col, 0) if isinstance(row, dict) else row[col]
        if isinstance(val, bool):
            vec.append(int(val))
        else:
            try:
                vec.append(float(val) if val is not None else 0.0)
            except (TypeError, ValueError):
                vec.append(0.0)

    x = np.array(vec, dtype=float).reshape(1, -1)
    pred = iso_model.predict(x)[0]
    return bool(pred == -1)


def apply_iso_brake_upgrade(action: str, is_anomaly: bool, reasons: list[str]) -> tuple[str, list[str]]:
    """Brake insertion: if action is 'allow' and iso_anomaly, upgrade to 'notify'.

    Never downgrade mule_credit_restrict, hold, or decline.
    """
    new_reasons = list(reasons)
    if action == "allow" and is_anomaly:
        new_reasons.append("iso_anomaly")
        return "notify", new_reasons
    return action, new_reasons


def _bool_flag(block: dict[str, Any], key: str, default: bool = False) -> bool:
    """Read a boolean feature flag defensively. Missing/malformed -> default (off)."""
    value = block.get(key, default)
    return value if isinstance(value, bool) else default


def iso_enabled_flag(
    iso_cfg: dict[str, Any] | None,
    genuine_notify_rate: float,
) -> bool:
    """Kill switch: IF is only used if enabled_default and notify rate on inner-val is low.

    A noisy IF that alerts on >abort fraction of genuine traffic is worse than none —
    this is a real off switch, not a warning. Missing/malformed config -> off.
    """
    cfg = iso_cfg or {}
    enabled_default = _bool_flag(cfg, "enabled_default", default=False)
    abort = 0.05
    try:
        abort = float(cfg.get("genuine_notify_rate_abort", 0.05))
    except (TypeError, ValueError):
        abort = 0.05
    return bool(enabled_default and genuine_notify_rate <= abort)
