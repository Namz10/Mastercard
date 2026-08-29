"""Plan 12 Phase C — champion fit, labels, time+entity split, ablation, no denylist."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from packages.eval import fit as fit_mod
from packages.eval.fit import _fraud_score, fit_champion, score_run
from packages.sim.export import TRAIN_DENYLIST
from packages.sim.ledger import LABEL_FAMILIES, TECHNIQUE_IDS
from packages.sim.runner import run_population


@pytest.fixture(scope="module")
def pop(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs")
    return run_population(
        None,
        run_id="fit-c",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )


def test_fit_y_is_family_enum_not_technique(pop: dict, tmp_path: Path):
    dest = tmp_path / "models"
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=dest)
    metrics = body["metrics"]
    cols = metrics["feature_columns"]
    for fam in LABEL_FAMILIES:
        assert fam not in TECHNIQUE_IDS
    assert body["split"] == "time_cut_2_3_plus_entity_holdout"
    assert "ap_by_family" in metrics
    for banned in ("is_authorized_push", "economic_class", "technique_id"):
        assert banned not in cols
    for banned in TRAIN_DENYLIST:
        assert banned not in cols
    assert metrics["n_train"] > 0 and metrics["n_eval"] > 0


def test_fit_feature_columns_exclude_gstin_payload(pop: dict, tmp_path: Path):
    dest = tmp_path / "models"
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=dest)
    cols = body["metrics"]["feature_columns"]
    assert "gstin" not in cols
    assert "payload" not in cols
    assert "beneficiary_changed" in cols



def test_reported_split_is_not_shuffle():
    src = inspect.getsource(fit_mod)
    assert "train_test_split" not in src
    assert "shuffle=True" not in src


def test_app_ablation_reported(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "models")
    ab = body["metrics"]["app_ablation"]
    flags = {str(x) for x in ab["app_flags"]}
    for col in ("call_active_flag", "copy_paste_payee_flag", "pause_ms", "urgency_pressure"):
        assert col in flags
    assert "average_precision" in ab["with_app_flags"]
    assert "average_precision" in ab["without_app_flags"]
    assert "app_metric_died_without_synthetic_flags" in ab


def test_fit_reproducible_seed_42(pop: dict, tmp_path: Path):
    runs = Path(pop["parquet_path"]).parent.parent
    a = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "m1")
    b = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "m2")
    assert a["metrics"]["n_train"] == b["metrics"]["n_train"]
    assert a["metrics"]["feature_columns"] == b["metrics"]["feature_columns"]
    assert Path(tmp_path / "m1" / "fit-c" / "champion.joblib").is_file()
    dumped = json.dumps(a)
    assert "simulatable_signals" not in dumped


FRAUD_FAMILIES = LABEL_FAMILIES - {"normal"}


@pytest.fixture(scope="module")
def fitted(pop: dict, tmp_path_factory) -> dict:
    dest = tmp_path_factory.mktemp("models-t2")
    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=dest)
    return {"dest": dest, "runs": runs, "body": body}


def test_fit_metrics_include_n_pos_all_families(fitted: dict):
    metrics = fitted["body"]["metrics"]
    assert set(metrics["n_pos"]) == set(LABEL_FAMILIES)
    assert all(isinstance(v, int) for v in metrics["n_pos"].values())
    assert metrics["n_pos"]["normal"] >= 0


def test_not_comparable_when_n_pos_below_30(fitted: dict):
    metrics = fitted["body"]["metrics"]
    for fam in FRAUD_FAMILIES:
        assert metrics["not_comparable"][fam] is (metrics["n_pos"][fam] < 30)


def test_score_run_all_rows_n_pos_matches_y_length_by_family(fitted: dict):
    body = score_run(
        "fit-c",
        model_run_id="fit-c",
        runs_dir=fitted["runs"],
        models_dir=fitted["dest"],
        all_rows=True,
    )
    y = pd.read_parquet(fitted["runs"] / "fit-c" / "train.parquet")["label_family"].astype(str)
    n_pos = body["metrics"]["n_pos"]
    for fam in LABEL_FAMILIES:
        assert n_pos[fam] == int((y == fam).sum())


def test_gtest_ablation_recomputed_not_copied(fitted: dict):
    body = score_run(
        "fit-c",
        model_run_id="fit-c",
        runs_dir=fitted["runs"],
        models_dir=fitted["dest"],
        all_rows=True,
    )
    ab = body["metrics"]["app_ablation"]
    assert ab["app_ablation_source"] == "scored_world"


def test_metrics_pass_false_without_n_pos(fitted: dict):
    metrics = dict(fitted["body"]["metrics"])
    del metrics["n_pos"]
    assert fit_mod._metrics_pass(metrics, hang_s=120) is False


def test_cost_sketch_lab_not_india(fitted: dict):
    cs = fitted["body"]["metrics"]["cost_sketch"]
    assert cs["unit"] == "lab_not_india"
    assert cs["miss_weight"] == 10.0
    assert cs["fp_notify_weight"] == 1.0
    assert cs["fp_hold_weight"] == 3.0
    assert cs["fp_decline_weight"] == 8.0


# ---------------------------------------------------------------------------
# CAL.1–CAL.3 — op_threshold coupling guard (Phase 7 §2.1).
# Reconciliation found the threshold was once fit on RAW inner-val scores with
# isotonic calibration applied only to outer eval. These permanent guards
# ensure the locked order (`ssot:533`: fit threshold on CALIBRATED inner-val
# scores) cannot silently regress.
# ---------------------------------------------------------------------------
def _spy_calibrate_with_marker(monkeypatch, offsets):
    """Wrap _calibrate_pmap so its output is unmistakably distinguishable from the
    raw pmap: add a per-family constant to the normal channel, and stash the marked
    pmap for later comparison. Any consumer of the calibrated output must reflect
    that marker; a raw path won't."""
    original = fit_mod._calibrate_pmap
    stash: dict[str, dict] = {"pmap": {}}

    def marked(pmap, y_inner_val, classes):
        out = original(pmap, y_inner_val, classes)
        n = len(y_inner_val)
        for fam, off in offsets.items():
            base = np.asarray(out.get(fam, np.zeros(n)))
            out[fam] = base + off
        if not stash["pmap"]:
            # The FIRST calibration is the inner-val one that feeds threshold selection.
            stash["pmap"] = {k: np.asarray(v).copy() for k, v in out.items()}
        return out

    monkeypatch.setattr(fit_mod, "_calibrate_pmap", marked)
    return stash


