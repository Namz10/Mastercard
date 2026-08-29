"""Phase 8 — Loop T remediation-cycle orchestrator (Priority Arbitrator) tests.

Covers ORC.1–ORC.12 from the Phase 8 spec plus the §2 calm-down mining mirrors.
Fast path (decision logic) is unit-tested with fabricated input docs; the gated
checks that need the real G-dev worlds reuse a module fixture like test_loop_t's.
"""

from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
import yaml

import apps.api.routes.defend as defend_mod
import packages.eval.loop_t_orchestrator as orch
import packages.policy.rule_hitl as rule_hitl_mod
from apps.api.routes.defend import defend_rules_drafts
from packages.eval.fit import _recipe_hash, fit_champion
from packages.eval.loop_t import (
    TREE_FEATURE_ALLOWLIST,
    mine_fn_rules,
    mine_fp_calmdown_candidates,
)
from packages.eval.loop_t_orchestrator import (
    _cycle_id,
    _normalize_decision,
    apply_remediation_decision,
    build_remediation_cycle_input,
    recommend_remediation_action,
)
from packages.policy.rule_hitl import (
    approve_draft,
    load_drafts,
    reject_draft,
    save_drafts,
)
from packages.policy.rules import (
    DEFAULT_RULES_PATH,
    load_v0_rules,
    parse_predicate,
)
from packages.sim.runner import run_population

ORCH_FAMILY = "app_fraud"
ORCH_WHEN = ("fan_in_1h >= 5",)


# ---------------------------------------------------------------------------
# Fixtures & builders
# ---------------------------------------------------------------------------
def _cand(
    cid: str = "c-hard-1",
    kind: str = "hard_flag",
    applies_to: str = "APP",
    family: str = ORCH_FAMILY,
    when: tuple[str, ...] = ORCH_WHEN,
) -> dict:
    when_l = list(when)
    metrics = (
        {"gate_genuine_fpr": 0.001, "gate_incremental_recall": 0.05}
        if kind == "hard_flag"
        else {"cd_calm_coverage": 0.8, "cd_over_calm": 0.01}
    )
    return {
        "id": cid,
        "kind": kind,
        "applies_to": applies_to,
        "family": family,
        "when": when_l,
        "reason": " AND ".join(when_l),
        "status": "proposed",
        "recipe_hash": "deadbeef",
        "created_at": "2026-08-29T00:00:00+00:00",
        "metrics": metrics,
        "leaf_precision": 0.9,
        "leaf_support": 40,
        "path_length": len(when_l),
        "jaccard_max_vs_live": 0.0,
        "duplicate_of_live_rule": None,
        "forbidden_field_hit": False,
    }


def _input_doc(
    gdev_run_id: str = "gdev44",
    train_run_id: str = "train42",
    date: str = "2026-08-29",
    candidates: list[dict] | None = None,
) -> dict:
    cands = candidates if candidates is not None else [_cand()]
    return {
        "gdev_run_id": gdev_run_id,
        "train_run_id": train_run_id,
        "world_seed": 44,
        "date": date,
        "recipe_hash": "deadbeef",
        "cycle_id": _cycle_id(gdev_run_id, train_run_id, date),
        "gdev_stats": {"n_rows": 100, "n_fraud": 10, "n_genuine": 90},
        "gdev_gate_stats": {"n_rows": 45, "n_fraud": 4, "n_genuine": 41},
        "fn_opportunities": [],
        "flagged_rules": [],
        "verify_candidates": cands,
        "live_rule_summary": {"total": 0, "by_kind": {}},
        "enqueued_drafts": [],
        "prior_cycle_approved": 0,
    }


class StubProvider:
    def __init__(self, out: dict | None = None, exc: Exception | None = None):
        self.out = out
        self.exc = exc
        self.last_meta = {"provider": "stub", "model": "stub", "schema_mode": "json_object", "wire_attempts": 1}

    def complete_json(self, **kwargs: object) -> dict:
        if self.exc is not None:
            raise self.exc
        return dict(self.out or {})


