"""Champion GBDT fit + metrics (Plan 12 Phase C). One HGB recipe, no AutoGluon."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_curve,
)
from sklearn.preprocessing import OrdinalEncoder

from packages.config.ml import load_ml_flags, select_n_trials
from packages.eval.brake import APP_HOLD_SCORE, ATO_DECLINE_SCORE, HUB_PAYEE_PREFIX, as_record, brake
from packages.eval.iso_check import (
    apply_iso_brake_upgrade,
    check_iso_genuine_notify_rate,
    fit_isolation_forest,
    is_iso_anomaly,
    iso_enabled_flag,
    predict_iso_anomalies_batch,
)
from packages.eval.split import (
    assert_fold_n_pos,
    assert_no_x_leak,
    folds_from_run,
    inner_folds_from_train,
    preflight_fold_floors,
    split_inner_val_ab,
)
from packages.policy.rules import Rule, evaluate_rules, load_v0_rules, vectorized_rule_bits
from packages.sim.ablation import APP_FLAG_COLS
from packages.sim.export import RUNS_DIR, TRAIN_ALLOWLIST, TRAIN_DENYLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS

_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = _ROOT / "models"
RECIPE_PATH = MODELS_DIR / "features.json"
V0_RECIPE_PATH = MODELS_DIR / "features.v0.json"
FROZEN_V0_RECIPE_HASH = (
    "19ec558dd466815531f4fb4390a858ff7a7ad32b46376ed50faeaab84c87b65e"
)
DEFAULT_ACT_THR = 0.5
RESERVED_WORLD_SEEDS = frozenset({43, 46, 47, 48, 49})
CAT_COLS = ("rail", "kyc_tier")
ALL_FAMILIES = tuple(sorted(LABEL_FAMILIES))
FRAUD_FAMILIES = tuple(sorted(LABEL_FAMILIES - {"normal"}))
METRICS_SCHEMA_VERSION = "2"
FP_COST_ACTIONS = ("notify", "hold", "decline")
JSON_BAN = frozenset(TRAIN_DENYLIST) | {
    "knobs_used",
    "knobs_pinned",
    "knobs",
    "simulatable_signals",
}


class RecipeHashMismatchError(RuntimeError):
    """features.json changed after the model was frozen — refuse to score."""


class GtestFreezeMismatchError(RuntimeError):
    """G-test already opened for a different model_freeze_id on this model_run_id."""


def _recipe_hash(path: Path | None = None) -> str:
    """SHA-256 of the raw features.json bytes — ties metrics to frozen config."""
    raw = (path or RECIPE_PATH).read_bytes()
    return hashlib.sha256(raw).hexdigest()


def _recipe_hash_accepted(frozen_hash: str) -> bool:
    """Accept museum v0 hash when exact frozen bytes live in features.v0.json."""
    if not frozen_hash:
        return True
    if _recipe_hash() == frozen_hash:
        return True
    if V0_RECIPE_PATH.is_file() and _recipe_hash(V0_RECIPE_PATH) == frozen_hash:
        return True
    if frozen_hash == FROZEN_V0_RECIPE_HASH and V0_RECIPE_PATH.is_file():
        return True
    wip = MODELS_DIR / "features.wip.json"
    if wip.is_file() and _recipe_hash(wip) == frozen_hash:
        return True
    return False


def _act_threshold(recipe: dict[str, Any] | None) -> float:
    rec = recipe or {}
    val = rec.get("act_thr")
    if val is None:
        val = (rec.get("thresholds") or {}).get("act_thr")
    try:
        return float(val) if val is not None else DEFAULT_ACT_THR
    except (TypeError, ValueError):
        return DEFAULT_ACT_THR


def _canonical_hgb_params(params: dict[str, Any], recipe: dict[str, Any] | None = None) -> dict[str, Any]:
    rec = recipe or {}
    out: dict[str, Any] = {
        "max_iter": int(params.get("max_iter", rec.get("max_iter", 80))),
        "learning_rate": float(params.get("learning_rate", rec.get("learning_rate", 0.08))),
        "random_state": int(params.get("random_state", rec.get("random_state", 42))),
        "early_stopping": False,
    }
    if params.get("max_leaf_nodes") is not None:
        out["max_leaf_nodes"] = int(params["max_leaf_nodes"])
    else:
        out["max_depth"] = int(params.get("max_depth", rec.get("max_depth", 3)))
    for key in ("min_samples_leaf", "l2_regularization", "max_bins"):
        if key in params:
            out[key] = params[key]
    return out


def _model_freeze_id(
    *,
    recipe_hash: str,
    best_params: dict[str, Any],
    op_threshold: float,
    recipe: dict[str, Any] | None = None,
) -> str:
    """G-test identity: features + HGB params + inner-val op_threshold."""
    payload = {
        "best_params": _canonical_hgb_params(best_params, recipe),
        "op_threshold": float(op_threshold),
        "recipe_hash": recipe_hash,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _best_params_from_champion(champ: Champion, champ_metrics: dict[str, Any]) -> dict[str, Any]:
    stored = champ_metrics.get("best_params")
    if isinstance(stored, dict) and stored:
        return _canonical_hgb_params(stored, champ.recipe)
    p = champ.model.get_params()
    return _canonical_hgb_params(
        {
            "max_depth": p.get("max_depth"),
            "max_iter": p.get("max_iter"),
            "learning_rate": p.get("learning_rate"),
            "random_state": p.get("random_state"),
            "early_stopping": False,
        },
        champ.recipe,
    )


def _genuine_fp_rate(yhat: np.ndarray, genuine: np.ndarray) -> float:
    """FP rate on label_family == normal rows (VALIDATION.md), not fp/n_eval."""
    n_normal = int(np.asarray(genuine).sum())
    if n_normal == 0:
        return float("nan")
    return float(((np.asarray(yhat) == 1) & np.asarray(genuine)).sum() / n_normal)


def _genuine_fp_over_eval(yhat: np.ndarray, n_eval: int) -> float:
    """Back-compat fp/n_eval for v0 museum comparison."""
    if n_eval <= 0:
        return float("nan")
    return float((np.asarray(yhat) == 1).sum() / n_eval)


def _binary_op_metrics(y_bin: np.ndarray, scores: np.ndarray, yhat: np.ndarray) -> dict[str, Any]:
    tn = fp = fn = tp = 0
    if len(y_bin) > 0:
        cm = confusion_matrix(y_bin, yhat, labels=[0, 1])
        tn, fp, fn, tp = (int(x) for x in cm.ravel())
    try:
        ap = float(average_precision_score(y_bin, scores))
    except ValueError:
        ap = float("nan")
    return {
        "binary_ap": ap,
        "precision_at_op": float(precision_score(y_bin, yhat, zero_division=0)),
        "recall_at_op": float(recall_score(y_bin, yhat, zero_division=0)),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def _gtest_protocol_path(model_run_id: str, models_dir: Path | None = None) -> Path:
    return (models_dir or MODELS_DIR) / model_run_id / "gtest_protocol.json"


def _load_gtest_protocol(model_run_id: str, models_dir: Path | None = None) -> dict[str, Any]:
    path = _gtest_protocol_path(model_run_id, models_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _gtest_score_path(model_run_id: str, models_dir: Path | None = None) -> Path:
    return (models_dir or MODELS_DIR) / model_run_id / "gtest_score.json"


def _record_gtest_opened(
    model_run_id: str,
    *,
    recipe_hash: str,
    model_freeze_id: str,
    world_seed: int,
    gtest_run_id: str,
    models_dir: Path | None = None,
) -> str:
    """Log first G-test photograph per model_run_id + model_freeze_id."""
    path = _gtest_protocol_path(model_run_id, models_dir)
    existing = _load_gtest_protocol(model_run_id, models_dir)
    if existing.get("gtest_opened_at"):
        stored = existing.get("model_freeze_id")
        if not stored:
            raise GtestFreezeMismatchError(
                f"G-test already opened for model_run_id={model_run_id} without "
                f"model_freeze_id (legacy protocol). Treat as exploratory; photograph "
                f"a new model_run_id or make-gconfirm seed 45."
            )
        if stored != model_freeze_id:
            raise GtestFreezeMismatchError(
                f"G-test already opened for a different freeze on model_run_id={model_run_id} "
                f"(stored={str(stored)[:16]}… current={model_freeze_id[:16]}…). "
                f"Fit the new params to a new model_run_id (tune dest_run_id) or use seed 45."
            )
        return str(existing["gtest_opened_at"])
    opened_at = datetime.now(UTC).isoformat()
    payload = {
        "gtest_opened_at": opened_at,
        "recipe_hash": recipe_hash,
        "model_freeze_id": model_freeze_id,
        "world_seed": int(world_seed),
        "gtest_run_id": gtest_run_id,
    }
    _atomic_write_json(path, payload)
    return opened_at


_LOG = logging.getLogger(__name__)


@contextmanager
def _stage(name: str):
    """Timed stderr stage log for defend-fit visibility."""
    t0 = time.perf_counter()
    print(f"[fit] start {name}", file=sys.stderr, flush=True)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        print(f"[fit] done {name} ({elapsed:.1f}s)", file=sys.stderr, flush=True)


def _perm_repeats() -> int:
    """Optional env override without touching features.json (recipe_hash frozen)."""
    raw = os.environ.get("AEGIS_PERM_REPEATS")
    if raw is None or raw == "":
        return 10
    return int(raw)


def _bootstrap_resamples() -> int:
    """Optional env override without touching features.json (recipe_hash frozen)."""
    # AEGIS_BOOTSTRAP_RESAMPLES — optional override; empty → 200
    raw = os.environ.get("AEGIS_BOOTSTRAP_RESAMPLES")
    if raw is None or raw == "":
        return 200
    return int(raw)


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
    detect_thr: float | None = None
    act_thr: float | None = None
    iso_model: Any | None = None
    isolation_forest_enabled: bool | None = None
    pmap_calibrators: dict[str, Any] | None = None


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
    bits = vectorized_rule_bits(df, rules)
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


def _build_hgb_kwargs(tuned_params: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    """HistGradientBoosting kwargs from Optuna/recipe; max_leaf_nodes OR max_depth."""
    clean = {k: v for k, v in tuned_params.items() if k != "use_max_leaf_nodes"}
    return _canonical_hgb_params(clean, recipe)


def _detect_thr_genuine_fpr(
    scores: np.ndarray,
    y_labels: pd.Series,
    *,
    fpr_target: float,
) -> dict[str, float]:
    from packages.eval.fpr_pareto import max_recall_at_genuine_fpr

    y_str = y_labels.astype(str).to_numpy()
    y_bin = (y_str != "normal").astype(int)
    normal_mask = y_str == "normal"
    return max_recall_at_genuine_fpr(scores, y_bin, normal_mask, fpr_target=fpr_target)


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


def _rule_hit_masks(
    raw: pd.DataFrame,
    rules: list[Rule],
    scores: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Hard/calm flags and applies_to from ``rule__`` bits.

    Nudges do not set applies_to (Brake must not credit-restrict on mule nudges).
    ``min_score`` gates bits when scores are provided.
    """
    n = len(raw)
    hard = np.zeros(n, dtype=bool)
    calm = np.zeros(n, dtype=bool)
    applies: dict[str, np.ndarray] = {}
    live = [r for r in rules if r.status == "live"]
    score_arr = np.asarray(scores, dtype=float) if scores is not None else None
    for rule in live:
        col = f"rule__{rule.id}"
        if col not in raw.columns:
            continue
        bit = raw[col].fillna(0).astype(int).to_numpy(dtype=bool)
        if score_arr is not None and rule.min_score is not None:
            bit = bit & (score_arr >= float(rule.min_score))
        if rule.kind == "hard_flag":
            hard |= bit
            key = rule.applies_to.lower()
            applies[key] = applies.get(key, np.zeros(n, dtype=bool)) | bit
        elif rule.kind == "calm_down":
            calm |= bit
    return hard, calm, applies