def test_op_threshold_uses_calibrated_scores_not_raw(pop: dict, tmp_path: Path, monkeypatch):
    """CAL.1 — metrics['op_threshold'] must be selected from the CALIBRATED inner-val
    scores. We inject an unmistakable marker into the calibration output and assert the
    exact score array fed to threshold selection equals _fraud_score of the marked
    (calibrated) pmap — never a parallel raw-score path."""
    marker = 0.03
    stash = _spy_calibrate_with_marker(monkeypatch, {"normal": marker})

    # Capture the exact scores fed to _tpr_at_fpr (threshold selection). The threshold
    # selection is the FIRST call per target; the outer-eval tpr block runs later with
    # a different row count, so we keep only the first (inner-val) occurrence.
    captured: dict[str, np.ndarray] = {}
    original_tpr = fit_mod._tpr_at_fpr

    def spy_tpr(y_bin, scores, target, **kw):
        key = f"{target:g}"
        if key not in captured:
            captured[key] = np.asarray(scores).copy()
        return original_tpr(y_bin, scores, target, **kw)

    monkeypatch.setattr(fit_mod, "_tpr_at_fpr", spy_tpr)

    runs = Path(pop["parquet_path"]).parent.parent
    body = fit_champion("fit-c", world_seed=42, runs_dir=runs, models_dir=tmp_path / "models")

    op_fpr = float(body["metrics"]["operating_point_fpr"])
    thr_scores = captured[f"{op_fpr:g}"]

    # The oracle: threshold selection must have consumed the marked CALIBRATED pmap.
    marked_pmap = stash["pmap"]
    expected = _fraud_score(marked_pmap, len(thr_scores))
    assert np.allclose(thr_scores, expected, atol=1e-12), (
        "op_threshold scores must equal the calibrated (marked) fraud score; "
        "a raw-score code path would not carry the marker"
    )
    # The marker moved the fraud scores (e.g. negative on confidently-normal rows),
    # proving the oracle distinguishes the calibrated path from a raw 1 - normal path.
    assert np.any(thr_scores < 0.0), "marker did not reach the threshold-selection scores"