@pytest.fixture(scope="module")
def pop_orch(tmp_path_factory) -> dict:
    runs = tmp_path_factory.mktemp("runs-orch")
    models = tmp_path_factory.mktemp("models-orch")
    run_population(
        None,
        run_id="train42",
        n_customers=25,
        n_merchants=8,
        sim_days=45,
        world_seed=42,
        pin=True,
        runs_dir=runs,
    )
    fit_champion("train42", world_seed=42, runs_dir=runs, models_dir=models)
    run_population(
        None,
        run_id="gdev44",
        n_customers=25,
        n_merchants=8,
        sim_days=45,
        world_seed=44,
        pin=True,
        runs_dir=runs,
    )
    return {"runs": runs, "models": models, "train_id": "train42", "gdev_id": "gdev44"}


def _tmp_rules(tmp_path: Path) -> Path:
    rules_p = tmp_path / "v0_rules.yaml"
    shutil.copy2(DEFAULT_RULES_PATH, rules_p)
    return rules_p


# ---------------------------------------------------------------------------
# ORC.1 — never open seed-43 / gtest (STOP-GATE)
# ---------------------------------------------------------------------------
def test_orc1_build_never_opens_seed_43(tmp_path: Path, monkeypatch):
    calls: list[str] = []
    real_run_paths = orch.run_paths

    def spy(run_id: str, runs_dir: Path | None = None) -> dict:
        calls.append(str(run_id))
        raise AssertionError("remediation must raise before opening gtest parquet")

    monkeypatch.setattr(orch, "run_paths", spy)
    with pytest.raises(ValueError, match="never seed 43"):
        build_remediation_cycle_input("make-gtest", "train42", runs_dir=tmp_path)
    assert not calls, "orchestrator must not call run_paths for a seed-43 id"
    monkeypatch.setattr(orch, "run_paths", real_run_paths)

    with pytest.raises(ValueError, match="never seed 43"):
        build_remediation_cycle_input("run_seed43", "train42", runs_dir=tmp_path)


def test_orc1_calmdown_never_opens_seed_43():
    with pytest.raises(ValueError, match="never seed 43"):
        mine_fp_calmdown_candidates("make-gtest", "any-live-rule")

    with pytest.raises(ValueError, match="never seed 43"):
        mine_fp_calmdown_candidates("run_seed43", "any-live-rule")


# ---------------------------------------------------------------------------
# ORC.2 — build returns G-dev mine stats and G-dev gate stats as separate keys
# ---------------------------------------------------------------------------
def test_orc2_build_stats(pop_orch: dict, tmp_path: Path):
    runs = pop_orch["runs"]
    models = pop_orch["models"]
    rules_p = _tmp_rules(tmp_path)

    inp = build_remediation_cycle_input(
        pop_orch["gdev_id"],
        pop_orch["train_id"],
        runs_dir=runs,
        models_dir=models,
        rules_path=rules_p,
    )
    assert inp["world_seed"] == 44
    assert "gdev_stats" in inp and "gdev_gate_stats" in inp
    gdev_paths = orch.run_paths(pop_orch["gdev_id"], runs)
    n_total = pd.read_parquet(gdev_paths["train"]).shape[0]
    assert inp["gdev_stats"]["n_rows"] + inp["gdev_gate_stats"]["n_rows"] == n_total
    assert set(inp) >= {"flagged_rules", "fn_opportunities", "verify_candidates",
                        "live_rule_summary", "enqueued_drafts", "cycle_id", "recipe_hash"}


