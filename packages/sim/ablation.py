"""APP flag ablation smoke — report metric; not Defend (Plan 08 Phase G)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.preprocessing import OrdinalEncoder

from packages.sim.export import train_rows

APP_FLAG_COLS = (
    "call_active_flag",
    "copy_paste_payee_flag",
    "pause_ms",
    "urgency_pressure",
)


def _frame(events: list[dict[str, Any]]) -> pd.DataFrame:
    rows = train_rows(events)
    df = pd.DataFrame(rows)
    df["_ts"] = [e["event_ts"] for e in events]
    return df.sort_values("_ts").reset_index(drop=True)


def _xy(df: pd.DataFrame, *, drop_app_flags: bool) -> tuple[np.ndarray, np.ndarray]:
    y = (df["label_family"] == "app_fraud").astype(int).to_numpy()
    work = df.drop(columns=["label_family", "_ts"], errors="ignore").copy()
    if drop_app_flags:
        for col in APP_FLAG_COLS:
            if col in work.columns:
                work[col] = 0
                if col.endswith("_flag"):
                    work[col] = False
    cat_cols = [c for c in ("rail", "kyc_tier") if c in work.columns]
    num = work.drop(columns=cat_cols)
    for c in num.columns:
        if num[c].dtype == bool:
            num[c] = num[c].astype(int)
        num[c] = pd.to_numeric(num[c], errors="coerce").fillna(0)
    x_num = num.to_numpy(dtype=float)
    if cat_cols:
        enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        x_cat = enc.fit_transform(work[cat_cols].astype(str))
        x = np.hstack([x_num, x_cat])
    else:
        x = x_num
    return x, y


def ablation_report(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Time cut 2/3–1/3 on this run's calendar. APP flags never a silent cheat."""
    df = _frame(events)
    n = len(df)
    if n < 40:
        raise ValueError("ablation needs a mixed ledger, not a 1-row stub")
    cut = int(n * 2 / 3)
    train_df, test_df = df.iloc[:cut], df.iloc[cut:]
    n_app_test = int((test_df["label_family"] == "app_fraud").sum())
    x_tr, y_tr = _xy(train_df, drop_app_flags=False)
    x_te, y_te = _xy(test_df, drop_app_flags=False)
    x_tr_ab, _ = _xy(train_df, drop_app_flags=True)
    x_te_ab, _ = _xy(test_df, drop_app_flags=True)

    def _fit_score(x_train: np.ndarray, x_test: np.ndarray) -> dict[str, float]:
        model = HistGradientBoostingClassifier(
            max_depth=3,
            max_iter=80,
            learning_rate=0.08,
            random_state=42,
        )
        model.fit(x_train, y_tr)
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x_test)[:, 1]
        else:
            proba = model.decision_function(x_test)
        out = {"n_test": int(len(y_te)), "n_app_test": n_app_test}
        if y_te.min() != y_te.max():
            out["roc_auc"] = float(roc_auc_score(y_te, proba))
            out["average_precision"] = float(average_precision_score(y_te, proba))
        else:
            out["roc_auc"] = float("nan")
            out["average_precision"] = float("nan")
        return out

    with_flags = _fit_score(x_tr, x_te)
    without_flags = _fit_score(x_tr_ab, x_te_ab)
    ap_with = with_flags.get("average_precision", float("nan"))
    ap_without = without_flags.get("average_precision", float("nan"))
    died = (
        n_app_test > 0
        and np.isfinite(ap_with)
        and np.isfinite(ap_without)
        and ap_without <= max(0.05, 0.5 * ap_with)
    )
    return {
        "n_rows": n,
        "split": "time_cut_first_2_3",
        "app_flags": list(APP_FLAG_COLS),
        "with_app_flags": with_flags,
        "without_app_flags": without_flags,
        "app_metric_died_without_synthetic_flags": died,
        "note": (
            "Lab LightGBM/HGB smoke only. Synthetic call/paste/urgency/pause are not an SDK. "
            "If APP average precision collapses without those columns, that is a documented "
            "result — not a silent train-time cheat. is_authorized_push is not a feature."
        ),
    }