def _brake_action_hist_loop(
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
    """Row-loop oracle for identity tests."""
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


def _vectorized_brake_actions(
    raw: pd.DataFrame,
    pred: np.ndarray,
    scores: np.ndarray,
    rules: list[Rule],
    iso_model: Any | None = None,
    pmap: dict[str, np.ndarray] | None = None,
    payees: pd.Series | None = None,
) -> np.ndarray:
    """Vectorized brake priority using attached ``rule__`` bits (not a second rule engine)."""
    n = len(raw)
    hard, calm, applies = _rule_hit_masks(raw, rules, scores=np.asarray(scores, dtype=float))
    family = np.array([str(p).lower() for p in pred], dtype=object)
    score_arr = np.asarray(scores, dtype=float)
    actions = np.array(["allow"] * n, dtype=object)
    done = np.zeros(n, dtype=bool)
    hub_mask = np.zeros(n, dtype=bool)
    fan_burst = np.zeros(n, dtype=bool)
    if payees is not None:
        hub_mask = payees.astype(str).str.startswith(HUB_PAYEE_PREFIX).to_numpy()
    if "rule__mule-fan-in-burst" in raw.columns:
        fan_burst = raw["rule__mule-fan-in-burst"].fillna(0).astype(int).to_numpy(dtype=bool)
    hub_fan_exempt = hub_mask & fan_burst
    if hub_fan_exempt.any():
        hard = hard & ~hub_fan_exempt

    def _assign(mask: np.ndarray, values: np.ndarray | str) -> None:
        m = mask & ~done
        if not m.any():
            return
        if isinstance(values, str):
            actions[m] = values
        else:
            actions[m] = values[m]
        done[m] = True

    mule_rule = applies.get("mule", np.zeros(n, dtype=bool))
    if hub_fan_exempt.any():
        mule_rule = mule_rule & ~hub_fan_exempt
    mule_hit = ((family == "mule") & (score_arr >= ATO_DECLINE_SCORE)) | mule_rule
    app_hit = (family == "app_fraud") | applies.get("app", np.zeros(n, dtype=bool))
    ato_hit = (family == "ato") | applies.get("ato", np.zeros(n, dtype=bool))
    invoice_hit = (family == "invoice_fraud") | applies.get("bec", np.zeros(n, dtype=bool))

    _assign(mule_hit, "mule_credit_restrict")
    _assign(calm & ~hard, "allow")
    app_vals = np.where(hard | (score_arr >= APP_HOLD_SCORE), "hold", "notify")
    _assign(app_hit, app_vals)
    invoice_vals = np.where(hard | (score_arr >= ATO_DECLINE_SCORE), "hold", "case")
    _assign(invoice_hit, invoice_vals)
    ato_vals = np.where(hard | (score_arr >= ATO_DECLINE_SCORE), "decline", "step_up")
    _assign(ato_hit, ato_vals)
    id_vals = np.where(score_arr >= ATO_DECLINE_SCORE, "step_up", "notify")
    _assign((family == "identity_burst") & ~done, id_vals)
    _assign((score_arr >= APP_HOLD_SCORE) & ~done, "notify")

    decline_app = (actions == "decline") & app_hit & ~mule_hit
    actions[decline_app] = "hold"

    if iso_model is not None and pmap is not None:
        p_norm = pmap.get("normal", np.zeros(n))
        gate = (family == "normal") & (p_norm >= 0.95)
        if gate.any():
            gated_idx = np.where(gate)[0]
            gated_df = raw.iloc[gated_idx]
            anomalies = predict_iso_anomalies_batch(iso_model, gated_df)
            allow_mask = actions[gated_idx] == "allow"
            upgrade_idx = gated_idx[allow_mask & anomalies]
            actions[upgrade_idx] = "notify"

    return actions


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
    actions = _vectorized_brake_actions(
        raw, pred, scores, rules, iso_model=iso_model, pmap=pmap, payees=payees
    )
    hist: dict[str, int] = {}
    fp_hist: dict[str, int] = {}
    fp_mask = (lbl == "normal") & (yhat == 1)
    for action in np.unique(actions):
        hist[str(action)] = int((actions == action).sum())
    if fp_mask.any():
        fp_actions = actions[fp_mask]
        for action in np.unique(fp_actions):
            fp_hist[str(action)] = int((fp_actions == action).sum())
    return hist, fp_hist


def _top_features(
    model: HistGradientBoostingClassifier | None = None,
    x_val: np.ndarray | None = None,
    y_val: pd.Series | None = None,
    raw_columns: list[str] | pd.Index | None = None,
    k: int = 5,
) -> tuple[list[str], dict[str, float]]:
    """Permutation importance on inner_val using neg_log_loss (replaces correlation).

    Inner-val may lack classes the HGB was trained on; pass model.classes_ into
    log_loss so this is a real ranking, not the allowlist-order fallback.
    """
    if model is not None and x_val is not None and y_val is not None and raw_columns is not None:
        cols = [str(c) for c in raw_columns]
        if len(y_val.unique()) >= 2 and x_val.shape[0] >= 5:
            y_arr = y_val.astype(str).to_numpy()
            labels = np.asarray(model.classes_).astype(str)
            known = np.isin(y_arr, labels)
            if int(known.sum()) < 5 or len(np.unique(y_arr[known])) < 2:
                raise RuntimeError(
                    f"permutation_importance needs >=5 known-class rows and >=2 classes; "
                    f"got known={int(known.sum())}"
                )
            x_pi = np.asarray(x_val)[known]
            y_pi = y_arr[known]

            def _neg_log_loss(estimator, X, y) -> float:
                proba = estimator.predict_proba(X)
                return float(-log_loss(np.asarray(y).astype(str), proba, labels=labels))

            old_omp = os.environ.get("OMP_NUM_THREADS")
            try:
                os.environ["OMP_NUM_THREADS"] = "1"
                res = permutation_importance(
                    model,
                    x_pi,
                    y_pi,
                    scoring=_neg_log_loss,
                    n_repeats=_perm_repeats(),
                    random_state=42,
                    n_jobs=-1,
                )
                importances = res.importances_mean
                ranked = sorted(zip(importances, cols), reverse=True)
                top = [name for _, name in ranked[:k]]
                imp_map = {name: float(imp) for imp, name in ranked}
                return top, imp_map
            finally:
                if old_omp is None:
                    os.environ.pop("OMP_NUM_THREADS", None)
                else:
                    os.environ["OMP_NUM_THREADS"] = old_omp
    raise RuntimeError(
        "permutation_importance failed or insufficient inner_val data; "
        "refusing silent first-k fallback"
    )


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


def _fit_pmap_calibrators(
    pmap: dict[str, np.ndarray],
    y_ref: pd.Series,
    classes: list[str],
) -> dict[str, IsotonicRegression | None]:
    """Fit per-class isotonic calibrators on a reference slice (inner-val)."""
    n = len(y_ref)
    yv = y_ref.astype(str).to_numpy()
    calibrators: dict[str, IsotonicRegression | None] = {}
    for c in classes:
        if c == "normal":
            calibrators[c] = None
            continue
        raw_c = pmap.get(c, np.zeros(n))
        c_mask = (yv == c).astype(int)
        if c_mask.sum() >= 50 and len(np.unique(c_mask)) >= 2:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(raw_c, c_mask)
            calibrators[c] = iso
        else:
            _LOG.info("stage2_skipped_n_pos_lt_50", extra={"family": c, "n_pos": int(c_mask.sum())})
            calibrators[c] = None
    return calibrators


def _apply_pmap_calibrators(
    pmap: dict[str, np.ndarray],
    calibrators: dict[str, IsotonicRegression | None],
    classes: list[str],
) -> dict[str, np.ndarray]:
    """Apply frozen calibrators to any pmap (e.g. outer eval or G-test)."""
    n = len(next(iter(pmap.values()))) if pmap else 0
    calibrated: dict[str, np.ndarray] = {}
    for c in classes:
        raw_c = pmap.get(c, np.zeros(n))
        iso = calibrators.get(c)
        calibrated[c] = iso.predict(raw_c) if iso is not None else raw_c

    if classes and n > 0:
        stacked = np.column_stack([calibrated.get(c, np.zeros(n)) for c in classes])
        sums = stacked.sum(axis=1, keepdims=True)
        sums[sums == 0] = 1.0
        normalized = stacked / sums
        for i, c in enumerate(classes):
            calibrated[c] = normalized[:, i]

    return calibrated


def _calibrate_pmap(
    pmap: dict[str, np.ndarray],
    y_inner_val: pd.Series,
    classes: list[str],
) -> dict[str, np.ndarray]:
    """Fit and apply calibrators on the same slice (inner-val threshold path)."""
    cals = _fit_pmap_calibrators(pmap, y_inner_val, classes)
    return _apply_pmap_calibrators(pmap, cals, classes)


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

    n_families_with_pos = sum(int((yv == fam).sum()) >= 1 for fam in FRAUD_FAMILIES)
    print(
        f"[fit] bootstrap_ci n_eval={n} n_resamples={n_resamples} "
        f"n_families_with_pos={n_families_with_pos}",
        file=sys.stderr,
        flush=True,
    )

    for fam in FRAUD_FAMILIES:
        mask = yv == fam
        n_pos = int(mask.sum())
        if n_pos < 1:
            print(
                f"[fit] bootstrap_ci family={fam} n_pos=0 skip",
                file=sys.stderr,
                flush=True,
            )
            out[fam] = {"low": float("nan"), "high": float("nan")}
            continue

        clusters = payees if fam in {"mule", "invoice_fraud"} else payers
        _, codes = np.unique(clusters, return_inverse=True)
        c_count = int(codes.max()) + 1

        print(
            f"[fit] bootstrap_ci family={fam} n_pos={n_pos} n_clusters={c_count} start",
            file=sys.stderr,
            flush=True,
        )

        scores = pmap.get(fam, np.zeros(n))
        aps: list[float] = []
        fam_t0 = time.perf_counter()

        for r_i in range(1, n_resamples + 1):
            sampled_codes = rng.choice(c_count, size=c_count, replace=True)
            seen = np.zeros(c_count, dtype=bool)
            seen[sampled_codes] = True
            row_mask = seen[codes]
            sub_y = mask[row_mask].astype(int)
            sub_scores = scores[row_mask]

            if sub_y.min() != sub_y.max() and len(sub_y) >= 2:
                ap = float(average_precision_score(sub_y, sub_scores))
                aps.append(ap)

            if r_i % 25 == 0:
                print(
                    f"[fit] bootstrap_ci family={fam} resample {r_i}/{n_resamples}",
                    file=sys.stderr,
                    flush=True,
                )

        fam_elapsed = time.perf_counter() - fam_t0
        if len(aps) >= 5:
            low = float(np.percentile(aps, 2.5))
            high = float(np.percentile(aps, 97.5))
            if low == high and high < 1.0:
                high = min(1.0, low + 1e-4)
            out[fam] = {"low": low, "high": high}
        else:
            out[fam] = {"low": float("nan"), "high": float("nan")}

        print(
            f"[fit] bootstrap_ci family={fam} done ({fam_elapsed:.1f}s, "
            f"kept={len(aps)}/{n_resamples} aps)",
            file=sys.stderr,
            flush=True,
        )

    return out


def _zero_encoded_columns(
    x: np.ndarray,
    raw: pd.DataFrame,
    cols: list[str],
    *,
    cap_amount_vs_p30: bool = False,
) -> np.ndarray:
    z = x.copy()
    col_index = {c: i for i, c in enumerate(raw.columns)}
    for c in cols:
        i = col_index.get(c)
        if i is not None and i < z.shape[1]:
            z[:, i] = 0.0
    if cap_amount_vs_p30 and "amount_vs_p30" in col_index:
        i = col_index["amount_vs_p30"]
        if i < z.shape[1]:
            z[:, i] = np.minimum(z[:, i], 1.5)
    return z


def _champion_pmap_scores(champ: Champion, x: np.ndarray) -> tuple[dict[str, np.ndarray], np.ndarray]:
    raw_pmap = _proba_map(champ.model, x)
    if getattr(champ, "pmap_calibrators", None):
        pmap = _apply_pmap_calibrators(raw_pmap, champ.pmap_calibrators, champ.classes)
    else:
        pmap = raw_pmap
    scores = _fraud_score(pmap, x.shape[0])
    return pmap, scores


def _app_ablation(
    champ: Champion,
    x_ev: np.ndarray,
    y_ev: pd.Series,
    raw_ev: pd.DataFrame,
    recipe: dict[str, Any],
    *,
    model_freeze_id: str | None = None,
) -> dict[str, Any]:
    """Zero columns on the frozen champion matrix; never refit a toy APP HGB."""
    y_app = (y_ev.astype(str) == "app_fraud").to_numpy(dtype=int)
    y_bin = (y_ev.astype(str) != "normal").to_numpy(dtype=int)
    flags = [c for c in recipe.get("app_flag_cols", list(APP_FLAG_COLS)) if c in raw_ev.columns]

    def _app_ap(x_mod: np.ndarray) -> float:
        if y_app.min() == y_app.max():
            return float("nan")
        pmap, _ = _champion_pmap_scores(champ, x_mod)
        app_scores = pmap.get("app_fraud", np.zeros(len(y_ev)))
        return float(average_precision_score(y_app, app_scores))

    def _binary_ap(x_mod: np.ndarray) -> float:
        if y_bin.min() == y_bin.max():
            return float("nan")
        _, scores = _champion_pmap_scores(champ, x_mod)
        return float(average_precision_score(y_bin, scores))

    with_flags = _app_ap(x_ev)
    without = _app_ap(_zero_encoded_columns(x_ev, raw_ev, flags))
    died = (
        int(y_app.sum()) > 0
        and np.isfinite(with_flags)
        and np.isfinite(without)
        and without <= max(0.05, 0.5 * with_flags)
    )
    stamp_cols = list(flags) + [
        c
        for c in ("beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag")
        if c in raw_ev.columns
    ] + [c for c in raw_ev.columns if str(c).startswith("rule__")]
    stamp_zero = list(stamp_cols)
    if "is_new_payee" in raw_ev.columns:
        stamp_zero.append("is_new_payee")
    without_stamps = _binary_ap(
        _zero_encoded_columns(x_ev, raw_ev, stamp_zero, cap_amount_vs_p30=True)
    )
    out: dict[str, Any] = {
        "app_flags": flags,
        "with_app_flags": {"average_precision": with_flags},
        "without_app_flags": {"average_precision": without},
        "without_stamps": {"average_precision": without_stamps},
        "app_metric_died_without_synthetic_flags": died,
        "app_ablation_source": "frozen_champion",
        "note": "Synthetic session flags are not an SDK. Collapse without flags is documented, not hidden.",
    }
    if model_freeze_id:
        out["model_freeze_id"] = model_freeze_id
    return out


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
        "n_pos_by_fold",
        "not_comparable",
        "tpr_at_fpr",
        "genuine_fp",
        "genuine_fp_over_eval",
        "f1_at_op",
        "binary_ap",
        "precision_at_op",
        "recall_at_op",
        "confusion_matrix",
        "app_ablation",
        "authgate_ms",
        "mule_entity_recall",
        "protocol",
        "inner_val_protocol",
        "recipe_hash",
        "model_freeze_id",
        "cost_sketch",
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
    cost_sketch = metrics.get("cost_sketch") or {}
    for key in ("unit", "expected_cost", "fn_rate", "fp_action_hist"):
        if key not in cost_sketch:
            reasons.append(f"missing:cost_sketch.{key}")
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
    dest_run_id: str | None = None,
) -> dict[str, Any]:
    recipe = load_recipe()
    r_hash = _recipe_hash()
    dest_id = dest_run_id or run_id
    opened = _load_gtest_protocol(dest_id, models_dir)
    if opened.get("gtest_opened_at"):
        raise ValueError(
            f"fit_champion refuses to overwrite model_run_id={dest_id} after G-test photograph; "
            "pass dest_run_id for Stage 2"
        )
    paths = run_paths(run_id, runs_dir)
    if not paths["train"].is_file() or not paths["split"].is_file():
        raise FileNotFoundError(f"missing train/split for run_id={run_id}")

    with _stage("load_parquet"):
        train_df = pd.read_parquet(paths["train"])
        split_df = pd.read_parquet(paths["split"])
    extra = set(train_df.columns) - set(TRAIN_ALLOWLIST)
    if extra:
        raise AssertionError(f"train cols outside allowlist: {extra}")
    rules = load_v0_rules()
    with _stage("attach_rule_bits"):
        train_df = _attach_rule_bits(train_df, rules)
    with _stage("assign_folds"):
        sidecar = (
            json.loads(paths["sidecar"].read_text(encoding="utf-8"))
            if paths["sidecar"].is_file()
            else {}
        )
        sim_days = sidecar.get("sim_days")
        packed = folds_from_run(
            train_df,
            split_df,
            seed=world_seed,
            force_train_event_ids=force_train_event_ids,
            sim_days=int(sim_days) if sim_days is not None else None,
        )
    x_tr_raw, y_tr = packed["X_train"], packed["y_train"]
    x_ev_raw, y_ev = packed["X_eval"], packed["y_eval"]
    inner = inner_folds_from_train(
        split_df.reset_index(drop=True),
        packed["folds"].reset_index(drop=True),
        exclude_event_ids=force_train_event_ids,
    )
    floor_min = int(recipe.get("fold_floor_min", 0))
    if floor_min > 0:
        preflight_fold_floors(
            train_df.reset_index(drop=True)["label_family"],
            packed["folds"].reset_index(drop=True),
            inner.reset_index(drop=True),
            min_n=floor_min,
        )
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
    with _stage("encode_features"):
        x_tr, encoder = _encode(x_tr_raw, encoder=None, cat_cols=cat_cols, fit=True)
        x_ev, encoder = _encode(x_ev_raw, encoder=encoder, cat_cols=cat_cols, fit=False)

    dest = (models_dir or MODELS_DIR) / dest_id
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
    hgb_kwargs = _build_hgb_kwargs(tuned_params, recipe)
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
    with _stage("inner_hgb"):
        inner_model = HistGradientBoostingClassifier(**hgb_kwargs)
        inner_model.fit(x_ifit, y_ifit.astype(str).to_numpy(), sample_weight=inner_sw)
    _LOG.info("threshold_fit", extra={"fold": "inner_fit", "n_rows": len(y_ifit)})
    # --- Step 2: compute op_threshold from inner_val scores ---
    with _stage("inner_val_threshold"):
        x_ival, _ = _encode(x_ival_raw, encoder=enc_inner, cat_cols=cat_cols, fit=False)
        inner_pmap = _proba_map(inner_model, x_ival)
        inner_y_bin = (y_ival.astype(str) != "normal").to_numpy(dtype=int)
        # Stage 1 isotonic: fit threshold on CALIBRATED inner-val scores (ssot Ticket 9).
        ival_classes = [str(c) for c in inner_model.classes_]
        inner_cal_pmap = _calibrate_pmap(inner_pmap, y_ival, ival_classes)
        inner_scores = _fraud_score(inner_cal_pmap, len(y_ival))
        op_fpr = float(recipe.get("operating_point_fpr", 0.01))
        inner_op = _detect_thr_genuine_fpr(inner_scores, y_ival, fpr_target=op_fpr)
        thr = float(inner_op.get("threshold") or 1.0)
    _LOG.info("threshold_fit", extra={"fold": "inner_val", "n_rows": len(y_ival), "op_threshold": thr})

    # --- Isolation Forest anomaly detector (Ticket 8, kill switch aware) ---
    iso_cfg = recipe.get("isolation_forest") or {}
    try:
        iso_contamination = float(iso_cfg.get("contamination", 0.01))
    except (TypeError, ValueError):
        iso_contamination = 0.01
    with _stage("isolation_forest"):
        iso_model = fit_isolation_forest(x_ifit_raw, y_ifit, contamination=iso_contamination)
        iso_notify_rate = check_iso_genuine_notify_rate(iso_model, x_ival_raw, y_ival)
    iso_enabled = iso_enabled_flag(iso_cfg, iso_notify_rate)
    _LOG.info(
        "isolation_forest_fit",
        extra={"notify_rate": iso_notify_rate, "enabled": iso_enabled, "enabled_default": iso_cfg.get("enabled_default")},
    )

    # --- Step 3: refit on full outer train with frozen threshold ---
    sample_weight = y_tr.astype(str).map(weights).to_numpy(dtype=float)
    with _stage("outer_hgb"):
        model = HistGradientBoostingClassifier(**hgb_kwargs)
        model.fit(x_tr, y_tr.astype(str).to_numpy(), sample_weight=sample_weight)
    classes = [str(c) for c in model.classes_]
    # --- Step 4: outer eval ---
    with _stage("outer_eval_calibration"):
        raw_pmap = _proba_map(model, x_ev)
        raw_scores = _fraud_score(raw_pmap, len(y_ev))
        y_bin = (y_ev.astype(str) != "normal").to_numpy(dtype=int)

        ece_before = _compute_ece(y_bin, raw_scores)
        x_ival_enc, _ = _encode(x_ival_raw, encoder=encoder, cat_cols=cat_cols, fit=False)
        ival_pmap_full = _proba_map(model, x_ival_enc)
        pmap_cals = _fit_pmap_calibrators(ival_pmap_full, y_ival, classes)
        calibrated_pmap = _apply_pmap_calibrators(raw_pmap, pmap_cals, classes)
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
    genuine_fp = _genuine_fp_rate(yhat, genuine.to_numpy())
    genuine_fp_over_eval = _genuine_fp_over_eval(yhat, len(y_ev))
    detect_thr = float(thr)
    act_thr = _act_threshold(recipe)
    f1 = float(f1_score(y_bin, yhat, zero_division=0))
    split_eval = split_df.reset_index(drop=True).loc[packed["folds"].reset_index(drop=True) == "eval"]
    hang_s = float(recipe.get("hang_guard_seconds_1k", 120))
    bench = _bench_ms(model, x_ev, hang_s)
    freeze_params_early = _canonical_hgb_params(hgb_kwargs, recipe)
    freeze_id_early = _model_freeze_id(
        recipe_hash=r_hash,
        best_params=freeze_params_early,
        op_threshold=thr,
        recipe=recipe,
    )
    champ_for_ablation = Champion(
        model=model,
        encoder=encoder,
        raw_columns=list(x_tr_raw.columns),
        cat_cols=cat_cols,
        classes=classes,
        op_threshold=thr,
        detect_thr=detect_thr,
        act_thr=act_thr,
        fold_seed=world_seed,
        rule_ids=[r.id for r in rules if r.status == "live"],
        top_features=[],
        recipe=recipe,
        iso_model=iso_model if iso_enabled else None,
        isolation_forest_enabled=iso_enabled,
        pmap_calibrators=pmap_cals,
    )
    with _stage("app_ablation"):
        ablation = _app_ablation(
            champ_for_ablation,
            x_ev,
            y_ev,
            x_ev_raw,
            recipe,
            model_freeze_id=freeze_id_early,
        )
    mule_rec = _mule_entity_recall(split_eval, pred, scores, thr)

    with _stage("permutation_importance"):
        try:
            top, importances_mean = _top_features(inner_model, x_ival, y_ival, x_tr_raw.columns)
        except RuntimeError:
            if recipe.get("pi_fail_loud", True) and len(y_ival) >= 50:
                raise
            top = [str(c) for c in list(x_tr_raw.columns)[:5]]
            importances_mean = {}
    with _stage("bootstrap_ci"):
        bootstrap_ci = _cluster_bootstrap_ci(split_eval, y_ev, pmap, n_resamples=_bootstrap_resamples())

    n_pos = _n_pos_by_family(y_ev)
    not_comparable = _not_comparable(n_pos, int(recipe.get("n_pos_not_comparable_below", 30)))
    n_pos_by_fold = {
        "train": _n_pos_by_family(y_tr),
        "eval": n_pos,
        "inner_fit": _n_pos_by_family(y_ifit),
        "inner_val": _n_pos_by_family(y_ival),
    }
    with _stage("brake_hist"):
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

    with _stage("persist"):
        champ = Champion(
            model=model,
            encoder=encoder,
            raw_columns=list(x_tr_raw.columns),
            cat_cols=cat_cols,
            classes=classes,
            op_threshold=thr,
            detect_thr=detect_thr,
            act_thr=act_thr,
            fold_seed=world_seed,
            rule_ids=[r.id for r in rules if r.status == "live"],
            top_features=top,
            recipe=recipe,
            iso_model=iso_model if iso_enabled else None,
            isolation_forest_enabled=iso_enabled,
            pmap_calibrators=pmap_cals,
        )
        bin_op = _binary_op_metrics(y_bin, scores, yhat)
        freeze_params = _canonical_hgb_params(hgb_kwargs, recipe)
        freeze_id = _model_freeze_id(
            recipe_hash=r_hash,
            best_params=freeze_params,
            op_threshold=thr,
            recipe=recipe,
        )
        joblib.dump(champ, dest / "champion.joblib")
        _atomic_write_json(
            dest / "model_manifest.json",
            {
                "recipe_hash": r_hash,
                "run_id": run_id,
                "model_run_id": dest_id,
                "model_freeze_id": freeze_id,
                "best_params": freeze_params,
                "op_threshold": thr,
                "detect_thr": detect_thr,
                "act_thr": act_thr,
            },
        )
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
            "n_pos_by_fold": n_pos_by_fold,
            "not_comparable": not_comparable,
            "cost_sketch": cost_sketch,
            "tpr_at_fpr": tpr_block,
            "genuine_fp": genuine_fp,
            "genuine_fp_over_eval": genuine_fp_over_eval,
            "f1_at_op": f1,
            "binary_ap": bin_op["binary_ap"],
            "precision_at_op": bin_op["precision_at_op"],
            "recall_at_op": bin_op["recall_at_op"],
            "confusion_matrix": bin_op["confusion_matrix"],
            "operating_point_fpr": op_fpr,
            "op_threshold": thr,
            "detect_thr": detect_thr,
            "act_thr": act_thr,
            "app_ablation": ablation,
            "authgate_ms": bench,
            "mule_entity_recall": mule_rec,
            "feature_columns": list(x_tr_raw.columns),
            "top_features": top,
            "importances_mean": importances_mean,
            "split": packed["protocol"],
            "inner_val_protocol": "last_20pct_train_calendar",
            "diagnostic_ap_by_family": _ap_by_family(y_ev, pmap),
            "recipe_hash": r_hash,
            "model_freeze_id": freeze_id,
            "best_params": freeze_params,
            "ece_before": ece_before,
            "ece_after": ece_after,
            "bootstrap_ci": bootstrap_ci,
            "isolation_forest_enabled": iso_enabled,
            "iso_genuine_notify_rate": iso_notify_rate,
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
        "model_run_id": dest_id,
        "model_dir": str(dest),
        "metrics": _jsonable(metrics),
        "split": packed["protocol"],
        "recipe_hash": r_hash,
        "model_freeze_id": freeze_id,
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
    dest_run_id: str | None = None,
) -> dict[str, Any]:
    """Nested inner_val A/B Optuna — never reads outer eval in the objective."""
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
    sidecar = (
        json.loads(paths["sidecar"].read_text(encoding="utf-8"))
        if paths["sidecar"].is_file()
        else {}
    )
    sim_days = sidecar.get("sim_days")
    packed = folds_from_run(
        train_df,
        split_df,
        seed=world_seed,
        sim_days=int(sim_days) if sim_days is not None else None,
    )
    x_tr_raw, y_tr = packed["X_train"], packed["y_train"]
    for fam in pd.concat([y_tr, packed["y_eval"]]).unique():
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
    opt_cfg = recipe.get("optuna") or {}
    fpr_ceiling = float(opt_cfg.get("inner_b_fpr_ceiling", 0.02))

    n_fraud_val = int(inner_y_bin.sum())
    skipped_small_n = bool(force_skip or n_fraud_val < min_inner_val_fraud_pos)
    trial_log: list[dict[str, Any]] = []
    if skipped_small_n:
        _LOG.info(
            "optuna_skipped_small_n",
            extra={"run_id": run_id, "inner_val_fraud_pos": n_fraud_val, "min": min_inner_val_fraud_pos},
        )
        best_params = {
            "max_depth": int(recipe.get("max_depth", 3)),
            "max_iter": int(recipe.get("max_iter", 80)),
            "learning_rate": float(recipe.get("learning_rate", 0.08)),
        }
        if recipe.get("min_samples_leaf") is not None:
            best_params["min_samples_leaf"] = int(recipe["min_samples_leaf"])
        direction = None
    else:
        weights = _class_weight(y_tr)
        inner_sw = y_ifit.astype(str).map(weights).to_numpy(dtype=float)
        full_split = split_df.reset_index(drop=True)
        train_row_idx = np.where(train_idx)[0]
        inner_val_global = np.zeros(len(full_split), dtype=bool)
        inner_val_global[train_row_idx[ival_mask]] = True
        ab_a, ab_b = split_inner_val_ab(full_split, inner_val_global)
        a_rows = ab_a[train_row_idx[ival_mask]]
        b_rows = ab_b[train_row_idx[ival_mask]]
        if not a_rows.any() or not b_rows.any():
            raise ValueError("inner_val A/B split produced an empty slice")

        def _objective(trial: Any) -> float:
            use_leaf = trial.suggest_categorical("use_max_leaf_nodes", [False, True])
            p: dict[str, Any] = {
                "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.2, log=True),
                "max_iter": trial.suggest_int("max_iter", 40, 200),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 5, 50),
                "l2_regularization": trial.suggest_float("l2_regularization", 1e-6, 10.0, log=True),
                "max_bins": trial.suggest_categorical("max_bins", [64, 128, 255]),
            }
            if use_leaf:
                p["max_leaf_nodes"] = trial.suggest_int("max_leaf_nodes", 15, 63)
            else:
                p["max_depth"] = trial.suggest_categorical("max_depth", [2, 3, 4, 5])
            m = HistGradientBoostingClassifier(**_build_hgb_kwargs(p, recipe))
            m.fit(x_ifit, y_ifit_s, sample_weight=inner_sw)
            classes_t = [str(c) for c in m.classes_]
            pmap_a = _proba_map(m, x_ival[a_rows])
            pmap_b = _proba_map(m, x_ival[b_rows])
            y_a = y_ival.iloc[np.where(a_rows)[0]]
            y_b = y_ival.iloc[np.where(b_rows)[0]]
            cals = _fit_pmap_calibrators(pmap_a, y_a, classes_t)
            cal_a = _apply_pmap_calibrators(pmap_a, cals, classes_t)
            cal_b = _apply_pmap_calibrators(pmap_b, cals, classes_t)
            scores_a = _fraud_score(cal_a, int(a_rows.sum()))
            scores_b = _fraud_score(cal_b, int(b_rows.sum()))
            op_pt = _detect_thr_genuine_fpr(scores_a, y_a, fpr_target=op_fpr)
            tau = float(op_pt.get("threshold") or 1.0)
            recall_a = float(op_pt.get("recall") or 0.0)
            genuine_b = (y_b.astype(str) == "normal").to_numpy()
            inner_b_fp = (
                float(np.mean(scores_b[genuine_b] >= tau)) if genuine_b.any() else 0.0
            )
            pareto_caps = tuple(float(x) for x in opt_cfg.get("fpr_pareto_targets", [0.01, 0.005, 0.001]))
            pareto_a = {
                f"{t:g}": _detect_thr_genuine_fpr(scores_a, y_a, fpr_target=t) for t in pareto_caps
            }
            trial.set_user_attr("inner_A_tpr", recall_a)
            trial.set_user_attr("inner_B_genuine_fp", inner_b_fp)
            trial.set_user_attr("tau", tau)
            trial.set_user_attr("pareto_inner_A", pareto_a)
            trial_log.append(
                {
                    "number": int(trial.number),
                    "params": p,
                    "inner_A_tpr": recall_a,
                    "inner_B_genuine_fp": inner_b_fp,
                    "tau": tau,
                    "pareto_inner_A": pareto_a,
                }
            )
            if inner_b_fp > fpr_ceiling:
                return -100.0 * (inner_b_fp - fpr_ceiling) - 1.0
            return recall_a

        import optuna

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=random_state),
            study_name=f"tune-{run_id}",
        )
        study.optimize(_objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)
        best_params = dict(study.best_params)
        direction = "maximize"
        dest_pre = (models_dir or MODELS_DIR) / (dest_run_id or run_id)
        dest_pre.mkdir(parents=True, exist_ok=True)
        trials_payload = {
            "objective": "max_recall_genuine_fpr_inner_val_A_subject_to_inner_B_genuine_fp",
            "operating_point_fpr": op_fpr,
            "fpr_pareto_targets": list(opt_cfg.get("fpr_pareto_targets", [0.01, 0.005, 0.001])),
            "inner_b_fpr_ceiling": fpr_ceiling,
            "best_value": study.best_value,
            "best_params": best_params,
            "trials": trial_log,
        }
        _atomic_write_json(dest_pre / "trials.json", trials_payload)
        _atomic_write_json(dest_pre / "optuna_trials.json", trials_payload)

    dest_id = dest_run_id or run_id
    opened = _load_gtest_protocol(dest_id, models_dir)
    if opened.get("gtest_opened_at"):
        raise ValueError(
            f"tune_champion refuses to overwrite model_run_id={dest_id} after G-test photograph; "
            "pass dest_run_id for Stage 2"
        )

    dest = (models_dir or MODELS_DIR) / dest_id
    dest.mkdir(parents=True, exist_ok=True)
    best_payload = {
        "run_id": run_id,
        "model_run_id": dest_id,
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
        dest_run_id=dest_id,
    )
    return {
        "run_id": run_id,
        "model_run_id": dest_id,
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
        frozen_hash = manifest.get("recipe_hash", "")
        if frozen_hash and not _recipe_hash_accepted(frozen_hash):
            raise RecipeHashMismatchError(
                f"features.json changed after model was frozen "
                f"(frozen={frozen_hash[:16]}… current={_recipe_hash()[:16]}…). "
                f"Refusing to score — retrain or revert features.json."
            )
    return joblib.load(path)


def _gtest_cached_score_if_opened(
    run_id: str,
    model_run_id: str,
    *,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    all_rows: bool = False,
) -> dict[str, Any] | None:
    """Return persisted gtest_score.json without loading holdout parquet when already photographed."""
    if not all_rows:
        return None
    paths = run_paths(run_id, runs_dir)
    if not paths["sidecar"].is_file():
        return None
    sidecar = json.loads(paths["sidecar"].read_text(encoding="utf-8"))
    if int(sidecar.get("world_seed", 0)) != 43:
        return None
    champ = load_champion(model_run_id, models_dir=models_dir)
    manifest_path = (models_dir or MODELS_DIR) / model_run_id / "model_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    recipe_hash = str(manifest.get("recipe_hash") or _recipe_hash())
    champ_metrics_path = (models_dir or MODELS_DIR) / model_run_id / "metrics.json"
    champ_metrics: dict[str, Any] = {}
    if champ_metrics_path.is_file():
        champ_metrics = json.loads(champ_metrics_path.read_text(encoding="utf-8"))
    freeze_params = _best_params_from_champion(champ, champ_metrics if champ_metrics_path.is_file() else {})
    freeze_id = _model_freeze_id(
        recipe_hash=recipe_hash,
        best_params=freeze_params,
        op_threshold=float(champ.op_threshold),
        recipe=champ.recipe,
    )
    proto = _load_gtest_protocol(model_run_id, models_dir)
    stored_freeze = proto.get("model_freeze_id")
    if proto.get("gtest_opened_at") and stored_freeze and stored_freeze != freeze_id:
        raise GtestFreezeMismatchError(
            f"G-test already opened for a different freeze on model_run_id={model_run_id} "
            f"(stored={str(stored_freeze)[:16]}… current={freeze_id[:16]}…). "
            "Fit the new params to a new model_run_id (tune dest_run_id) or use seed 45."
        )
    score_path = _gtest_score_path(model_run_id, models_dir)
    if proto.get("gtest_opened_at") and stored_freeze == freeze_id and score_path.is_file():
        cached_run_id = proto.get("gtest_run_id")
        if cached_run_id and str(cached_run_id) != str(run_id):
            return None
        return json.loads(score_path.read_text(encoding="utf-8"))
    return None


def score_run(
    run_id: str,
    *,
    model_run_id: str | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    all_rows: bool = False,
) -> dict[str, Any]:
    mid = model_run_id or run_id
    cached = _gtest_cached_score_if_opened(
        run_id, mid, runs_dir=runs_dir, models_dir=models_dir, all_rows=all_rows
    )
    if cached is not None:
        return cached
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
    raw_pmap = _proba_map(champ.model, x_ev)
    if getattr(champ, "pmap_calibrators", None):
        pmap = _apply_pmap_calibrators(raw_pmap, champ.pmap_calibrators, champ.classes)
    else:
        pmap = raw_pmap
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
    genuine_fp = _genuine_fp_rate(yhat, genuine.to_numpy())
    genuine_fp_over_eval = _genuine_fp_over_eval(yhat, len(y_ev))
    hang_s = float(recipe.get("hang_guard_seconds_1k", 120))
    bench = _bench_ms(champ.model, x_ev, hang_s)
    manifest_path = (models_dir or MODELS_DIR) / mid / "model_manifest.json"
    manifest = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    recipe_hash = str(manifest.get("recipe_hash") or _recipe_hash())
    champ_metrics_path = (models_dir or MODELS_DIR) / mid / "metrics.json"
    champ_metrics: dict[str, Any] = {}
    if champ_metrics_path.is_file():
        champ_metrics = json.loads(champ_metrics_path.read_text(encoding="utf-8"))
    freeze_params = _best_params_from_champion(champ, champ_metrics if champ_metrics_path.is_file() else {})
    freeze_id = _model_freeze_id(
        recipe_hash=recipe_hash,
        best_params=freeze_params,
        op_threshold=float(thr),
        recipe=recipe,
    )
    ablation = _app_ablation(
        champ,
        x_ev,
        y_ev,
        x_ev_raw,
        recipe,
        model_freeze_id=freeze_id,
    )

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

    bin_op = _binary_op_metrics(y_bin, scores, yhat)

    metrics = {
        "pass": False,
        "schema_version": METRICS_SCHEMA_VERSION,
        "protocol": protocol,
        "n_eval": len(y_ev),
        "ap_by_family": _ap_by_family(y_ev, pmap),
        "n_pos": n_pos,
        "n_pos_by_fold": champ_metrics.get("n_pos_by_fold") or {"eval": n_pos},
        "not_comparable": not_comparable,
        "cost_sketch": cost_sketch,
        "tpr_at_fpr": tpr_block,
        "genuine_fp": genuine_fp,
        "genuine_fp_over_eval": genuine_fp_over_eval,
        "f1_at_op": float(f1_score(y_bin, yhat, zero_division=0)),
        "binary_ap": bin_op["binary_ap"],
        "precision_at_op": bin_op["precision_at_op"],
        "recall_at_op": bin_op["recall_at_op"],
        "confusion_matrix": bin_op["confusion_matrix"],
        "app_ablation": ablation,
        "authgate_ms": bench,
        "mule_entity_recall": _mule_entity_recall(split_eval, pred, scores, thr),
        "feature_columns": list(champ.raw_columns),
        "top_features": champ.top_features,
        "split": protocol,
        "inner_val_protocol": champ_metrics.get("inner_val_protocol", "last_20pct_train_calendar"),
        "recipe_hash": recipe_hash,
        "model_freeze_id": freeze_id,
        "op_threshold": float(thr),
        "detect_thr": float(getattr(champ, "detect_thr", None) or thr),
        "act_thr": float(getattr(champ, "act_thr", None) or _act_threshold(recipe)),
        "best_params": freeze_params,
    }
    if champ_metrics.get("isolation_forest_enabled"):
        metrics["isolation_forest_enabled"] = champ_metrics["isolation_forest_enabled"]
        if "iso_genuine_notify_rate" in champ_metrics:
            metrics["iso_genuine_notify_rate"] = champ_metrics["iso_genuine_notify_rate"]

    gtest_opened_at: str | None = None
    sidecar: dict[str, Any] = {}
    if paths["sidecar"].is_file():
        sidecar = json.loads(paths["sidecar"].read_text(encoding="utf-8"))
    world_seed_scored = int(sidecar.get("world_seed", 0))
    if all_rows and world_seed_scored == 43:
        gtest_opened_at = _record_gtest_opened(
            mid,
            recipe_hash=recipe_hash,
            model_freeze_id=freeze_id,
            world_seed=world_seed_scored,
            gtest_run_id=run_id,
            models_dir=models_dir,
        )
        metrics["gtest_opened_at"] = gtest_opened_at

    metrics["pass"] = _metrics_pass(metrics, hang_s)
    metrics_json = _jsonable(metrics)
    body = {
        "run_id": run_id,
        "model_run_id": mid,
        "metrics": metrics_json,
        "action_histogram": hist,
        "split": protocol,
        "recipe_hash": recipe_hash,
        "model_freeze_id": freeze_id,
    }
    if gtest_opened_at:
        body["gtest_opened_at"] = gtest_opened_at
    if all_rows:
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
            "recipe_hash",
            "model_freeze_id",
            "binary_ap",
            "precision_at_op",
            "recall_at_op",
            "confusion_matrix",
        )
        body["gtest"] = {
            "world_seed": sidecar.get("world_seed"),
            "run_id": run_id,
            **{key: metrics_json[key] for key in headline_keys if key in metrics_json},
        }
        if gtest_opened_at:
            body["gtest"]["gtest_opened_at"] = gtest_opened_at
            _atomic_write_json(_gtest_score_path(mid, models_dir), body)
            run_score = paths["train"].parent / "score.json"
            run_score.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_json(run_score, body)
    assert_no_denylist_payload(body)
    return body