# ---------------------------------------------------------------------------
# ORC.3 — invented rule ids are dropped (deterministic)
# ---------------------------------------------------------------------------
def test_orc3_invented_ids_dropped():
    doc = _input_doc(candidates=[_cand()])
    raw = {
        "verdict": "submit",
        "reason": "ok",
        "in_focus_families": [ORCH_FAMILY],
        "error": None,
        "items": [
            {"action": "fn", "rule_id": "c-hard-1", "kind": "hard_flag",
             "applies_to": "APP", "family": ORCH_FAMILY, "when": None, "reason": "good"},
            {"action": "fn", "rule_id": "c-id-9999", "kind": "hard_flag",
             "applies_to": "APP", "family": None, "when": None, "reason": "invented"},
            {"action": "fn", "rule_id": "c-hard-1", "kind": "calm_down",
             "applies_to": "APP", "family": None, "when": None, "reason": "kind mismatch"},
        ],
    }
    normalized = _normalize_decision(raw, doc, 3)
    assert [i["rule_id"] for i in normalized["items"]] == ["c-hard-1"]
    assert normalized["items"][0]["when"] == list(ORCH_WHEN)


# ---------------------------------------------------------------------------
# ORC.4 — unknown reasons / verdicts coerce to fail-closed
# ---------------------------------------------------------------------------
def test_orc4_unknown_reason_coerced():
    doc = _input_doc()
    raw = {"verdict": "lie", "reason": "", "in_focus_families": ["madeup"],
           "error": None, "items": [1, 2, "x"]}
    normalized = _normalize_decision(raw, doc, 3)
    assert normalized["verdict"] == "stop"
    assert normalized["reason"] == "orchestrator_reject_unclassified"
    assert normalized["items"] == []
    assert normalized["in_focus_families"] == []


# ---------------------------------------------------------------------------
# ORC.5 — LLM failure => fail closed: no queue change, one ledger entry
# ---------------------------------------------------------------------------
def test_orc5_fail_closed_llm_unavailable(tmp_path: Path):
    doc = _input_doc(date="2026-08-05")
    ledger_p = tmp_path / "ledger.jsonl"
    drafts_p = tmp_path / "drafts.json"

    # The provider-less decision path is exactly apply(None) — fail closed.
    res = apply_remediation_decision(doc, None, flags={"orchestrator_enabled": True, "reviewer_capacity_hint": 3},
                                     drafts_path=drafts_p, ledger_path=ledger_p)
    assert res["enqueued"] == 0
    assert res["auto_rejected"] == 0
    assert not drafts_p.is_file(), "fail-closed must not create drafts.json"
    entries = [json.loads(l) for l in ledger_p.read_text().splitlines() if l.strip()]
    assert len(entries) == 1
    assert entries[0]["verdict"] == "stop"
    assert "orchestrator_fail_closed" in entries[0]["reason"]


def test_orc5_recommend_returns_none_on_failure(pop_orch: dict, tmp_path: Path):
    provider = StubProvider(exc=ValueError("no route"))
    assert recommend_remediation_action(_input_doc(), provider) is None


def test_orc5_end_to_end_kill_switch_off_raises(pop_orch: dict, tmp_path: Path):
    with pytest.raises(orch.OrchestratorDisabledError):
        orch.run_remediation_cycle(
            gdev_run_id=pop_orch["gdev_id"],
            train_run_id=pop_orch["train_id"],
            provider=StubProvider(out={"verdict": "submit", "reason": "x", "items": [],
                                       "in_focus_families": [], "error": None}),
            date="2026-08-05",
            runs_dir=pop_orch["runs"],
            models_dir=pop_orch["models"],
            rules_path=_tmp_rules(tmp_path),
            drafts_path=tmp_path / "drafts.json",
            ledger_path=tmp_path / "ledger.jsonl",
            flags={"orchestrator_enabled": False, "reviewer_capacity_hint": 3},
        )


