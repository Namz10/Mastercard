"""Champion GBDT fit + metrics (Plan 12 Phase C). One HGB recipe, no AutoGluon."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, f1_score, roc_curve
from sklearn.preprocessing import OrdinalEncoder

from packages.eval.brake import as_record, brake
from packages.eval.split import assert_no_x_leak, folds_from_run
from packages.policy.rules import Rule, evaluate_rules, load_v0_rules
from packages.sim.ablation import APP_FLAG_COLS
from packages.sim.export import RUNS_DIR, TRAIN_DENYLIST, TRAIN_ALLOWLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS

_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = _ROOT / "models"
RECIPE_PATH = MODELS_DIR / "features.json"
CAT_COLS = ("rail", "kyc_tier")
FRAUD_FAMILIES = tuple(sorted(LABEL_FAMILIES - {"normal"}))
JSON_BAN = frozenset(TRAIN_DENYLIST) | {
    "knobs_used",
    "knobs_pinned",
    "knobs",
    "simulatable_signals",
}


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


def load_recipe(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or RECIPE_PATH).read_text(encoding="utf-8"))


def run_paths(run_id: str, runs_dir: Path | None = None) -> dict[str, Path]:
    folder = (runs_dir or RUNS_DIR) / run_id
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


def _top_features(raw: pd.DataFrame, y_bin: np.ndarray, k: int = 5) -> list[str]:
    ranked: list[tuple[float, str]] = []
    y = pd.Series(y_bin, index=raw.index)
    for c in raw.columns:
        if str(c).startswith("rule__"):
            s = pd.to_numeric(raw[c], errors="coerce")
        elif c in CAT_COLS:
            continue
        else:
            s = pd.to_numeric(raw[c], errors="coerce")
        if s.nunique(dropna=True) < 2:
            continue
        corr = abs(float(s.fillna(0).corr(y)))
        if np.isfinite(corr):
            ranked.append((corr, str(c)))
    ranked.sort(reverse=True)
    return [name for _, name in ranked[:k]]


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
        "n": int(len(xt)),
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
        return None
    return value


def assert_no_denylist_payload(payload: dict[str, Any]) -> None:
    blob = json.dumps(payload, default=str)
    for banned in ("simulatable_signals", "is_authorized_push", "economic_class"):
        if banned in blob:
            raise AssertionError(f"denylist key leaked into Defend JSON: {banned}")


def _metrics_pass(metrics: dict[str, Any], hang_s: float) -> bool:
    required = (
        "ap_by_family",
        "tpr_at_fpr",
        "genuine_fp",
        "f1_at_op",
        "app_ablation",
        "authgate_ms",
        "mule_entity_recall",
    )
    if any(k not in metrics for k in required):
        return False
    bench = metrics.get("authgate_ms") or {}
    if float(bench.get("batch_seconds_1k") or 0) > hang_s:
        return False
    return True


def fit_champion(
    run_id: str,
    *,
    world_seed: int = 42,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    force_train_event_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    recipe = load_recipe()
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
    for fam in pd.concat([y_tr, y_ev]).unique():
        if fam in TECHNIQUE_IDS:
            raise AssertionError(f"y leaked technique id {fam}")
        if fam not in LABEL_FAMILIES:
            raise AssertionError(f"unknown label_family {fam}")
    assert_no_x_leak(x_tr_raw.columns)
    cat_cols = [c for c in CAT_COLS if c in x_tr_raw.columns]
    x_tr, encoder = _encode(x_tr_raw, encoder=None, cat_cols=cat_cols, fit=True)
    x_ev, encoder = _encode(x_ev_raw, encoder=encoder, cat_cols=cat_cols, fit=False)

    weights = _class_weight(y_tr)
    sample_weight = y_tr.astype(str).map(weights).to_numpy(dtype=float)
    model = HistGradientBoostingClassifier(
        max_depth=int(recipe.get("max_depth", 3)),
        max_iter=int(recipe.get("max_iter", 80)),
        learning_rate=float(recipe.get("learning_rate", 0.08)),
        random_state=int(recipe.get("random_state", 42)),
    )
    model.fit(x_tr, y_tr.astype(str).to_numpy(), sample_weight=sample_weight)
    classes = [str(c) for c in model.classes_]
    pmap = _proba_map(model, x_ev)
    scores = _fraud_score(pmap, len(y_ev))
    pred = _pred_family(pmap, classes, len(y_ev))
    y_bin = (y_ev.astype(str) != "normal").to_numpy(dtype=int)
    op_fpr = float(recipe.get("operating_point_fpr", 0.01))
    tpr_block = {
        f"{t:g}": _tpr_at_fpr(y_bin, scores, t) for t in recipe.get("tpr_at_fpr", [0.001, 0.005, 0.01])
    }
    op = tpr_block.get(f"{op_fpr:g}") or _tpr_at_fpr(y_bin, scores, op_fpr)
    thr = float(op.get("threshold") or 1.0)
    yhat = (scores >= thr).astype(int)
    genuine = y_ev.astype(str) == "normal"
    genuine_fp = float(((yhat == 1) & genuine.to_numpy()).mean()) if genuine.any() else float("nan")
    f1 = float(f1_score(y_bin, yhat, zero_division=0))
    split_eval = split_df.reset_index(drop=True).loc[packed["folds"].reset_index(drop=True) == "eval"]
    hang_s = float(recipe.get("hang_guard_seconds_1k", 120))
    bench = _bench_ms(model, x_ev, hang_s)
    ablation = _app_ablation(x_tr, y_tr, x_ev, y_ev, x_tr_raw, x_ev_raw, recipe)
    mule_rec = _mule_entity_recall(split_eval, pred, scores, thr)
    top = _top_features(x_tr_raw, (y_tr.astype(str) != "normal").to_numpy(dtype=int))

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
    )
    dest = (models_dir or MODELS_DIR) / run_id
    dest.mkdir(parents=True, exist_ok=True)
    joblib.dump(champ, dest / "champion.joblib")
    metrics = {
        "pass": False,
        "protocol": packed["protocol"],
        "estimator": recipe["estimator"],
        "n_train": int(len(y_tr)),
        "n_eval": int(len(y_ev)),
        "class_weight": weights,
        "ap_by_family": _ap_by_family(y_ev, pmap),
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
    }
    metrics["pass"] = _metrics_pass(metrics, hang_s)
    (dest / "metrics.json").write_text(json.dumps(_jsonable(metrics), indent=2), encoding="utf-8")
    (dest / "features.json").write_text(
        json.dumps(
            {
                **recipe,
                "run_id": run_id,
                "feature_columns": list(x_tr_raw.columns),
                "classes": classes,
                "op_threshold": thr,
                "fold_seed": world_seed,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    body = {
        "run_id": run_id,
        "model_run_id": run_id,
        "model_dir": str(dest),
        "metrics": _jsonable(metrics),
        "split": packed["protocol"],
    }
    assert_no_denylist_payload(body)
    return body


def load_champion(model_run_id: str, models_dir: Path | None = None) -> Champion:
    path = (models_dir or MODELS_DIR) / model_run_id / "champion.joblib"
    if not path.is_file():
        raise FileNotFoundError(f"no champion for model_run_id={model_run_id}")
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
        ablation = {
            "app_flags": list(recipe.get("app_flag_cols") or []),
            "note": "G-test full population; APP ablation is the champion-train report, not re-fit here.",
        }
    else:
        x_tr, _ = _encode(x_tr_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
        ablation = _app_ablation(x_tr, y_tr, x_ev, y_ev, x_tr_raw, x_ev_raw, recipe)

    hist: dict[str, int] = {}
    records = x_ev_raw.reset_index(drop=True).to_dict(orient="records")
    payees = split_eval.reset_index(drop=True)["payee"].astype(str).tolist()
    for i, rec in enumerate(records):
        hits = evaluate_rules(rec, rules)
        decision = brake(
            pred_label_family=str(pred[i]),
            score=float(scores[i]),
            hits=hits,
            payee=payees[i] if i < len(payees) else None,
        )
        rec_d = as_record(decision)
        hist[rec_d["policy_action"]] = hist.get(rec_d["policy_action"], 0) + 1

    metrics = {
        "pass": False,
        "protocol": protocol,
        "n_eval": int(len(y_ev)),
        "ap_by_family": _ap_by_family(y_ev, pmap),
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
    body = {
        "run_id": run_id,
        "model_run_id": mid,
        "metrics": _jsonable(metrics),
        "action_histogram": hist,
        "split": protocol,
    }
    assert_no_denylist_payload(body)
    return body
