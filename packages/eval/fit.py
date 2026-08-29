"""Champion GBDT fit + metrics (Plan 12 Phase C). One HGB recipe, no AutoGluon."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, f1_score, roc_curve
from sklearn.preprocessing import OrdinalEncoder

from packages.config.ml import load_ml_flags, select_n_trials
from packages.eval.brake import as_record, brake
from packages.eval.iso_check import (
    apply_iso_brake_upgrade,
    check_iso_genuine_notify_rate,
    fit_isolation_forest,
    is_iso_anomaly,
    iso_enabled_flag,
)
from packages.eval.split import assert_no_x_leak, folds_from_run, inner_folds_from_train
from packages.policy.rules import Rule, evaluate_rules, load_v0_rules
from packages.sim.ablation import APP_FLAG_COLS
from packages.sim.export import RUNS_DIR, TRAIN_ALLOWLIST, TRAIN_DENYLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS

_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = _ROOT / "models"
RECIPE_PATH = MODELS_DIR / "features.json"
CAT_COLS = ("rail", "kyc_tier")
ALL_FAMILIES = tuple(sorted(LABEL_FAMILIES))
FRAUD_FAMILIES = tuple(sorted(LABEL_FAMILIES - {"normal"}))
METRICS_SCHEMA_VERSION = "1"
FP_COST_ACTIONS = ("notify", "hold", "decline")
JSON_BAN = frozenset(TRAIN_DENYLIST) | {
    "knobs_used",
    "knobs_pinned",
    "knobs",
    "simulatable_signals",
}


class RecipeHashMismatchError(RuntimeError):
    """features.json changed after the model was frozen — refuse to score."""


def _recipe_hash(path: Path | None = None) -> str:
    """SHA-256 of the raw features.json bytes — ties metrics to frozen config."""
    raw = (path or RECIPE_PATH).read_bytes()
    return hashlib.sha256(raw).hexdigest()


_LOG = logging.getLogger(__name__)


@dataclass
class Champion:
    model: HistGradientBoostingClassifier
    encoder: OrdinalEncoder
    raw_columns: list[str]
    cat_cols: list[str]
    classes: list[str]
    op_threshold: float
    fold_seed: int
    rule_ids: list[str]
    top_features: list[str]
    recipe: dict[str, Any]
    iso_model: Any | None = None
    isolation_forest_enabled: bool | None = None


def load_recipe(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or RECIPE_PATH).read_text(encoding="utf-8"))


def run_paths(run_id: str, runs_dir: Path | None = None) -> dict[str, Path]:
    folder = (runs_dir or RUNS_DIR) / run_id
    done = folder / "_DONE"
    if folder.is_dir() and not done.is_file():
        raise FileNotFoundError(f"run_id={run_id} is incomplete (missing _DONE marker)")
    return {
        "train": folder / "train.parquet",
        "split": folder / "split.parquet",
        "sidecar": folder / "sidecar.json",
        "folder": folder,
    }


def _attach_rule_bits(df: pd.DataFrame, rules: list[Rule]) -> pd.DataFrame:
    live = [r for r in rules if r.status == "live"]
    ids = [r.id for r in live]
    rows: list[dict[str, int]] = []
    for rec in df.to_dict(orient="records"):
        hits = {h.id for h in evaluate_rules(rec, live).hits}
        rows.append({f"rule__{rid}": int(rid in hits) for rid in ids})
    bits = pd.DataFrame(rows, index=df.index)
    out = pd.concat([df, bits], axis=1)
    assert_no_x_leak(out.drop(columns=["label_family"], errors="ignore").columns)
    return out


def _encode(
    df: pd.DataFrame,
    *,
    encoder: OrdinalEncoder | None,
    cat_cols: list[str],
    fit: bool,
) -> tuple[np.ndarray, OrdinalEncoder]:
    """Column i of X matches df.columns[i] so APP-flag ablation can zero by name."""
    work = df.copy()
    present = [c for c in cat_cols if c in work.columns]
    for c in work.columns:
        if c in present:
            work[c] = work[c].astype(str).fillna("missing")
        else:
            if work[c].dtype == bool:
                work[c] = work[c].astype(int)
            work[c] = pd.to_numeric(work[c], errors="coerce").fillna(0)
    if present:
        cat_frame = work[present].astype(str)
        if fit or encoder is None:
            encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
            codes = encoder.fit_transform(cat_frame)
        else:
            codes = encoder.transform(cat_frame)
        for i, c in enumerate(present):
            work[c] = codes[:, i]
    else:
        encoder = encoder or OrdinalEncoder()
    return work.to_numpy(dtype=float), encoder


def _class_weight(y: pd.Series) -> dict[str, float]:
    counts = y.value_counts()
    n = float(len(y))
    k = max(float(len(counts)), 1.0)
    return {str(c): n / (k * float(cnt)) for c, cnt in counts.items()}


def _proba_map(model: HistGradientBoostingClassifier, x: np.ndarray) -> dict[str, np.ndarray]:
    proba = model.predict_proba(x)
    return {str(c): proba[:, i] for i, c in enumerate(model.classes_)}


def _fraud_score(pmap: dict[str, np.ndarray], n: int) -> np.ndarray:
    if "normal" in pmap:
        return 1.0 - pmap["normal"]
    stacked = np.vstack(list(pmap.values())) if pmap else np.zeros((1, n))
    return stacked.max(axis=0)


def _pred_family(pmap: dict[str, np.ndarray], classes: list[str], n: int) -> np.ndarray:
    if not classes:
        return np.array(["normal"] * n, dtype=object)
    mat = np.column_stack([pmap.get(c, np.zeros(n)) for c in classes])
    idx = mat.argmax(axis=1)
    return np.array(classes, dtype=object)[idx]


def _tpr_at_fpr(y_bin: np.ndarray, scores: np.ndarray, target: float) -> dict[str, float]:
    if y_bin.min() == y_bin.max() or len(y_bin) < 2:
        return {"tpr": float("nan"), "threshold": 1.0, "fpr_target": target}
    fpr, tpr, thr = roc_curve(y_bin, scores)
    ok = np.where(fpr <= target)[0]
    if len(ok) == 0:
        return {"tpr": 0.0, "threshold": float(thr[0]), "fpr_target": target}
    i = int(ok[-1])
    return {"tpr": float(tpr[i]), "threshold": float(thr[i] if i < len(thr) else 1.0), "fpr_target": target}


def _ap_by_family(y: pd.Series, pmap: dict[str, np.ndarray]) -> dict[str, float]:
    out: dict[str, float] = {}
    yv = y.astype(str).to_numpy()
    n = len(yv)
    for fam in FRAUD_FAMILIES:
        mask = yv == fam
        if mask.sum() == 0 or (~mask).sum() == 0:
            out[fam] = float("nan")
            continue
        scores = pmap.get(fam, np.zeros(n))
        out[fam] = float(average_precision_score(mask.astype(int), scores))
    return out


def _n_pos_by_family(y: pd.Series) -> dict[str, int]:
    """Count label_family positives per family, covering all of LABEL_FAMILIES."""
    arr = y.astype(str).to_numpy()
    return {fam: int((arr == fam).sum()) for fam in ALL_FAMILIES}


def _not_comparable(n_pos: dict[str, int], below: int) -> dict[str, bool]:
    """Small-sample guard: a fraud family with fewer than `below` positives is not comparable."""
    return {fam: bool(n_pos.get(fam, 0) < below) for fam in FRAUD_FAMILIES}


def _cost_sketch(
    n_total: int,
    n_fraud: int,
    n_fn: int,
    fp_action_hist: dict[str, int],
) -> dict[str, Any]:
    """
    Lab-relative expected cost in unit 'lab_not_india' — never a real currency.

    expected_cost = miss_weight * FN_rate + weighted-FP-by-Brake-action, per row.
    A Brake action missing from the FP histogram defaults its contribution to 0
    (fail closed) and is surfaced via cost_sketch_action_missing notes + logs.
    """
    weights = {"notify": 1.0, "hold": 3.0, "decline": 8.0}
    miss_weight = 10.0
    notes: list[str] = []
    n = max(1, n_total)
    fp_cost = 0.0
    for action in FP_COST_ACTIONS:
        if action not in fp_action_hist:
            note = f"cost_sketch_action_missing:{action}"
            notes.append(note)
            _LOG.warning("cost_sketch_action_missing action=%s hist=%s", action, fp_action_hist)
        count = int(fp_action_hist.get(action, 0))
        fp_cost += weights[action] * count / n
    fn_rate = float(n_fn / max(1, n_fraud))
    return {
        "unit": "lab_not_india",
        "miss_weight": miss_weight,
        "fp_notify_weight": weights["notify"],
        "fp_hold_weight": weights["hold"],
        "fp_decline_weight": weights["decline"],
        "fn_rate": fn_rate,
        "fp_action_hist": dict(fp_action_hist),
        "expected_cost": float(miss_weight * fn_rate + fp_cost),
        "notes": notes,
    }


def _brake_action_hist(
    raw: pd.DataFrame,
    labels: pd.Series,
    payees: pd.Series,
    pred: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    rules: list[Rule],
    iso_model: Any | None = None,
    pmap: dict[str, np.ndarray] | None = None,
) -> tuple[dict[str, int], dict[str, int]]:
    """Brake action histogram over all rows + the false-positive rows only."""
    yhat = (scores >= threshold).astype(int)
    lbl = labels.astype(str).to_numpy()
    hist: dict[str, int] = {}
    fp_hist: dict[str, int] = {}
    records = raw.reset_index(drop=True).to_dict(orient="records")
    payee_list = payees.astype(str).tolist()
    n_rec = len(records)
    p_norm_arr = pmap.get("normal", np.zeros(n_rec)) if pmap else np.zeros(n_rec)

    for i, rec in enumerate(records):
        hits = evaluate_rules(rec, rules)
        action = as_record(
            brake(
                pred_label_family=str(pred[i]),
                score=float(scores[i]),
                hits=hits,
                payee=payee_list[i] if i < len(payee_list) else None,
            )
        )["policy_action"]

        if iso_model is not None and pmap is not None:
            if is_iso_anomaly(iso_model, rec, str(pred[i]), float(p_norm_arr[i])):
                action, _ = apply_iso_brake_upgrade(action, True, [])

        hist[action] = hist.get(action, 0) + 1
        if lbl[i] == "normal" and yhat[i] == 1:
            fp_hist[action] = fp_hist.get(action, 0) + 1
    return hist, fp_hist


def _top_features(
    model: HistGradientBoostingClassifier | None = None,
    x_val: np.ndarray | None = None,
    y_val: pd.Series | None = None,
    raw_columns: list[str] | pd.Index | None = None,
    k: int = 5,
) -> list[str]:
    """Permutation importance on inner_val using neg_log_loss (replaces correlation)."""
    if model is not None and x_val is not None and y_val is not None and raw_columns is not None:
        cols = [str(c) for c in raw_columns]
        if len(y_val.unique()) >= 2 and x_val.shape[0] >= 5:
            try:
                res = permutation_importance(
                    model,
                    x_val,
                    y_val.astype(str).to_numpy(),
                    scoring="neg_log_loss",
                    n_repeats=10,
                    random_state=42,
                )
                importances = res.importances_mean
                ranked = sorted(zip(importances, cols), reverse=True)
                return [name for _, name in ranked[:k]]
            except Exception:
                pass
    if raw_columns is not None:
        return [str(c) for c in list(raw_columns)[:k]]
    return []


def _compute_ece(y_bin: np.ndarray, scores: np.ndarray, n_bins: int = 10) -> float:
    if len(y_bin) == 0:
        return 0.0
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_bin)
    for i in range(n_bins):
        b_min, b_max = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (scores >= b_min) & (scores < b_max if i < n_bins - 1 else scores <= b_max)
        if mask.sum() == 0:
            continue
        bin_acc = float(y_bin[mask].mean())
        bin_conf = float(scores[mask].mean())
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def _calibrate_pmap(
    pmap: dict[str, np.ndarray],
    y_inner_val: pd.Series,
    classes: list[str],
) -> dict[str, np.ndarray]:
    calibrated: dict[str, np.ndarray] = {}
    n = max(0, len(y_inner_val))
    yv = y_inner_val.astype(str).to_numpy()

    for c in classes:
        raw_c = pmap.get(c, np.zeros(n))
        if c == "normal":
            calibrated[c] = raw_c
            continue
        c_mask = (yv == c).astype(int)
        if c_mask.sum() >= 50 and len(np.unique(c_mask)) >= 2:
            iso = IsotonicRegression(out_of_bounds="clip")
            calibrated[c] = iso.fit_transform(raw_c, c_mask)
        else:
            _LOG.info("stage2_skipped_n_pos_lt_50", extra={"family": c, "n_pos": int(c_mask.sum())})
            calibrated[c] = raw_c

    # Renormalize probability map per row so sum == 1.0
    if classes and n > 0:
        stacked = np.column_stack([calibrated.get(c, np.zeros(n)) for c in classes])
        sums = stacked.sum(axis=1, keepdims=True)
        sums[sums == 0] = 1.0
        normalized = stacked / sums
        for i, c in enumerate(classes):
            calibrated[c] = normalized[:, i]

    return calibrated


def _cluster_bootstrap_ci(
    split_eval: pd.DataFrame,
    y_eval: pd.Series,
    pmap: dict[str, np.ndarray],
    n_resamples: int = 200,
) -> dict[str, dict[str, float]]:
    """Resample payee IDs for mule/invoice rows, payer IDs otherwise."""
    # Cheapest-by-construction: no .fit() calls below this line — only resample + repredict
    # against the already-fitted model. Cost stays O(n_resamples * n_rows), not O(n_resamples * train).
    out: dict[str, dict[str, float]] = {}
    yv = y_eval.astype(str).to_numpy()
    n = len(yv)
    if n == 0:
        for fam in FRAUD_FAMILIES:
            out[fam] = {"low": float("nan"), "high": float("nan")}
        return out

    payees = split_eval["payee"].astype(str).to_numpy()
    payers = split_eval["payer"].astype(str).to_numpy()
    rng = np.random.default_rng(42)

    for fam in FRAUD_FAMILIES:
        mask = yv == fam
        n_pos = int(mask.sum())
        if n_pos < 1:
            out[fam] = {"low": float("nan"), "high": float("nan")}
            continue

        clusters = payees if fam in {"mule", "invoice_fraud"} else payers
        unique_clusters = np.unique(clusters)

        scores = pmap.get(fam, np.zeros(n))
        aps: list[float] = []

        for _ in range(n_resamples):
            sampled_clusters = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)
            cluster_mask = np.isin(clusters, sampled_clusters)
            sub_y = mask[cluster_mask].astype(int)
            sub_scores = scores[cluster_mask]

            if sub_y.min() != sub_y.max() and len(sub_y) >= 2:
                ap = float(average_precision_score(sub_y, sub_scores))
                aps.append(ap)

        if len(aps) >= 5:
            low = float(np.percentile(aps, 2.5))
            high = float(np.percentile(aps, 97.5))
            if low == high and high < 1.0:
                high = min(1.0, low + 1e-4)
            out[fam] = {"low": low, "high": high}
        else:
            out[fam] = {"low": float("nan"), "high": float("nan")}

    return out


def _app_ablation(
    x_tr: np.ndarray,
    y_tr: pd.Series,
    x_te: np.ndarray,
    y_te: pd.Series,
    raw_tr: pd.DataFrame,
    raw_te: pd.DataFrame,
    recipe: dict[str, Any],
) -> dict[str, Any]:
    y_app_tr = (y_tr.astype(str) == "app_fraud").to_numpy(dtype=int)
    y_app_te = (y_te.astype(str) == "app_fraud").to_numpy(dtype=int)
    flags = [c for c in recipe.get("app_flag_cols", list(APP_FLAG_COLS)) if c in raw_tr.columns]
    col_index = {c: i for i, c in enumerate(raw_tr.columns)}

    def _zero(x: np.ndarray, raw: pd.DataFrame) -> np.ndarray:
        z = x.copy()
        for c in flags:
            i = col_index.get(c)
            if i is not None and i < z.shape[1]:
                z[:, i] = 0.0
        _ = raw
        return z

    def _ap(x_train: np.ndarray, x_test: np.ndarray) -> float:
        if y_app_tr.min() == y_app_tr.max() or y_app_te.min() == y_app_te.max():
            return float("nan")
        m = HistGradientBoostingClassifier(
            max_depth=int(recipe.get("max_depth", 3)),
            max_iter=int(recipe.get("max_iter", 80)),
            learning_rate=float(recipe.get("learning_rate", 0.08)),
            random_state=int(recipe.get("random_state", 42)),
            class_weight="balanced",
        )
        m.fit(x_train, y_app_tr)
        scores = m.predict_proba(x_test)[:, 1]
        return float(average_precision_score(y_app_te, scores))

    with_flags = _ap(x_tr, x_te)
    without = _ap(_zero(x_tr, raw_tr), _zero(x_te, raw_te))
    died = (
        int(y_app_te.sum()) > 0
        and np.isfinite(with_flags)
        and np.isfinite(without)
        and without <= max(0.05, 0.5 * with_flags)
    )
    return {
        "app_flags": flags,
        "with_app_flags": {"average_precision": with_flags},
        "without_app_flags": {"average_precision": without},
        "app_metric_died_without_synthetic_flags": died,
        "note": "Synthetic session flags are not an SDK. Collapse without flags is documented, not hidden.",
    }


def _mule_entity_recall(
    split_eval: pd.DataFrame,
    pred: np.ndarray,
    scores: np.ndarray,
    threshold: float,
) -> float | None:
    from packages.eval.split import MULE_PAYEE_PREFIXES

    payees = split_eval["payee"].astype(str)
    gold = split_eval["label_family"].astype(str) == "mule"
    mule_ids = sorted(
        {
            p
            for p, g in zip(payees, gold, strict=False)
            if g and p.startswith(MULE_PAYEE_PREFIXES)
        }
    )
    if not mule_ids:
        return None
    caught = 0
    pred_s = pd.Series(pred, index=split_eval.index)
    sc = pd.Series(scores, index=split_eval.index)
    for mid in mule_ids:
        inbound = payees == mid
        hit = ((pred_s == "mule") | (sc >= threshold)) & inbound
        if bool(hit.any()):
            caught += 1
    return float(caught / len(mule_ids))


def _bench_ms(model: HistGradientBoostingClassifier, x: np.ndarray, hang_s: float) -> dict[str, Any]:
    n_target = 1000
    if x.shape[0] == 0:
        return {"p50_ms_per_row": float("nan"), "p99_ms_per_row": float("nan"), "n": 0, "batch_seconds_1k": 0.0}
    reps = int(np.ceil(n_target / x.shape[0]))
    xt = np.vstack([x] * max(reps, 1))[:n_target]
    t0 = time.perf_counter()
    model.predict_proba(xt)
    batch_s = time.perf_counter() - t0
    if batch_s > hang_s:
        raise TimeoutError(f"AuthGate hang: {batch_s:.1f}s to score {len(xt)} rows (limit {hang_s}s)")
    sample_n = min(200, len(xt))
    times = []
    for i in range(sample_n):
        t1 = time.perf_counter()
        model.predict_proba(xt[i : i + 1])
        times.append((time.perf_counter() - t1) * 1000.0)
    return {
        "p50_ms_per_row": float(np.percentile(times, 50)),
        "p99_ms_per_row": float(np.percentile(times, 99)),
        "n": len(xt),
        "batch_seconds_1k": float(batch_s),
        "note": "Laptop in-process predict. Not a Mastercard issuer SLA.",
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items() if str(k) not in JSON_BAN}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return "NaN"
    return value


def _atomic_write_json(path: Path, payload: Any) -> None:
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def assert_no_denylist_payload(payload: dict[str, Any]) -> None:
    blob = json.dumps(payload, default=str)
    for banned in ("simulatable_signals", "is_authorized_push", "economic_class"):
        if banned in blob:
            raise AssertionError(f"denylist key leaked into Defend JSON: {banned}")


def _metrics_pass(metrics: dict[str, Any], hang_s: float) -> bool:
    """
    Hard metrics contract (Ticket 2). A missing required key flips pass -> False.

    JSON NaN convention: every non-finite float serializes as the string "NaN"
    (never null, which would read as "missing"). Consumers parse it as
    float("NaN") -> not finite. E.g. ap_by_family[fam] == "NaN" iff n_pos == 0.

    Also attaches a non-breaking metrics["pass_reasons"] naming each missing key
    or failed check so a CI failure is self-diagnosing.
    """
    reasons: list[str] = []
    required = (
        "ap_by_family",
        "n_pos",
        "not_comparable",
        "tpr_at_fpr",
        "genuine_fp",
        "f1_at_op",
        "app_ablation",
        "authgate_ms",
        "mule_entity_recall",
        "protocol",
        "inner_val_protocol",
        "recipe_hash",
    )
    for key in required:
        if key not in metrics:
            reasons.append(f"missing:{key}")
    tpr = metrics.get("tpr_at_fpr") or {}
    for key in ("0.001", "0.005", "0.01"):
        if key not in tpr:
            reasons.append(f"missing:tpr_at_fpr.{key}")
    n_pos = metrics.get("n_pos") or {}
    for fam in ALL_FAMILIES:
        if fam not in n_pos:
            reasons.append(f"missing:n_pos.{fam}")
    not_cmp = metrics.get("not_comparable") or {}
    for fam in FRAUD_FAMILIES:
        if fam not in not_cmp:
            reasons.append(f"missing:not_comparable.{fam}")
    ablation = metrics.get("app_ablation") or {}
    for key in ("with_app_flags", "without_app_flags", "app_metric_died_without_synthetic_flags"):
        if key not in ablation:
            reasons.append(f"missing:app_ablation.{key}")
    bench = metrics.get("authgate_ms") or {}
    for key in ("p50_ms_per_row", "p99_ms_per_row", "batch_seconds_1k"):
        if key not in bench:
            reasons.append(f"missing:authgate_ms.{key}")
    if float(bench.get("batch_seconds_1k") or 0) > hang_s:
        reasons.append(f"authgate_hang:{bench.get('batch_seconds_1k')}")
    metrics["pass_reasons"] = reasons
    return not reasons


def fit_champion(
    run_id: str,
    *,
    world_seed: int = 42,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    force_train_event_ids: frozenset[str] | None = None,
    override_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recipe = load_recipe()
    r_hash = _recipe_hash()
    paths = run_paths(run_id, runs_dir)
    if not paths["train"].is_file() or not paths["split"].is_file():
        raise FileNotFoundError(f"missing train/split for run_id={run_id}")
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    extra = set(train_df.columns) - set(TRAIN_ALLOWLIST)
    if extra:
        raise AssertionError(f"train cols outside allowlist: {extra}")
    rules = load_v0_rules()
    train_df = _attach_rule_bits(train_df, rules)
    packed = folds_from_run(
        train_df, split_df, seed=world_seed, force_train_event_ids=force_train_event_ids
    )
    x_tr_raw, y_tr = packed["X_train"], packed["y_train"]
    x_ev_raw, y_ev = packed["X_eval"], packed["y_eval"]
    inner = inner_folds_from_train(split_df.reset_index(drop=True), packed["folds"].reset_index(drop=True))
    inner_fit_mask = (inner == "inner_fit").to_numpy()
    inner_val_mask = (inner == "inner_val").to_numpy()
    _LOG.info("threshold_fit", extra={"fold": "inner_folds", "inner_fit_n": int(inner_fit_mask.sum()), "inner_val_n": int(inner_val_mask.sum())})
    for fam in pd.concat([y_tr, y_ev]).unique():
        if fam in TECHNIQUE_IDS:
            raise AssertionError(f"y leaked technique id {fam}")
        if fam not in LABEL_FAMILIES:
            raise AssertionError(f"unknown label_family {fam}")
    assert_no_x_leak(x_tr_raw.columns)
    cat_cols = [c for c in CAT_COLS if c in x_tr_raw.columns]
    x_tr, encoder = _encode(x_tr_raw, encoder=None, cat_cols=cat_cols, fit=True)
    x_ev, encoder = _encode(x_ev_raw, encoder=encoder, cat_cols=cat_cols, fit=False)

    dest = (models_dir or MODELS_DIR) / run_id
    dest.mkdir(parents=True, exist_ok=True)

    tuned_params = dict(override_params or {})
    best_params_file = dest / "best_params.json"
    if not tuned_params and best_params_file.is_file():
        try:
            bdata = json.loads(best_params_file.read_text(encoding="utf-8"))
            if bdata.get("status") == "success" and bdata.get("best_params"):
                tuned_params = bdata["best_params"]
        except Exception:
            pass

    weights = _class_weight(y_tr)
    # Deterministic weight assertion — same y must produce identical weights
    assert _class_weight(y_tr) == weights, "_class_weight must be deterministic"
    hgb_kwargs = dict(
        max_depth=int(tuned_params.get("max_depth", recipe.get("max_depth", 3))),
        max_iter=int(tuned_params.get("max_iter", recipe.get("max_iter", 80))),
        learning_rate=float(tuned_params.get("learning_rate", recipe.get("learning_rate", 0.08))),
        random_state=int(recipe.get("random_state", 42)),
        early_stopping=False,
    )
    # --- Inner fold masks relative to train-only rows ---
    train_idx = (packed["folds"].reset_index(drop=True) == "train")
    inner_of_train = inner[train_idx.to_numpy()].reset_index(drop=True)
    ifit_mask = (inner_of_train == "inner_fit").to_numpy()
    ival_mask = (inner_of_train == "inner_val").to_numpy()
    # --- Step 1: fit on inner_fit only (for threshold selection) ---
    x_ifit_raw = x_tr_raw.iloc[ifit_mask].reset_index(drop=True)
    y_ifit = y_tr.iloc[ifit_mask].reset_index(drop=True)
    x_ival_raw = x_tr_raw.iloc[ival_mask].reset_index(drop=True)
    y_ival = y_tr.iloc[ival_mask].reset_index(drop=True)
    x_ifit, enc_inner = _encode(x_ifit_raw, encoder=None, cat_cols=cat_cols, fit=True)
    inner_sw = y_ifit.astype(str).map(weights).to_numpy(dtype=float)
    inner_model = HistGradientBoostingClassifier(**hgb_kwargs)
    inner_model.fit(x_ifit, y_ifit.astype(str).to_numpy(), sample_weight=inner_sw)
    _LOG.info("threshold_fit", extra={"fold": "inner_fit", "n_rows": len(y_ifit)})
    # --- Step 2: compute op_threshold from inner_val scores ---
    x_ival, _ = _encode(x_ival_raw, encoder=enc_inner, cat_cols=cat_cols, fit=False)
    inner_pmap = _proba_map(inner_model, x_ival)
    inner_y_bin = (y_ival.astype(str) != "normal").to_numpy(dtype=int)
    # Stage 1 isotonic: fit threshold on CALIBRATED inner-val scores (ssot Ticket 9).
    ival_classes = [str(c) for c in inner_model.classes_]
    inner_cal_pmap = _calibrate_pmap(inner_pmap, y_ival, ival_classes)
    inner_scores = _fraud_score(inner_cal_pmap, len(y_ival))
    op_fpr = float(recipe.get("operating_point_fpr", 0.01))
    inner_op = _tpr_at_fpr(inner_y_bin, inner_scores, op_fpr)
    thr = float(inner_op.get("threshold") or 1.0)
    _LOG.info("threshold_fit", extra={"fold": "inner_val", "n_rows": len(y_ival), "op_threshold": thr})

    # --- Isolation Forest anomaly detector (Ticket 8, kill switch aware) ---
    iso_model = fit_isolation_forest(x_ifit_raw, y_ifit)
    iso_notify_rate = check_iso_genuine_notify_rate(iso_model, x_ival_raw, y_ival)
    iso_cfg = recipe.get("isolation_forest") or {}
    iso_enabled = iso_enabled_flag(iso_cfg, iso_notify_rate)
    _LOG.info(
        "isolation_forest_fit",
        extra={"notify_rate": iso_notify_rate, "enabled": iso_enabled, "enabled_default": iso_cfg.get("enabled_default")},
    )

    # --- Step 3: refit on full outer train with frozen threshold ---
    sample_weight = y_tr.astype(str).map(weights).to_numpy(dtype=float)
    model = HistGradientBoostingClassifier(**hgb_kwargs)
    model.fit(x_tr, y_tr.astype(str).to_numpy(), sample_weight=sample_weight)
    classes = [str(c) for c in model.classes_]
    # --- Step 4: outer eval ---
    raw_pmap = _proba_map(model, x_ev)
    raw_scores = _fraud_score(raw_pmap, len(y_ev))
    y_bin = (y_ev.astype(str) != "normal").to_numpy(dtype=int)

    ece_before = _compute_ece(y_bin, raw_scores)
    calibrated_pmap = _calibrate_pmap(raw_pmap, y_ival, classes)
    calibrated_scores = _fraud_score(calibrated_pmap, len(y_ev))
    ece_after = _compute_ece(y_bin, calibrated_scores)

    pmap = calibrated_pmap
    scores = calibrated_scores
    pred = _pred_family(pmap, classes, len(y_ev))

    _LOG.info("outer_eval_metrics", extra={"fold": "eval", "n_rows": len(y_ev)})
    tpr_block = {
        f"{t:g}": _tpr_at_fpr(y_bin, scores, t) for t in recipe.get("tpr_at_fpr", [0.001, 0.005, 0.01])
    }
    yhat = (scores >= thr).astype(int)
    genuine = y_ev.astype(str) == "normal"
    genuine_fp = float(((yhat == 1) & genuine.to_numpy()).mean()) if genuine.any() else float("nan")
    f1 = float(f1_score(y_bin, yhat, zero_division=0))
    split_eval = split_df.reset_index(drop=True).loc[packed["folds"].reset_index(drop=True) == "eval"]
    hang_s = float(recipe.get("hang_guard_seconds_1k", 120))
    bench = _bench_ms(model, x_ev, hang_s)
    ablation = _app_ablation(x_tr, y_tr, x_ev, y_ev, x_tr_raw, x_ev_raw, recipe)
    mule_rec = _mule_entity_recall(split_eval, pred, scores, thr)

    # Permutation importance on inner_val (Ticket 10)
    top = _top_features(inner_model, x_ival, y_ival, x_tr_raw.columns)
    # Cluster bootstrap CI (Ticket 10)
    bootstrap_ci = _cluster_bootstrap_ci(split_eval, y_ev, pmap)

    n_pos = _n_pos_by_family(y_ev)
    not_comparable = _not_comparable(n_pos, int(recipe.get("n_pos_not_comparable_below", 30)))
    _, fp_hist = _brake_action_hist(
        x_ev_raw, y_ev, split_eval["payee"], pred, scores, thr, rules,
        iso_model=iso_model if iso_enabled else None, pmap=pmap,
    )
    cost_sketch = _cost_sketch(
        n_total=len(y_ev),
        n_fraud=int(y_bin.sum()),
        n_fn=int(((y_bin == 1) & (yhat == 0)).sum()),
        fp_action_hist=fp_hist,
    )

    champ = Champion(
        model=model,
        encoder=encoder,
        raw_columns=list(x_tr_raw.columns),
        cat_cols=cat_cols,
        classes=classes,
        op_threshold=thr,
        fold_seed=world_seed,
        rule_ids=[r.id for r in rules if r.status == "live"],
        top_features=top,
        recipe=recipe,
        iso_model=iso_model if iso_enabled else None,
        isolation_forest_enabled=iso_enabled,
    )
    joblib.dump(champ, dest / "champion.joblib")
    _atomic_write_json(dest / "model_manifest.json", {"recipe_hash": r_hash, "run_id": run_id})
    metrics = {
        "pass": False,
        "schema_version": METRICS_SCHEMA_VERSION,
        "protocol": packed["protocol"],
        "estimator": recipe["estimator"],
        "n_train": len(y_tr),
        "n_eval": len(y_ev),
        "class_weight": weights,
        "ap_by_family": _ap_by_family(y_ev, pmap),
        "n_pos": n_pos,
        "not_comparable": not_comparable,
        "cost_sketch": cost_sketch,
        "tpr_at_fpr": tpr_block,
        "genuine_fp": genuine_fp,
        "f1_at_op": f1,
        "operating_point_fpr": op_fpr,
        "op_threshold": thr,
        "app_ablation": ablation,
        "authgate_ms": bench,
        "mule_entity_recall": mule_rec,
        "feature_columns": list(x_tr_raw.columns),
        "top_features": top,
        "split": packed["protocol"],
        "inner_val_protocol": "last_20pct_train_calendar",
        "diagnostic_ap_by_family": _ap_by_family(y_ev, pmap),
        "recipe_hash": r_hash,
        "ece_before": ece_before,
        "ece_after": ece_after,
        "bootstrap_ci": bootstrap_ci,
        "isolation_forest_enabled": iso_enabled,
    }
    metrics["pass"] = _metrics_pass(metrics, hang_s)
    _atomic_write_json(dest / "metrics.json", _jsonable(metrics))
    _atomic_write_json(
        dest / "features.json",
        {
            **recipe,
            "run_id": run_id,
            "feature_columns": list(x_tr_raw.columns),
            "classes": classes,
            "op_threshold": thr,
        },
    )
    fit_body = {
        "run_id": run_id,
        "model_run_id": run_id,
        "model_dir": str(dest),
        "metrics": _jsonable(metrics),
        "split": packed["protocol"],
        "recipe_hash": r_hash,
    }
    assert_no_denylist_payload(fit_body)
    return fit_body


def _opened_run_world_seed(paths: dict[str, Path]) -> int:
    """Read a run's sidecar world_seed. Tests monkeypatch this as a sentinel gate."""
    sidecar_path = paths["sidecar"]
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8")) if sidecar_path.is_file() else {}
    return int(sidecar.get("world_seed", 42))