# ---------------------------------------------------------------------------
# ORC.6 — capacity breach => fail closed (enqueue nothing)
# ---------------------------------------------------------------------------
def test_orc6_capacity_breach_fails_closed(tmp_path: Path):
    cands = [_cand(cid=f"c-{i}") for i in range(4)]
    doc = _input_doc(date="2026-08-06", candidates=cands)
    decision = {
        "verdict": "submit",
        "reason": "lots",
        "items": [{"action": "fn", "rule_id": c["id"], "kind": "hard_flag",
                   "applies_to": "APP", "family": ORCH_FAMILY, "when": c["when"], "reason": "x"}
                  for c in cands],
        "in_focus_families": [ORCH_FAMILY],
        "reviewer_capacity_hint": 3,
        "error": None,
    }
    drafts_p = tmp_path / "drafts.json"
    ledger_p = tmp_path / "ledger.jsonl"
    res = apply_remediation_decision(doc, decision,
                                     flags={"orchestrator_enabled": True, "reviewer_capacity_hint": 3},
                                     drafts_path=drafts_p, ledger_path=ledger_p)
    assert res["status"] == "capacity_breach"
    assert res["enqueued"] == 0
    assert not drafts_p.is_file()


def test_orc6_capacity_ok_under_hint(tmp_path: Path):
    doc = _input_doc(date="2026-08-07", candidates=[_cand()])
    decision = {
        "verdict": "submit",
        "reason": "ok",
        "items": [{"action": "fn", "rule_id": "c-hard-1", "kind": "hard_flag",
                   "applies_to": "APP", "family": ORCH_FAMILY, "when": None, "reason": "keep"}],
        "in_focus_families": [ORCH_FAMILY],
        "reviewer_capacity_hint": 3,
        "error": None,
    }
    drafts_p = tmp_path / "drafts.json"
    ledger_p = tmp_path / "ledger.jsonl"
    res = apply_remediation_decision(doc, decision,
                                     flags={"orchestrator_enabled": True, "reviewer_capacity_hint": 3},
                                     drafts_path=drafts_p, ledger_path=ledger_p)
    assert res["status"] == "applied"
    assert res["enqueued"] == 1
    drafts = load_drafts(drafts_p)
    assert drafts[0]["id"] == "c-hard-1"
    assert drafts[0]["status"] == "proposed"
    assert drafts[0]["cycle_id"] == doc["cycle_id"]


# ---------------------------------------------------------------------------
# ORC.7 — auto_rejected invisible in default view
# ---------------------------------------------------------------------------
def test_orc7_auto_rejected_invisible_by_default(monkeypatch, tmp_path: Path):
    drafts_p = tmp_path / "drafts.json"
    monkeypatch.setattr(rule_hitl_mod, "DEFAULT_DRAFTS_PATH", drafts_p)
    save_drafts(
        [
            {"id": "a", "status": "proposed"},
            {"id": "b", "status": "auto_rejected", "auto_reject_reason": "pressed"},
            {"id": "c", "status": "approved"},
            {"id": "d", "status": "rejected"},
        ],
        drafts_p,
    )

    default = defend_rules_drafts()
    assert {i["id"] for i in default["items"]} == {"a"}

    explicit = defend_rules_drafts(status="auto_rejected")
    assert {i["id"] for i in explicit["items"]} == {"b"}


# ---------------------------------------------------------------------------
# ORC.8 — approve() promotes an auto_rejected draft to live
# ---------------------------------------------------------------------------
def test_orc8_approve_promotes_auto_rejected(tmp_path: Path):
    rules_p = _tmp_rules(tmp_path)
    drafts_p = tmp_path / "drafts.json"
    versions_p = tmp_path / "versions.json"
    backups_d = tmp_path / "backups"
    draft = {
        "id": "loop-t-pressed-1",
        "kind": "calm_down",
        "applies_to": "genuine",
        "family": ORCH_FAMILY,
        "when": ["fan_in_1h >= 9"],
        "reason": "calm the fan-in floor",
        "status": "auto_rejected",
        "auto_reject_reason": "orchestrator judge pressed",
        "rejected_by": "orchestrator",
        "cycle_id": "cycle-abc",
        "recipe_hash": _recipe_hash(),
    }
    save_drafts([draft], drafts_p)

    approved = approve_draft(
        "loop-t-pressed-1",
        rules_path=rules_p,
        drafts_path=drafts_p,
        versions_path=versions_p,
        backups_dir=backups_d,
    )
    assert approved["status"] == "approved"
    assert "loop-t-pressed-1" in {r.id for r in load_v0_rules(rules_p)}


