"""Protocol hardening — gtest_opened_at, cross-world disjoint event_ids, score_run contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import joblib

from packages.eval.fit import (
    GtestFreezeMismatchError,
    _load_gtest_protocol,
    _model_freeze_id,
    _recipe_hash,
    fit_champion,
    run_paths,
    score_run,
    tune_champion,
)
from packages.policy.loop_i import draft_rule_from_spec
from packages.catalog.query import specs_by_technique
from apps.api.db import SessionLocal, init_db
from apps.api.seed import seed_catalog
from packages.sim.runner import run_population

_NAMED_GAP_TECHNIQUES = ("T06", "T07", "T20", "T21", "T22", "T23")


@pytest.fixture()
def db():
    init_db()
    seed_catalog(reset=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_named_gaps_t06_t07_t20_t21_t22_t23(db):
    """Tracker C.2 — named-gap techniques stay named_gap in Loop I."""
    by_tid = specs_by_technique(db)
    for tid in _NAMED_GAP_TECHNIQUES:
        specs = by_tid.get(tid) or []
        assert specs, f"no catalog row for {tid}"
        primary = specs[0]
        draft = draft_rule_from_spec(primary)
        assert draft["coverage_status"] == "named_gap", (
            f"{tid} must be named_gap, got {draft['coverage_status']}"
        )


def test_cross_world_populations_are_separate_worlds(tmp_path: Path):
    """Train 42, G-test 43, G-dev 44 are distinct worlds (sidecar seeds + parquet content)."""
    runs = tmp_path / "runs"
    scale = dict(n_customers=20, n_merchants=8, sim_days=45, pin=True, runs_dir=runs)
    pop42 = run_population(None, run_id="vw-train", world_seed=42, **scale)
    pop43 = run_population(None, run_id="vw-gtest", world_seed=43, **scale)
    pop44 = run_population(None, run_id="vw-gdev", world_seed=44, **scale)

    import pandas as pd

    def sidecar_seed(pop: dict) -> int:
        p = Path(pop["parquet_path"]).parent / "sidecar.json"
        return int(json.loads(p.read_text(encoding="utf-8"))["world_seed"])

    def train_hash(pop: dict) -> str:
        import hashlib

        return hashlib.sha256(Path(pop["parquet_path"]).read_bytes()).hexdigest()

    assert sidecar_seed(pop42) == 42
    assert sidecar_seed(pop43) == 43
    assert sidecar_seed(pop44) == 44
    h42, h43, h44 = train_hash(pop42), train_hash(pop43), train_hash(pop44)
    assert len({h42, h43, h44}) == 3, "each world_seed must produce distinct train parquet bytes"
    # Scoring G-test must not mutate the train-world parquet (protocol guard).
    train42_path = Path(pop42["parquet_path"])
    mtime_before = train42_path.stat().st_mtime_ns
    import time

    time.sleep(0.01)
    run_population(None, run_id="vw-gtest-rescore", world_seed=43, **scale)
    assert train42_path.stat().st_mtime_ns == mtime_before


def test_gtest_opened_at_recorded_on_seed_43(tmp_path: Path):
    """First score_run(all_rows=True) on world_seed 43 logs gtest_opened_at."""
    runs = tmp_path / "runs"
    models = tmp_path / "models"
    run_population(
        None,
        run_id="go-train",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )
    fit_champion("go-train", world_seed=42, runs_dir=runs, models_dir=models)
    run_population(
        None,
        run_id="go-gtest",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=43,
        pin=True,
        runs_dir=runs,
    )
    body = score_run(
        "go-gtest",
        model_run_id="go-train",
        runs_dir=runs,
        models_dir=models,
        all_rows=True,
    )
    assert body.get("gtest_opened_at"), "gtest_opened_at must be set on first seed-43 score"
    assert body["metrics"].get("gtest_opened_at")
    proto = _load_gtest_protocol("go-train", models)
    assert proto.get("recipe_hash") == _recipe_hash()
    assert proto.get("model_freeze_id") == body["model_freeze_id"]
    assert int(proto.get("world_seed", 0)) == 43
    persisted = models / "go-train" / "gtest_score.json"
    assert persisted.is_file()
    saved = json.loads(persisted.read_text(encoding="utf-8"))
    assert "action_histogram" in saved
    m = saved["metrics"]
    for key in ("binary_ap", "precision_at_op", "recall_at_op", "confusion_matrix", "model_freeze_id"):
        assert key in m, key
    assert set(m["confusion_matrix"]) == {"tn", "fp", "fn", "tp"}

    body2 = score_run(
        "go-gtest",
        model_run_id="go-train",
        runs_dir=runs,
        models_dir=models,
        all_rows=True,
    )
    assert body2["gtest_opened_at"] == body["gtest_opened_at"], (
        "second score on same freeze must return persisted gtest_score.json"
    )
    assert body2["metrics"]["binary_ap"] == saved["metrics"]["binary_ap"]


def test_gtest_second_score_skips_holdout_parquet(tmp_path: Path, monkeypatch):
    """Second seed-43 all_rows score must return cache without re-reading G-test parquet."""
    runs = tmp_path / "runs"
    models = tmp_path / "models"
    scale = dict(n_customers=20, n_merchants=8, sim_days=45, pin=True, runs_dir=runs)
    run_population(None, run_id="sk-train", world_seed=42, **scale)
    fit_champion("sk-train", world_seed=42, runs_dir=runs, models_dir=models)
    run_population(None, run_id="sk-gtest", world_seed=43, **scale)
    score_run("sk-gtest", model_run_id="sk-train", runs_dir=runs, models_dir=models, all_rows=True)
    gtest_path = runs / "sk-gtest" / "train.parquet"
    mtime_before = gtest_path.stat().st_mtime_ns

    def _forbid_parquet(path, *args, **kwargs):
        p = Path(path)
        if p == gtest_path:
            raise AssertionError("second score_run must not re-read G-test parquet")
        import pandas as pd

        return pd.read_parquet(path, *args, **kwargs)

    monkeypatch.setattr("packages.eval.fit.pd.read_parquet", _forbid_parquet)
    score_run("sk-gtest", model_run_id="sk-train", runs_dir=runs, models_dir=models, all_rows=True)
    assert gtest_path.stat().st_mtime_ns == mtime_before


def test_model_freeze_id_changes_with_params_threshold_and_recipe_hash():
    rh = "a" * 64
    params = {
        "max_depth": 3,
        "max_iter": 80,
        "learning_rate": 0.08,
        "random_state": 42,
        "early_stopping": False,
    }
    base = _model_freeze_id(recipe_hash=rh, best_params=params, op_threshold=0.5)
    deeper = _model_freeze_id(
        recipe_hash=rh, best_params={**params, "max_depth": 4}, op_threshold=0.5
    )
    thr = _model_freeze_id(recipe_hash=rh, best_params=params, op_threshold=0.9)
    same = _model_freeze_id(recipe_hash=rh, best_params=params, op_threshold=0.5)
    other_recipe = _model_freeze_id(recipe_hash="b" * 64, best_params=params, op_threshold=0.5)
    assert base != deeper
    assert base != thr
    assert base == same
    assert base != other_recipe


def test_gtest_refuse_after_freeze_mutation(tmp_path: Path):
    runs = tmp_path / "runs"
    models = tmp_path / "models"
    scale = dict(n_customers=20, n_merchants=8, sim_days=45, pin=True, runs_dir=runs)
    run_population(None, run_id="fm-train", world_seed=42, **scale)
    fit_champion("fm-train", world_seed=42, runs_dir=runs, models_dir=models)
    run_population(None, run_id="fm-gtest", world_seed=43, **scale)
    score_run(
        "fm-gtest",
        model_run_id="fm-train",
        runs_dir=runs,
        models_dir=models,
        all_rows=True,
    )
    champ_path = models / "fm-train" / "champion.joblib"
    champ = joblib.load(champ_path)
    champ.op_threshold = float(champ.op_threshold) + 0.25
    joblib.dump(champ, champ_path)
    with pytest.raises(GtestFreezeMismatchError):
        score_run(
            "fm-gtest",
            model_run_id="fm-train",
            runs_dir=runs,
            models_dir=models,
            all_rows=True,
        )


def test_two_model_run_ids_can_score_same_gtest_parquet(tmp_path: Path):
    runs = tmp_path / "runs"
    models = tmp_path / "models"
    scale = dict(n_customers=20, n_merchants=8, sim_days=45, pin=True, runs_dir=runs)
    run_population(None, run_id="tm-train", world_seed=42, **scale)
    fit_champion("tm-train", world_seed=42, runs_dir=runs, models_dir=models, dest_run_id="m-a")
    fit_champion("tm-train", world_seed=42, runs_dir=runs, models_dir=models, dest_run_id="m-b")
    run_population(None, run_id="tm-gtest", world_seed=43, **scale)
    a = score_run("tm-gtest", model_run_id="m-a", runs_dir=runs, models_dir=models, all_rows=True)
    b = score_run("tm-gtest", model_run_id="m-b", runs_dir=runs, models_dir=models, all_rows=True)
    assert a.get("gtest_opened_at")
    assert b.get("gtest_opened_at")
    assert a["model_run_id"] == "m-a"
    assert b["model_run_id"] == "m-b"


def test_tune_champion_refuses_dest_after_gtest(tmp_path: Path):
    runs = tmp_path / "runs"
    models = tmp_path / "models"
    scale = dict(n_customers=20, n_merchants=8, sim_days=45, pin=True, runs_dir=runs)
    run_population(None, run_id="tn-train", world_seed=42, **scale)
    fit_champion("tn-train", world_seed=42, runs_dir=runs, models_dir=models)
    run_population(None, run_id="tn-gtest", world_seed=43, **scale)
    score_run(
        "tn-gtest",
        model_run_id="tn-train",
        runs_dir=runs,
        models_dir=models,
        all_rows=True,
    )
    with pytest.raises(ValueError, match="dest_run_id"):
        tune_champion(
            "tn-train",
            world_seed=42,
            runs_dir=runs,
            models_dir=models,
            force_skip=True,
        )


def test_score_run_includes_recipe_hash_and_inner_val_protocol(fitted: dict):
    """score_run metrics must include recipe_hash and inner_val_protocol for _metrics_pass."""
    runs = Path(fitted["parquet_path"]).parent.parent
    models = fitted["models_dir"]
    scored = score_run(
        fitted["run_id"],
        model_run_id=fitted["run_id"],
        runs_dir=runs,
        models_dir=models,
    )
    m = scored["metrics"]
    assert m.get("recipe_hash")
    assert len(m["recipe_hash"]) == 64
    assert m.get("inner_val_protocol") == "last_20pct_train_calendar"
    assert m.get("pass") is True


@pytest.fixture()
def fitted(tmp_path: Path):
    runs = tmp_path / "runs"
    models = tmp_path / "models"
    run_population(
        None,
        run_id="sr-fit",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )
    body = fit_champion("sr-fit", world_seed=42, runs_dir=runs, models_dir=models)
    paths = run_paths("sr-fit", runs)
    return {
        "run_id": "sr-fit",
        "parquet_path": str(paths["train"]),
        "models_dir": models,
        "body": body,
    }