def tune_champion(
    run_id: str,
    *,
    world_seed: int = 42,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    n_trials: int | None = None,
    timeout: float | None = None,
    min_inner_val_fraud_pos: int = 50,
    force_skip: bool = False,
    ci: bool = False,
    random_state: int = 42,
) -> dict[str, Any]:
    """Ticket 5 — bounded Optuna HGB search on inner_val only.

    Objective (locked, never family-AP min):

        objective = binary_AP(inner_val) - 10.0 * max(0, genuine_fp - 0.01)

    Writes models/{run_id}/best_params.json, then refits the champion on the
    full outer train with the tuned params. The inner-val op_threshold stays
    frozen exactly as Phase 3 produced it (tuning never touches the threshold).

    Stop-gate: never opens any parquet whose sidecar world_seed == 43 (G-test).
    Stop-gate: the Optuna study object is never required by score_run — the
    tuned params are persisted as best_params.json and baked into champion.joblib.
    """
    recipe = load_recipe()
    r_hash = _recipe_hash()
    flags = load_ml_flags(recipe)
    if n_trials is None:
        n_trials = select_n_trials(flags, ci=ci)
    if timeout is None:
        timeout = flags["optuna_timeout_seconds"]
    if min_inner_val_fraud_pos is None:
        flags_opt = recipe.get("optuna") or {}
        min_inner_val_fraud_pos = int(flags_opt.get("min_inner_val_fraud_pos", 50))

    paths = run_paths(run_id, runs_dir)
    if _opened_run_world_seed(paths) == 43:
        raise ValueError("tune_champion refuses to open G-test run (sidecar world_seed==43)")
    if not paths["train"].is_file() or not paths["split"].is_file():
        raise FileNotFoundError(f"missing train/split for run_id={run_id}")

    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    extra = set(train_df.columns) - set(TRAIN_ALLOWLIST)
    if extra:
        raise AssertionError(f"train cols outside allowlist: {extra}")
    rules = load_v0_rules()
    train_df = _attach_rule_bits(train_df, rules)
    packed = folds_from_run(train_df, split_df, seed=world_seed)
    x_tr_raw, y_tr = packed["X_train"], packed["y_train"]
    x_ev_raw, y_ev = packed["X_eval"], packed["y_eval"]
    for fam in pd.concat([y_tr, y_ev]).unique():
        if fam in TECHNIQUE_IDS:
            raise AssertionError(f"y leaked technique id {fam}")
        if fam not in LABEL_FAMILIES:
            raise AssertionError(f"unknown label_family {fam}")
    assert_no_x_leak(x_tr_raw.columns)
    cat_cols = [c for c in CAT_COLS if c in x_tr_raw.columns]

    inner = inner_folds_from_train(split_df.reset_index(drop=True), packed["folds"].reset_index(drop=True))
    train_idx = (packed["folds"].reset_index(drop=True) == "train").to_numpy()
    inner_of_train = inner[train_idx].reset_index(drop=True)
    ifit_mask = (inner_of_train == "inner_fit").to_numpy()
    ival_mask = (inner_of_train == "inner_val").to_numpy()
    x_ifit_raw = x_tr_raw.iloc[ifit_mask].reset_index(drop=True)
    y_ifit = y_tr.iloc[ifit_mask].reset_index(drop=True)
    x_ival_raw = x_tr_raw.iloc[ival_mask].reset_index(drop=True)
    y_ival = y_tr.iloc[ival_mask].reset_index(drop=True)

    x_ifit, enc_inner = _encode(x_ifit_raw, encoder=None, cat_cols=cat_cols, fit=True)
    x_ival, _ = _encode(x_ival_raw, encoder=enc_inner, cat_cols=cat_cols, fit=False)
    y_ifit_s = y_ifit.astype(str).to_numpy()
    inner_y_bin = (y_ival.astype(str) != "normal").to_numpy(dtype=int)
    op_fpr = float(recipe.get("operating_point_fpr", 0.01))

    n_fraud_val = int(inner_y_bin.sum())
    skipped_small_n = bool(force_skip or n_fraud_val < min_inner_val_fraud_pos)
    if skipped_small_n:
        _LOG.info("optuna_skipped_small_n", extra={"run_id": run_id, "inner_val_fraud_pos": n_fraud_val, "min": min_inner_val_fraud_pos})
        params = {
            "max_depth": int(recipe.get("max_depth", 3)),
            "max_iter": int(recipe.get("max_iter", 80)),
            "learning_rate": float(recipe.get("learning_rate", 0.08)),
        }
        best_params = params
        direction = None
    else:
        weights = _class_weight(y_tr)
        inner_sw = y_ifit.astype(str).map(weights).to_numpy(dtype=float)

        def _objective(trial: Any) -> float:
            p = {
                "max_depth": trial.suggest_categorical("max_depth", [2, 3, 4, 5]),
                "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
                "max_iter": trial.suggest_int("max_iter", 40, 200),
            }
            m = HistGradientBoostingClassifier(
                max_depth=p["max_depth"],
                learning_rate=p["learning_rate"],
                max_iter=p["max_iter"],
                random_state=random_state,
                early_stopping=False,
            )
            m.fit(x_ifit, y_ifit_s, sample_weight=inner_sw)
            pmap = _proba_map(m, x_ival)
            cal_pmap = _calibrate_pmap(pmap, y_ival, [str(c) for c in m.classes_])
            scores = _fraud_score(cal_pmap, len(y_ival))
            binary_ap = float(average_precision_score(inner_y_bin, scores))
            op_thr = float(_tpr_at_fpr(inner_y_bin, scores, op_fpr).get("threshold") or 1.0)
            genuine = inner_y_bin == 0
            genuine_fp = float(np.mean(scores[genuine] >= op_thr)) if genuine.any() else 0.0
            return binary_ap - 10.0 * max(0.0, genuine_fp - 0.01)

        import optuna

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=random_state),
            study_name=f"tune-{run_id}",
        )
        study.optimize(_objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)
        best_params = dict(study.best_params)
        direction = "maximize"

    dest = (models_dir or MODELS_DIR) / run_id
    dest.mkdir(parents=True, exist_ok=True)
    best_payload = {
        "run_id": run_id,
        "status": "success",
        "optuna_skipped_small_n": skipped_small_n,
        "inner_val_fraud_pos": n_fraud_val,
        "n_trials": n_trials if not skipped_small_n else 0,
        "timeout_seconds": timeout if not skipped_small_n else 0,
        "direction": direction,
        "recipe_hash": r_hash,
        "best_params": best_params,
    }
    _atomic_write_json(dest / "best_params.json", best_payload)

    fit_champion(
        run_id,
        world_seed=world_seed,
        runs_dir=runs_dir,
        models_dir=models_dir,
        override_params=best_params,
    )
    return {
        "run_id": run_id,
        "optuna_skipped_small_n": skipped_small_n,
        "inner_val_fraud_pos": n_fraud_val,
        "best_params": best_params,
        "recipe_hash": r_hash,
        "best_params_path": str(dest / "best_params.json"),
    }