def test_orc8_reject_denied_for_auto_rejected(tmp_path: Path):
    drafts_p = tmp_path / "drafts.json"
    save_drafts(
        [{"id": "loop-t-pressed-2", "status": "auto_rejected", "when": []}],
        drafts_p,
    )
    with pytest.raises(ValueError, match="cannot be rejected"):
        reject_draft("loop-t-pressed-2", drafts_path=drafts_p)


# ---------------------------------------------------------------------------
# ORC.9 — stop verdict produces no drafts at all (STOP-GATE, shared with 7.6)
# ---------------------------------------------------------------------------
def test_orc9_stop_verdict_no_drafts(tmp_path: Path):
    doc = _input_doc(date="2026-08-09", candidates=[_cand()])
    decision = {
        "verdict": "stop",
        "reason": "no remediation needed this cycle",
        "items": [],
        "in_focus_families": [],
        "reviewer_capacity_hint": 3,
        "error": None,
    }
    drafts_p = tmp_path / "drafts.json"
    ledger_p = tmp_path / "ledger.jsonl"
    res = apply_remediation_decision(doc, decision,
                                     flags={"orchestrator_enabled": True, "reviewer_capacity_hint": 3},
                                     drafts_path=drafts_p, ledger_path=ledger_p)
    assert res["enqueued"] == 0
    assert not drafts_p.is_file()
    entries = [json.loads(l) for l in ledger_p.read_text().splitlines() if l.strip()]
    assert entries[0]["verdict"] == "stop"


# ---------------------------------------------------------------------------
# ORC.10 — the orchestrator never calls reject_draft / Loop M
# ---------------------------------------------------------------------------
def test_orc10_no_reject_draft_and_no_new_routes():
    src = inspect.getsource(defend_mod)
    assert "/loop-t/mine" in src
    assert "/rules/drafts" in src
    assert "/rules/approve/" in src
    assert "/rules/reject/" in src
    assert "/rules/edit" not in src
    assert "fp-propose" not in src

    orch_src = inspect.getsource(orch)
    assert "reject_draft" not in orch_src
    assert "run_loop_m" not in orch_src


# ---------------------------------------------------------------------------
# ORC.11 — deterministic rejects never enter the verify set (they bypass the LLM)
# ---------------------------------------------------------------------------
def test_orc11_deterministic_rejects_never_in_verify_set(pop_orch: dict, tmp_path: Path):
    runs = pop_orch["runs"]
    models = pop_orch["models"]
    rules_p = _tmp_rules(tmp_path)

    inp = build_remediation_cycle_input(
        pop_orch["gdev_id"],
        pop_orch["train_id"],
        runs_dir=runs,
        models_dir=models,
        rules_path=rules_p,
    )
    for cand in inp["verify_candidates"]:
        assert cand["duplicate_of_live_rule"] is None, f"dup of {cand['duplicate_of_live_rule']!r}"
        assert cand["forbidden_field_hit"] is False
        if cand["kind"] == "hard_flag":
            assert cand["metrics"]["gate_genuine_fpr"] <= 0.002
        else:
            assert cand["metrics"]["cd_over_calm"] <= 0.05


def test_orc11_jaccard_dup_candidate_not_emitted(pop_orch: dict, tmp_path: Path):
    runs = pop_orch["runs"]
    models = pop_orch["models"]
    rules_p = _tmp_rules(tmp_path)

    # Add a live hard_flag that is an exact duplicate of what mining would emit:
    # the (single-predicate) FN catch rule on fan_in_1h.
    dup_live = {
        "id": "dupe-live",
        "kind": "hard_flag",
        "applies_to": "APP",
        "when": ["fan_in_1h >= 5"],
        "status": "live",
        "reason": "already live",
    }
    existing = yaml.safe_load(rules_p.read_text(encoding="utf-8"))
    assert isinstance(existing, list)
    existing.append(dup_live)
    rules_p.write_text(yaml.safe_dump(existing, sort_keys=False), encoding="utf-8")

    res = mine_fn_rules(
        pop_orch["train_id"],
        pop_orch["gdev_id"],
        ORCH_FAMILY,
        runs_dir=runs,
        models_dir=models,
        rules_path=rules_p,
        drafts_path=tmp_path / "drafts.json",
        persist=False,
    )
    assert res["status"] in {"success", "skipped"}
    for cand in res.get("candidates") or []:
        assert cand.get("duplicate_of_live_rule") is None
        assert cand.get("jaccard_max_vs_live", 0.0) <= 0.80