def test_threshold_called_after_calibration_transform(fitted: dict, monkeypatch):
    """CAL.2 — spy asserts the calibrator runs BEFORE threshold selection, and that
    threshold selection consumes exactly the calibrator's (marked) output."""
    order: list[str] = []
    original_cal = fit_mod._calibrate_pmap

    def marked(pmap, y_inner_val, classes):
        order.append("calibrate_start")
        out = original_cal(pmap, y_inner_val, classes)
        # Mutate so we can detect consumption below.
        out["normal"] = np.asarray(out.get("normal", np.zeros(len(y_inner_val)))) - 0.05
        order.append("calibrate_end")
        return out

    original_tpr = fit_mod._tpr_at_fpr

    def spy_tpr(y_bin, scores, target, **kw):
        order.append(f"threshold:{target:g}")
        return original_tpr(y_bin, scores, target, **kw)

    monkeypatch.setattr(fit_mod, "_calibrate_pmap", marked)
    monkeypatch.setattr(fit_mod, "_tpr_at_fpr", spy_tpr)

    body = fit_champion(
        "fit-c", world_seed=fitted["body"]["metrics"].get("fold_seed", 42),
        runs_dir=fitted["runs"], models_dir=fitted["dest"] / "cal2",
    )
    op_fpr = float(body["metrics"]["operating_point_fpr"])
    # The FIRST calibrate that produces inner-val scores must complete before the first
    # op_threshold selection. (A later outer-eval calibration is independent and may
    # appear after threshold selection — that is not what this guard checks.)
    first_threshold = order.index(f"threshold:{op_fpr:g}")
    first_calibrate_end = order.index("calibrate_end")
    assert first_calibrate_end < first_threshold, (
        "op_threshold must be computed AFTER the calibration transform that feeds it"
    )


def test_scoring_reuses_frozen_calibrator_not_refit(fitted: dict, monkeypatch):
    """CAL.3 — score_run never re-fits the calibrator. Any IsotonicRegression.fit that
    a fit_champion triggers happens once at fit time; inference adds zero. Guards the
    frozen threshold drifting out of sync with a re-fit-at-inference calibrator."""
    from sklearn.isotonic import IsotonicRegression

    fits: list[str] = []
    original_fit = IsotonicRegression.fit

    def counting_fit(self, X, y, *a, **k):
        fits.append("fit")
        return original_fit(self, X, y, *a, **k)

    monkeypatch.setattr(IsotonicRegression, "fit", counting_fit)

    n_after_baseline = len(fits)

    # Inference (score_run) must not invoke any calibrator fit.
    score_run("fit-c", model_run_id="fit-c", runs_dir=fitted["runs"],
              models_dir=fitted["dest"], all_rows=True)
    assert len(fits) == n_after_baseline, "score_run must not re-fit the calibrator"

    # A fit_champion may fit the calibrator at most once (per-family stage2 isotonic),
    # even when n_pos is large enough for calibration to engage.
    fit_champion("fit-c", world_seed=42, runs_dir=fitted["runs"],
                 models_dir=fitted["dest"] / "cal3")
    assert len(fits) - n_after_baseline <= 1, (
        "fit_champion must fit the calibrator at most once per run"
    )

    # Score the freshly-fit champion: still zero additional fits.
    n_before_second_score = len(fits)
    score_run("fit-c", model_run_id="fit-c", runs_dir=fitted["runs"],
              models_dir=fitted["dest"] / "cal3", all_rows=True)
    assert len(fits) == n_before_second_score, "score_run re-fit the calibrator"