def load_champion(model_run_id: str, models_dir: Path | None = None) -> Champion:
    base = (models_dir or MODELS_DIR) / model_run_id
    path = base / "champion.joblib"
    if not path.is_file():
        raise FileNotFoundError(f"no champion for model_run_id={model_run_id}")
    manifest_path = base / "model_manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        current_hash = _recipe_hash()
        frozen_hash = manifest.get("recipe_hash", "")
        if frozen_hash and current_hash != frozen_hash:
            raise RecipeHashMismatchError(
                f"features.json changed after model was frozen "
                f"(frozen={frozen_hash[:16]}… current={current_hash[:16]}…). "
                f"Refusing to score — retrain or revert features.json."
            )
    return joblib.load(path)


def score_run(
    run_id: str,
    *,
    model_run_id: str | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    all_rows: bool = False,
) -> dict[str, Any]:
    mid = model_run_id or run_id
    champ = load_champion(mid, models_dir=models_dir)
    paths = run_paths(run_id, runs_dir)
    train_df = pd.read_parquet(paths["train"])
    split_df = pd.read_parquet(paths["split"])
    rules = load_v0_rules()
    train_df = _attach_rule_bits(train_df, rules)
    if all_rows:
        y_ev = train_df["label_family"].astype(str)
        x_ev_raw = train_df.drop(columns=["label_family"])
        x_ev_raw = x_ev_raw.reindex(columns=champ.raw_columns, fill_value=0)
        assert_no_x_leak(x_ev_raw.columns)
        protocol = "g_test_full_population"
        split_eval = split_df.reset_index(drop=True)
        x_tr_raw, y_tr = x_ev_raw, y_ev
    else:
        packed = folds_from_run(train_df, split_df, seed=champ.fold_seed)
        x_ev_raw, y_ev = packed["X_eval"], packed["y_eval"]
        x_ev_raw = x_ev_raw.reindex(columns=champ.raw_columns, fill_value=0)
        assert_no_x_leak(x_ev_raw.columns)
        protocol = packed["protocol"]
        split_eval = split_df.reset_index(drop=True).loc[packed["folds"].reset_index(drop=True) == "eval"]
        x_tr_raw, y_tr = packed["X_train"], packed["y_train"]
        x_tr_raw = x_tr_raw.reindex(columns=champ.raw_columns, fill_value=0)

    x_ev, _ = _encode(x_ev_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x_ev)
    scores = _fraud_score(pmap, len(y_ev))
    pred = _pred_family(pmap, champ.classes, len(y_ev))
    y_bin = (y_ev.astype(str) != "normal").to_numpy(dtype=int)
    recipe = champ.recipe
    tpr_block = {
        f"{t:g}": _tpr_at_fpr(y_bin, scores, t) for t in recipe.get("tpr_at_fpr", [0.001, 0.005, 0.01])
    }
    thr = champ.op_threshold
    yhat = (scores >= thr).astype(int)
    genuine = y_ev.astype(str) == "normal"
    genuine_fp = float(((yhat == 1) & genuine.to_numpy()).mean()) if genuine.any() else float("nan")
    hang_s = float(recipe.get("hang_guard_seconds_1k", 120))
    bench = _bench_ms(champ.model, x_ev, hang_s)
    if all_rows:
        champion_metrics_path = (models_dir or MODELS_DIR) / mid / "metrics.json"
        if not champion_metrics_path.is_file():
            raise FileNotFoundError(f"cannot copy G-test ablation: {mid} has no metrics.json")
        champ_metrics = json.loads(champion_metrics_path.read_text(encoding="utf-8"))
        ablation = dict(champ_metrics.get("app_ablation") or {})
        ablation["app_ablation_source"] = "champion_fit"
    else:
        x_tr, _ = _encode(x_tr_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
        ablation = _app_ablation(x_tr, y_tr, x_ev, y_ev, x_tr_raw, x_ev_raw, recipe)

    iso_model_pass = champ.iso_model if (getattr(champ, "isolation_forest_enabled", None) is True) else None
    hist, fp_hist = _brake_action_hist(
        x_ev_raw, y_ev, split_eval["payee"], pred, scores, thr, rules,
        iso_model=iso_model_pass, pmap=pmap if iso_model_pass is not None else None,
    )
    n_pos = _n_pos_by_family(y_ev)
    not_comparable = _not_comparable(n_pos, int(recipe.get("n_pos_not_comparable_below", 30)))
    cost_sketch = _cost_sketch(
        n_total=len(y_ev),
        n_fraud=int(y_bin.sum()),
        n_fn=int(((y_bin == 1) & (yhat == 0)).sum()),
        fp_action_hist=fp_hist,
    )

    metrics = {
        "pass": False,
        "schema_version": METRICS_SCHEMA_VERSION,
        "protocol": protocol,
        "n_eval": len(y_ev),
        "ap_by_family": _ap_by_family(y_ev, pmap),
        "n_pos": n_pos,
        "not_comparable": not_comparable,
        "cost_sketch": cost_sketch,
        "tpr_at_fpr": tpr_block,
        "genuine_fp": genuine_fp,
        "f1_at_op": float(f1_score(y_bin, yhat, zero_division=0)),
        "app_ablation": ablation,
        "authgate_ms": bench,
        "mule_entity_recall": _mule_entity_recall(split_eval, pred, scores, thr),
        "feature_columns": list(champ.raw_columns),
        "top_features": champ.top_features,
        "split": protocol,
    }
    metrics["pass"] = _metrics_pass(metrics, hang_s)
    metrics_json = _jsonable(metrics)
    body = {
        "run_id": run_id,
        "model_run_id": mid,
        "metrics": metrics_json,
        "action_histogram": hist,
        "split": protocol,
    }
    if all_rows:
        sidecar = {}
        if paths["sidecar"].is_file():
            sidecar = json.loads(paths["sidecar"].read_text(encoding="utf-8"))
        headline_keys = (
            "ap_by_family",
            "n_pos",
            "not_comparable",
            "genuine_fp",
            "tpr_at_fpr",
            "app_ablation",
            "mule_entity_recall",
            "authgate_ms",
            "cost_sketch",
        )
        body["gtest"] = {
            "world_seed": sidecar.get("world_seed"),
            "run_id": run_id,
            **{key: metrics_json[key] for key in headline_keys},
        }
    assert_no_denylist_payload(body)
    return body