# ---------------------------------------------------------------------------
# ORC.12 — defer/stop never enqueues, never triggers Loop M
# ---------------------------------------------------------------------------
def test_orc12_defer_holds(tmp_path: Path):
    doc = _input_doc(date="2026-08-12", candidates=[_cand()])
    decision = {
        "verdict": "defer",
        "reason": "wait for next batch",
        "items": [{"action": "fn", "rule_id": "c-hard-1", "kind": "hard_flag",
                   "applies_to": "APP", "family": ORCH_FAMILY, "when": None, "reason": "later"}],
        "in_focus_families": [],
        "reviewer_capacity_hint": 3,
        "error": None,
    }
    drafts_p = tmp_path / "drafts.json"
    ledger_p = tmp_path / "ledger.jsonl"
    res = apply_remediation_decision(doc, decision,
                                     flags={"orchestrator_enabled": True, "reviewer_capacity_hint": 3},
                                     drafts_path=drafts_p, ledger_path=ledger_p)
    assert res["enqueued"] == 0
    assert not drafts_p.is_file()
    entries = [json.loads(l) for l in ledger_p.read_text().splitlines() if l.strip()]
    assert entries[0]["verdict"] == "defer"


# ---------------------------------------------------------------------------
# Idempotency — identical (gdev, train, date) rerun is a ledger no-op
# ---------------------------------------------------------------------------
def test_cycle_idempotent(tmp_path: Path):
    doc = _input_doc(date="2026-08-13", candidates=[_cand()])
    decision = {
        "verdict": "submit",
        "reason": "ok",
        "items": [{"action": "fn", "rule_id": "c-hard-1", "kind": "hard_flag",
                   "applies_to": "APP", "family": ORCH_FAMILY, "when": None, "reason": "keep"}],
        "in_focus_families": [ORCH_FAMILY],
        "reviewer_capacity_hint": 3,
        "error": None,
    }
    flags = {"orchestrator_enabled": True, "reviewer_capacity_hint": 3}
    drafts_p = tmp_path / "drafts.json"
    ledger_p = tmp_path / "ledger.jsonl"

    first = apply_remediation_decision(doc, decision, flags=flags, drafts_path=drafts_p, ledger_path=ledger_p)
    assert first["enqueued"] == 1

    second = apply_remediation_decision(doc, dict(decision, items=[]), flags=flags,
                                        drafts_path=drafts_p, ledger_path=ledger_p)
    assert second["status"] == "duplicate"
    assert second["enqueued"] == 0
    assert len(load_drafts(drafts_p)) == 1
    assert len([l for l in ledger_p.read_text().splitlines() if l.strip()]) == 1


# ---------------------------------------------------------------------------
# recommend_remediation_action — schema round-trip through a stub
# ---------------------------------------------------------------------------
def test_recommend_round_trip(pop_orch: dict):
    doc = _input_doc(candidates=[_cand()])
    decision = {
        "verdict": "submit",
        "reason": "queue the honest catch",
        "in_focus_families": [ORCH_FAMILY],
        "error": None,
        "items": [
            {"action": "press", "rule_id": "c-hard-1", "kind": "hard_flag",
             "applies_to": "APP", "family": ORCH_FAMILY, "when": ["invented"], "reason": "actually bad"},
        ],
    }
    out = recommend_remediation_action(doc, StubProvider(out=decision), flags={"reviewer_capacity_hint": 3})
    assert out is not None
    assert out["verdict"] == "submit"
    assert out["items"][0]["when"] == list(ORCH_WHEN), "LLM cannot inject when clauses"
    assert out["llm_meta"]["provider"] == "stub"


