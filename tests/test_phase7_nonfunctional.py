"""Phase 7 §9 & §6 — production-readiness (non-functional) checks and the
Coverage/Identify handshake (C.4). These are additive system-level guards a
"production grade, scalable" claim needs that no single ticket owns."""

from __future__ import annotations

import json
import shutil
import time

import numpy as np
import pandas as pd
import pytest

from apps.api.db import init_db
from apps.api.seed import seed_catalog
from packages.eval import fit as fit_mod
from packages.eval.fit import (
    RecipeHashMismatchError,
    load_champion,
    run_paths,
    score_run,
)
from packages.eval.split import SPLIT_ONLY_COLUMNS, LeakError, assert_no_x_leak
from packages.policy.rule_hitl import (
    approve_draft,
    load_drafts,
    save_drafts,
)
from packages.policy.rules import (
    DEFAULT_RULES_PATH,
    FORBIDDEN_RULE_FIELDS,
    load_v0_rules,
)
from packages.sim.export import (
    TRAIN_DENYLIST,
    assert_train_schema,
    export_run,
)
from packages.sim.ledger import make_event
from packages.sim.runner import run_population


@pytest.fixture(scope="module")
def champ_fixture(tmp_path_factory):
    runs = tmp_path_factory.mktemp("runs-nf")
    run_population(
        None,
        run_id="nf-train",
        n_customers=20,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )
    models = tmp_path_factory.mktemp("models-nf")
    fit_mod.fit_champion("nf-train", world_seed=42, runs_dir=runs, models_dir=models)
    return {"runs": runs, "models": models}


def _batch_df(champ, n: int, rng: np.random.Generator) -> pd.DataFrame:
    cols = [c for c in champ.raw_columns if c != "label_family"]
    df = pd.DataFrame({c: rng.normal(size=n) for c in cols})
    return df