def test_recommend_schema_name_is_remediation_decision(pop_orch: dict):
    seen: dict[str, str] = {}

    class RecordingProvider(StubProvider):
        def complete_json(self, **kw: object) -> dict:
            seen["schema_name"] = str(kw.get("schema_name"))
            seen["user_len"] = str(len(str(kw.get("user"))))
            return {"verdict": "stop", "reason": "x", "items": [], "in_focus_families": [], "error": None}

    out = recommend_remediation_action(_input_doc(), RecordingProvider(),
                                       flags={"reviewer_capacity_hint": 3})
    assert out is not None
    assert seen["schema_name"] == "RemediationDecision"
    assert int(seen["user_len"]) > 0


# ---------------------------------------------------------------------------
# Calm-down miner mirrors of the 7.1 / 7.3 / 7.4 gates
# ---------------------------------------------------------------------------
def _flagged_rule_for_calmdown(pop_orch: dict, tmp_path: Path):
    """Fixture hard rule that fires on most genuine rows, so fp_inbox flags it."""
    runs = pop_orch["runs"]
    rules_p = _tmp_rules(tmp_path)
    raw = yaml.safe_load(rules_p.read_text(encoding="utf-8"))
    raw.append({
        "id": "detrimental-broad",
        "kind": "hard_flag",
        "applies_to": "APP",
        "when": ["is_new_payee == false"],
        "status": "live",
        "reason": "fixture detrimental rule",
    })
    rules_p.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    gdev_train = pd.read_parquet(orch.run_paths(pop_orch["gdev_id"], runs)["train"])
    flagged = [f for f in orch.fp_inbox(gdev_train, rules=load_v0_rules(rules_p), threshold=0.005)
               if f["id"] == "detrimental-broad"]
    return runs, rules_p, (flagged[0] if flagged else None)


def test_calmdown_candidates_parse_and_allowlist(pop_orch: dict, tmp_path: Path):
    runs, rules_p, flagged = _flagged_rule_for_calmdown(pop_orch, tmp_path)
    if flagged is None:
        pytest.skip("fixture detrimental rule was not flagged")
    res = mine_fp_calmdown_candidates(
        pop_orch["gdev_id"], flagged["id"], runs_dir=runs, models_dir=pop_orch["models"], rules_path=rules_p
    )
    if res.get("status") != "success" or not res.get("candidates"):
        pytest.skip("no calm-down candidates mined on fixture population")

    for cand in res["candidates"]:
        for clause in cand["when"]:
            pred = parse_predicate(clause)
            assert pred.field in set(TREE_FEATURE_ALLOWLIST)
            assert pred.op in {"==", "!=", ">=", "<=", ">", "<"}
        assert cand["kind"] == "calm_down"
        assert cand["applies_to"] == "genuine"
        assert cand["metrics"]["cd_over_calm"] <= 0.05
        assert cand["metrics"]["cd_calm_coverage"] >= 0.70


def test_orc11_calmdown_dup_never_in_verify_set(pop_orch: dict, tmp_path: Path):
    """Novelty gate: anything that reaches candidates is not a duplicate of a
    live calm_down clause (duplicate_of_live_rule must be None)."""
    runs, rules_p, flagged = _flagged_rule_for_calmdown(pop_orch, tmp_path)
    if flagged is None:
        pytest.skip("fixture detrimental rule was not flagged")
    res = mine_fp_calmdown_candidates(
        pop_orch["gdev_id"], flagged["id"], runs_dir=runs, models_dir=pop_orch["models"], rules_path=rules_p
    )
    mends = res.get("candidates") or []
    if not mends:
        pytest.skip("no calm-down candidates mined on fixture population")
    for cand in mends:
        assert cand.get("duplicate_of_live_rule") is None
        assert cand["jaccard_max_vs_live"] <= 0.80
        assert cand["forbidden_field_hit"] is False