def test_nf1_throughput_scales_sublinear(champ_fixture):
    """NF.1 — score batches of 1k/5k/20k, assert batch_seconds_1k < 120 and that
    latency grows sub-quadratically with batch size (linear is sub-quadratic)."""
    champ = load_champion("nf-train", models_dir=champ_fixture["models"])
    rng = np.random.default_rng(0)
    df = pd.read_parquet(run_paths("nf-train", champ_fixture["runs"])["train"])
    del df["label_family"]
    df = df.reindex(columns=champ.raw_columns, fill_value=0)

    def time_batch(n: int) -> float:
        x = df.iloc[:n].copy()
        x = _batch_df(champ, n, rng)  # deterministic normal matrix of width |raw|+1
        x_enc, _ = fit_mod._encode(x, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
        t0 = time.perf_counter()
        champ.model.predict_proba(x_enc)
        return time.perf_counter() - t0

    t1k = time_batch(1000)
    t5k = time_batch(5000)
    t20k = time_batch(20000)

    assert t1k < 120, f"batch_seconds_1k must be < 120, got {t1k:.3f}"
    # Linear bound: 5k <= 5 * 1k and 20k <= 20 * 1k. If these fail, prediction scales
    # quadratically or worse (e.g. an accidental O(n^2) per-row loop or nested join).
    assert t5k <= 5 * t1k + 0.05, f"5k batch must scale linearly vs 1k ({t5k:.3f} vs {t1k:.3f})"
    assert t20k <= 20 * t1k + 0.1, f"20k batch must scale linearly vs 1k ({t20k:.3f} vs {t1k:.3f})"


def test_nf2_idempotent_fit_same_run(champ_fixture, tmp_path):
    """NF.2 — fitting the same run_id twice yields identical artifacts (no silent
    partial overwrite / drift). This is the product of the `make defend-fit` target."""
    models_a = tmp_path / "m-a"
    models_b = tmp_path / "m-b"
    a = fit_mod.fit_champion("nf-train", world_seed=42,
                             runs_dir=champ_fixture["runs"], models_dir=models_a)
    b = fit_mod.fit_champion("nf-train", world_seed=42,
                             runs_dir=champ_fixture["runs"], models_dir=models_b)
    assert a["metrics"]["n_train"] == b["metrics"]["n_train"]
    assert a["metrics"]["feature_columns"] == b["metrics"]["feature_columns"]
    assert a["metrics"]["recipe_hash"] == b["metrics"]["recipe_hash"]
    assert a["metrics"]["op_threshold"] == b["metrics"]["op_threshold"]


def test_nf3_crash_safety_generation(tmp_path):
    """NF.3 — simulate a killed write mid-run (train/split written but no _DONE) and
    assert fit_champion / run_paths refuse to read that run_id."""
    run_dir = tmp_path / "crashed"
    run_dir.mkdir(parents=True)
    (run_dir / "train.parquet").touch()
    (run_dir / "split.parquet").touch()
    (run_dir / "sidecar.json").write_text(json.dumps({"run_id": "crashed"}), encoding="utf-8")
    # no _DONE marker -> refuse
    with pytest.raises(FileNotFoundError, match="incomplete"):
        run_paths("crashed", runs_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="incomplete"):
        fit_mod.fit_champion("crashed", runs_dir=tmp_path)


def test_nf4_hitl_single_approval(tmp_path):
    """NF.4 — two approve calls on the same draft_id: exactly one succeeds and the live
    YAML gains exactly one rule. Optimistic lock: once the draft leaves 'proposed'
    status, the second call is rejected (never a double-apply into the live YAML)."""
    from packages.eval.fit import _recipe_hash

    rules_p = tmp_path / "v0_rules.yaml"
    drafts_p = tmp_path / "drafts.json"
    versions_p = tmp_path / "versions.json"
    backups_d = tmp_path / "backups"

    shutil.copy2(DEFAULT_RULES_PATH, rules_p)
    draft = {
        "id": "nf4-rule-001",
        "kind": "hard_flag",
        "applies_to": "mule",
        "family": "mule",
        "when": ["fan_in_1h >= 10"],
        "reason": "NF.4 concurrency flag",
        "status": "proposed",
        "recipe_hash": _recipe_hash(),
    }
    save_drafts([draft], drafts_p)

    n_before = len(load_v0_rules(rules_p))

    # First approve must succeed.
    approve_draft(
        "nf4-rule-001",
        rules_path=rules_p,
        drafts_path=drafts_p,
        versions_path=versions_p,
        backups_dir=backups_d,
    )

    # A second approve of the same draft is rejected (draft is no longer 'proposed').
    with pytest.raises(ValueError, match="cannot be approved"):
        approve_draft(
            "nf4-rule-001",
            rules_path=rules_p,
            drafts_path=drafts_p,
            versions_path=versions_p,
            backups_dir=backups_d,
        )

    n_after = len(load_v0_rules(rules_p))
    assert n_after == n_before + 1, "live YAML must gain exactly one rule"
    # The approved draft no longer has 'proposed' status.
    for d in load_drafts(drafts_p):
        if d["id"] == "nf4-rule-001":
            assert d["status"] == "approved"


def test_nf5_recipe_hash_mismatch_blocks_scoring(champ_fixture, tmp_path):
    """NF.5 — a champion.joblib whose manifest recipe_hash does not match the current
    features.json must refuse to score with a clear error, not a silent wrong number."""
    models = champ_fixture["models"]
    # Tamper with the manifest hash.
    base = models / "nf-train"
    manifest = json.loads((base / "model_manifest.json").read_text(encoding="utf-8"))
    manifest["recipe_hash"] = "0" * 64
    (base / "model_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RecipeHashMismatchError, match="features.json changed"):
        score_run("nf-train", model_run_id="nf-train",
                  runs_dir=champ_fixture["runs"], models_dir=models)


def test_nf6_error_path_no_denylist(champ_fixture):
    """NF.6 — force /defend/score to fail (unknown run_id) and assert the error
    response contains none of TRAIN_DENYLIST."""
    from fastapi.testclient import TestClient

    from apps.api.main import app

    with TestClient(app) as client:
        # 404 error path (missing run) → body must expose no denylist field.
        resp = client.post("/defend/score", json={"run_id": "no-such-run",
                                                  "model_run_id": "no-such-run"})
        assert resp.status_code == 404
        blob = resp.text
        for banned in TRAIN_DENYLIST:
            assert f'"{banned}"' not in blob, f"denylist leaked into error body: {banned}"


def test_nf7_leakage_regression_job():
    """NF.7 — standalone leak regression: assert_no_x_leak, assert_train_schema, and
    FORBIDDEN_RULE_FIELDS enforced as their own independent checks."""
    # assert_no_x_leak must reject split-only / denylist columns.
    with pytest.raises(LeakError):
        assert_no_x_leak(list(SPLIT_ONLY_COLUMNS))
    with pytest.raises(LeakError):
        assert_no_x_leak(["gstin"])
    with pytest.raises(LeakError):
        assert_no_x_leak(["label_family"])
    # assert_train_schema rejects denylist and non-allowlist columns.
    with pytest.raises(ValueError):
        assert_train_schema({"rail", "label_family", "vector_id"})
    with pytest.raises(ValueError):
        assert_train_schema({"totally_made_up_col"})
    # Denylist columns must be disallowed as rule fields.
    assert set(TRAIN_DENYLIST).issubset(FORBIDDEN_RULE_FIELDS)


def test_nf7b_no_denylist_in_export(tmp_path):
    """NF.7 — an exported train run stays allowlist-clean (gstin/payload absent)."""
    events = [
        make_event(
            seq=1,
            ts=pd.Timestamp("2024-01-01T10:00:00Z"),
            rail="upi_like",
            payer="VID-SIM-C-000001",
            payee="VID-SIM-M-000001",
            amount_minor=1000,
            label_family="normal",
            features_auth={"fan_in_1h": 0, "kyc_tier": "tier2"},
            kyc_tier="tier2",
        )
    ]
    export_run(events, {"run_id": "x", "world_seed": 42}, "x", runs_dir=tmp_path)
    assert_train_schema(tmp_path / "x" / "train.parquet")


def test_c4_approve_flips_case_only_to_live(postgres_required, tmp_path, monkeypatch):
    """C.4 — post-Phase-5 approve (tmp): a new rule field overlapping a case_only spec's
    features flips that cell to live_rule. We never fake 24 live_rule cells."""

    from apps.api.db import SessionLocal
    from packages.policy import coverage as coverage_mod
    from packages.policy.coverage import build_coverage_map
    from packages.policy.rules import parse_predicate

    init_db()
    seed_catalog(reset=True)
    db = SessionLocal()
    try:
        m0 = build_coverage_map(db)
        t17 = next(c for c in m0["cells"] if c["technique_id"] == "T17")
        assert t17["coverage_status"] == "case_only", "T17 must start as case_only"
        assert "copy_paste_payee_flag" in t17["features_expected"]
    finally:
        db.close()

    # Approve a live rule whose single field covers T17's expected feature.
    rules_p = tmp_path / "v0_rules.yaml"
    drafts_p = tmp_path / "drafts.json"
    versions_p = tmp_path / "versions.json"
    backups_d = tmp_path / "backups"
    shutil.copy2(DEFAULT_RULES_PATH, rules_p)
    from packages.eval.fit import _recipe_hash

    parse_predicate("copy_paste_payee_flag == true")  # field is allowlisted
    draft = {
        "id": "c4-rule",
        "kind": "hard_flag",
        "applies_to": "APP",
        "family": "app_fraud",
        "when": ["copy_paste_payee_flag == true"],
        "reason": "C.4 field-overlap flag",
        "status": "proposed",
        "recipe_hash": _recipe_hash(),
    }
    save_drafts([draft], drafts_p)
    approve_draft("c4-rule", rules_path=rules_p, drafts_path=drafts_p,
                  versions_path=versions_p, backups_dir=backups_d)
    approved = load_v0_rules(rules_p)
    assert any(r.id == "c4-rule" for r in approved)

    # Drive coverage with the approved (tmp) rule set.
    monkeypatch.setattr(coverage_mod, "load_v0_rules", lambda *a, **k: approved)
    db = SessionLocal()
    try:
        m1 = build_coverage_map(db)
    finally:
        db.close()

    t17_after = next(c for c in m1["cells"] if c["technique_id"] == "T17")
    assert t17_after["coverage_status"] == "live_rule", (
        "approving a rule that overlaps a case_only spec's fields must flip it to live_rule"
    )
