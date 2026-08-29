"""Phase 8 — Loop T remediation-cycle orchestrator (priority arbitrator).

A bounded, single-review-pass decision layer that sits *in front of* the Phase 5
Loop T mine/backtest/HITL pipeline. One LLM call per cycle verdicts the mined
verify set; the orchestrator writes the outcome (propose / auto-reject / hold) to
data/remediation/ledger.jsonl, and enqueues drafts for a human exactly like the
today flow — never approving, never mutating rules, never calling Loop M on its own.

Guarantees
----------
- One model call per cycle; no tools, no retries, no follow-up turns.
- Fail closed: any LLM error / malformed / unknown verdict / capacity breach leaves
  the queue untouched and records one ledger entry with the reason.
- Stop-gate: this module never opens a seed-43 / G-test parquet (guard mirrors
  mine_fn_rules; ORC.1).
- Determinism: candidate ids/when are derived from mined candidates, never from
  the LLM; invented rule ids are dropped (ORC.3); unknown reasons are coerced to
  ``orchestrator_reject_unclassified`` (ORC.4).
- Deterministic rejects (Jaccard, FPR/recall/augment gates) reject a candidate
  before it ever reaches the LLM or drafts.json (ORC.11).
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.config.ml import load_remediation_flags
from packages.eval.fit import _recipe_hash, load_recipe, run_paths
from packages.eval.loop_t import (
    FRAUD_FAMILIES,
    fn_opportunities,
    fp_inbox,
    mine_fn_rules,
    mine_fp_calmdown_candidates,
)
from packages.policy.rule_hitl import DEFAULT_DRAFTS_PATH, load_drafts, save_drafts
from packages.policy.rules import load_v0_rules
from packages.sim.export import RUNS_DIR

_REMEDIATION_DIR = Path(__file__).resolve().parents[2] / "data" / "remediation"
DEFAULT_LEDGER_PATH = _REMEDIATION_DIR / "ledger.jsonl"

# Same calendar 70/30 rule that mine_fn_rules uses to build its mine/gate slices.
_GDEV_MINE_FRACTION = 0.70

_VERDICTS = frozenset({"stop", "defer", "submit"})
_ACTIONS = frozenset({"press", "calm_down", "fn"})
_KINDS = frozenset({"hard_flag", "calm_down"})
_MAX_ITEMS = 7

_IN_FLIGHT_CYCLES: set[str] = set()
_IN_FLIGHT_LOCK = threading.Lock()
_LEDGER_LOCK = threading.Lock()


class OrchestratorError(RuntimeError):
    """Raised on deterministic orchestrator failures (never on LLM uncertainty)."""


class OrchestratorDisabledError(OrchestratorError):
    """Kill switch off — orchestrator must not run."""


# ---------------------------------------------------------------------------
# §2 prerequisite caveat — the FP calm-down generator now exists (mine_fp_calmdown_candidates)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Ledger
# ---------------------------------------------------------------------------
def _cycle_id(gdev_run_id: str, train_run_id: str, date: str) -> str:
    digest = hashlib.sha256(f"{gdev_run_id}:{train_run_id}:{date}".encode()).hexdigest()
    return f"cycle-{digest[:12]}"


def _load_ledger(path: Path | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else DEFAULT_LEDGER_PATH
    if not p.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _append_ledger(entry: dict[str, Any], path: Path | None = None) -> None:
    p = Path(path) if path else DEFAULT_LEDGER_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with _LEDGER_LOCK, p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


# ---------------------------------------------------------------------------
# §3 — RemediationCycleInput (deterministic snapshot, assembled from G-dev only)
# ---------------------------------------------------------------------------
def _gdev_split(gdev_run_id: str, runs_dir: Path) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """G-dev mine/gate stats without opening any seed-43 sidecar."""
    if "43" in str(gdev_run_id) or "gtest" in str(gdev_run_id).lower():
        raise ValueError(f"remediation cycle must run on G-dev seed 44, never seed 43 / gtest ({gdev_run_id})")
    gdev_paths = run_paths(gdev_run_id, runs_dir)
    train = pd.read_parquet(gdev_paths["train"])
    split = pd.read_parquet(gdev_paths["split"])
    ts = pd.to_datetime(split["event_ts"], utc=True, format="ISO8601")
    t0, t1 = ts.min(), ts.max()
    cut = t0 + (t1 - t0) * _GDEV_MINE_FRACTION
    mine_mask = (ts < cut).to_numpy()
    gate_mask = (ts >= cut).to_numpy()
    y = train["label_family"].astype(str)

    def _stats(mask: np.ndarray) -> dict[str, Any]:
        rows = int(mask.sum())
        fraud = int((y.to_numpy()[mask] != "normal").sum())
        genuine = rows - fraud
        return {"n_rows": rows, "n_fraud": fraud, "n_genuine": genuine}

    return train, _stats(mine_mask), _stats(gate_mask)


def _maybe_mine_family(
    opp: dict[str, Any],
    train_run_id: str,
    gdev_run_id: str,
    runs_dir: Path,
    models_dir: Path,
    rules_path: Path,
    min_fn: int,
    min_genuine_gate: int,
) -> list[dict[str, Any]]:
    if int(opp["n_fn"]) < min_fn or int(opp["n_genuine_gate"]) < min_genuine_gate:
        return []
    res = mine_fn_rules(
        train_run_id,
        gdev_run_id,
        opp["family"],
        runs_dir=runs_dir,
        models_dir=models_dir,
        rules_path=rules_path,
        persist=False,
    )
    if res.get("status") != "success":
        return []
    return list(res.get("candidates") or [])


def _maybe_mine_calmdown(
    flagged: dict[str, Any],
    gdev_run_id: str,
    runs_dir: Path,
    models_dir: Path,
    rules_path: Path,
) -> list[dict[str, Any]]:
    try:
        res = mine_fp_calmdown_candidates(
            gdev_run_id,
            flagged["id"],
            runs_dir=runs_dir,
            models_dir=models_dir,
            rules_path=rules_path,
        )
    except KeyError:
        return []
    if res.get("status") != "success":
        return []
    return list(res.get("candidates") or [])


def build_remediation_cycle_input(
    gdev_run_id: str,
    train_run_id: str,
    *,
    world_seed: int = 44,
    date: str | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    rules_path: Path | None = None,
    drafts_path: Path | None = None,
    flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the deterministic input document for one remediation cycle.

    Reads only the G-dev (seed 44) mine and gate slices. Never makes a model
    call and never mutates the queue.
    """
    if world_seed != 44:
        raise OrchestratorError(f"remediation world_seed must be 44 (G-dev), got {world_seed}")
    runs = runs_dir or RUNS_DIR
    recipe = load_recipe()

    gdev_train, gdev_stats, gdev_gate_stats = _gdev_split(gdev_run_id, runs)

    live_rules = load_v0_rules(rules_path)
    live = [r for r in live_rules if r.status == "live"]

    opps = fn_opportunities(
        gdev_run_id, train_run_id, runs_dir=runs, models_dir=models_dir, rules_path=rules_path
    )

    loop_t_block = recipe.get("loop_t") or {}
    flagged = fp_inbox(gdev_train, rules=live, threshold=float(loop_t_block.get("fp_inbox_threshold", 0.005)))

    verify_candidates: list[dict[str, Any]] = []
    for opp in opps:
        mends = _maybe_mine_family(
            opp, train_run_id, gdev_run_id, runs, models_dir, rules_path,
            min_fn=int(loop_t_block.get("min_fn", 10)),
            min_genuine_gate=int(loop_t_block.get("min_genuine", 30)),
        )
        verify_candidates.extend(mends)
    for flag in flagged:
        if flag.get("kind") == "hard_flag":
            mends = _maybe_mine_calmdown(flag, gdev_run_id, runs, models_dir, rules_path)
            verify_candidates.extend(mends)

    enqueued = load_drafts(drafts_path)
    enqueued_drafts = [
        {
            "id": d.get("id", ""),
            "kind": d.get("kind", ""),
            "applies_to": d.get("applies_to", ""),
            "family": d.get("family", ""),
            "status": d.get("status", ""),
        }
        for d in enqueued
    ]
    prior_cycle_approved = sum(1 for d in enqueued if d.get("status") == "approved")

    by_kind: dict[str, int] = {}
    for rule in live:
        by_kind[rule.kind] = by_kind.get(rule.kind, 0) + 1

    cycle_date = date or datetime.now(UTC).date().isoformat()
    return {
        "gdev_run_id": gdev_run_id,
        "train_run_id": train_run_id,
        "world_seed": world_seed,
        "date": cycle_date,
        "recipe_hash": _recipe_hash(),
        "cycle_id": _cycle_id(gdev_run_id, train_run_id, cycle_date),
        "gdev_stats": gdev_stats,
        "gdev_gate_stats": gdev_gate_stats,
        "fn_opportunities": opps,
        "flagged_rules": flagged,
        "verify_candidates": verify_candidates,
        "live_rule_summary": {"total": len(live), "by_kind": by_kind},
        "enqueued_drafts": enqueued_drafts,
        "prior_cycle_approved": prior_cycle_approved,
    }


# ---------------------------------------------------------------------------
# §4 — deterministic post-processing of the LLM decision
# ---------------------------------------------------------------------------
def _normalize_decision(raw: Any, input_doc: dict[str, Any], capacity_hint: int) -> dict[str, Any] | None:
    """Validate + normalize the LLM decision. None means "fail closed"."""
    if not isinstance(raw, dict):
        return None

    candidates = {c["id"]: c for c in input_doc.get("verify_candidates", [])}
    known_families = set(FRAUD_FAMILIES)

    raw_verdict = raw.get("verdict")
    verdict = raw_verdict if isinstance(raw_verdict, str) and raw_verdict in _VERDICTS else "stop"
    reason = raw.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = "orchestrator_reject_unclassified"

    focus: list[str] = []
    for fam in raw.get("in_focus_families") or []:
        if isinstance(fam, str) and fam in known_families and fam not in focus:
            focus.append(fam)

    items: list[dict[str, Any]] = []
    raw_items = raw.get("items")
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            action = item.get("action")
            rule_id = item.get("rule_id")
            if action not in _ACTIONS or not isinstance(rule_id, str):
                continue
            cand = candidates.get(rule_id)
            if cand is None:
                continue  # invented rule id — drop (ORC.3)
            kind = item.get("kind")
            applies_to = item.get("applies_to")
            if cand.get("kind") != kind or cand.get("applies_to") != applies_to:
                continue
            item_reason = item.get("reason")
            if not isinstance(item_reason, str) or not item_reason.strip():
                item_reason = "orchestrator_reject_unclassified"
            items.append({
                "action": action,
                "rule_id": rule_id,
                "kind": cand.get("kind"),
                "applies_to": cand.get("applies_to"),
                "family": cand.get("family"),
                "when": list(cand.get("when") or []),
                "reason": item_reason,
            })

    items.sort(key=lambda it: (it["action"], it["rule_id"]))
    items = items[:_MAX_ITEMS]

    return {
        "verdict": verdict,
        "reason": reason,
        "items": items,
        "in_focus_families": focus,
        "reviewer_capacity_hint": int(capacity_hint),
        "error": raw.get("error"),
    }


def _system_prompt() -> str:
    return (
        "You are the Loop T remediation priority arbitrator for the Defend auth-fraud "
        "pipeline. One review pass. Decide: submit (queue for a human), press "
        "(auto-reject, still recorded so a human may override later), or hold "
        "(defer/stop, enqueue nothing). Never invent rule ids: you may only act on "
        "rule_id values present in the cycle input. Never fabricate when clauses "
        "or metrics. Prefer the smallest queue that fixes the largest caught-"
        "fraction; respect your reviewer capacity hint exactly. Deterministic, "
        "terse, no editorializing."
    )


def recommend_remediation_action(
    input_doc: dict[str, Any],
    provider: Any,
    *,
    flags: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """One LLM call reviewing the deterministic verify set. None on any failure."""
    flags = flags or load_remediation_flags()
    user = json.dumps(input_doc, default=str)
    try:
        raw = provider.complete_json(
            system=_system_prompt(),
            user=user,
            schema_name="RemediationDecision",
        )
    except Exception:  # noqa: BLE001 — fail-closed by design: any provider fault holds the queue
        return None

    decision = _normalize_decision(raw, input_doc, int(flags.get("reviewer_capacity_hint", 3)))
    if decision is None:
        return None
    decision["llm_meta"] = dict(getattr(provider, "last_meta", {}) or {})
    decision["raw_llm_response"] = raw
    return decision


# ---------------------------------------------------------------------------
# §5 — apply the decision (the only function that touches the queue + ledger)
# ---------------------------------------------------------------------------
def _draft_from_candidate(cand: dict[str, Any], cycle_id: str) -> dict[str, Any]:
    draft = dict(cand)
    draft["cycle_id"] = cycle_id
    draft["recommended_by"] = "orchestrator"
    draft["status"] = "proposed"
    draft.pop("source_rule_id", None)
    return draft


def apply_remediation_decision(
    input_doc: dict[str, Any],
    decision: dict[str, Any] | None,
    *,
    flags: dict[str, Any] | None = None,
    drafts_path: Path | None = None,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    """Apply one cycle's decision. Idempotent on the ledger; fail-closed everywhere."""
    flags = flags or load_remediation_flags()
    d_path = Path(drafts_path) if drafts_path else DEFAULT_DRAFTS_PATH
    cycle_id = input_doc.get("cycle_id") or _cycle_id(
        str(input_doc.get("gdev_run_id", "")), str(input_doc.get("train_run_id", "")), str(input_doc.get("date", ""))
    )
    ledger_path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH

    # Idempotency: identical (gdev_run_id, train_run_id, date) already applied.
    if any(e.get("cycle_id") == cycle_id for e in _load_ledger(ledger_path)):
        return {"status": "duplicate", "enqueued": 0, "auto_rejected": 0, "cycle_id": cycle_id}

    candidates = {c["id"]: c for c in input_doc.get("verify_candidates", [])}
    capacity_hint = int(flags.get("reviewer_capacity_hint", 3))

    enqueued: list[dict[str, Any]] = []
    pressed: list[dict[str, Any]] = []
    summary = {"status": "held", "verdict": "stop", "reason": "orchestrator_fail_closed"}

    if decision is not None and decision.get("verdict") == "submit":
        submit_items = [it for it in decision["items"] if it["action"] in {"fn", "calm_down"}]
        press_items = [it for it in decision["items"] if it["action"] == "press"]

        if len(submit_items) > capacity_hint:
            # Capacity breach → fail closed, queue untouched (ORC.6).
            enqueued = []
            pressed = []
            summary = {
                "status": "capacity_breach",
                "verdict": "submit",
                "reason": "orchestrator_capacity_breach",
            }
        else:
            for it in submit_items:
                cand = candidates[it["rule_id"]]
                draft = _draft_from_candidate(cand, cycle_id)
                draft["llm_support_reason"] = it["reason"]
                draft["action"] = it["action"]
                enqueued.append(draft)
            for it in press_items:
                cand = candidates[it["rule_id"]]
                draft = _draft_from_candidate(cand, cycle_id)
                draft["status"] = "auto_rejected"
                draft["auto_reject_reason"] = it["reason"]
                draft["rejected_by"] = "orchestrator"
                pressed.append(draft)
            summary = {"status": "applied", "verdict": "submit", "reason": decision.get("reason", "")}
    else:
        reason = "orchestrator_fail_closed (LLM unavailable)"
        if decision is not None:
            reason = decision.get("reason") or "orchestrator_reject_unclassified"
            summary = {
                "status": "applied",
                "verdict": decision.get("verdict", "stop"),
                "reason": reason,
            }

    if enqueued or pressed:
        existing = load_drafts(d_path)
        ids = {d["id"] for d in existing}
        drafts = list(existing)
        for d in enqueued + pressed:
            if d["id"] not in ids:
                drafts.append(d)
                ids.add(d["id"])
        save_drafts(drafts, d_path)

    entry = {
        "cycle_id": cycle_id,
        "ts": _now_iso(),
        "gdev_run_id": input_doc.get("gdev_run_id"),
        "train_run_id": input_doc.get("train_run_id"),
        "recipe_hash": input_doc.get("recipe_hash"),
        "date": input_doc.get("date"),
        "n_verify_candidates": len(candidates),
        "verdict": summary.get("verdict"),
        "outcome": summary.get("status"),
        "reason": summary.get("reason"),
        "candidate_enqueued": [d["id"] for d in enqueued],
        "candidate_pressed": [d["id"] for d in pressed],
        "capacity_hint": capacity_hint,
        "llm_meta": (decision or {}).get("llm_meta", {}),
        "raw_llm_response": (decision or {}).get("raw_llm_response"),
    }
    _append_ledger(entry, ledger_path)

    return {
        "status": summary.get("status"),
        "verdict": summary.get("verdict"),
        "enqueued": len(enqueued),
        "auto_rejected": len(pressed),
        "cycle_id": cycle_id,
        "ledger_entry": entry,
    }


# ---------------------------------------------------------------------------
# §6 — single entrypoint for make defend-remediate (kill switch aware)
# ---------------------------------------------------------------------------
def run_remediation_cycle(
    *,
    gdev_run_id: str,
    train_run_id: str,
    provider: Any,
    world_seed: int = 44,
    date: str | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    rules_path: Path | None = None,
    drafts_path: Path | None = None,
    ledger_path: Path | None = None,
    flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Hat the whole cycle: build → recommend → apply. Kill-switch aware."""
    flags = flags or load_remediation_flags()
    if not flags.get("orchestrator_enabled"):
        raise OrchestratorDisabledError("remediation orchestrator disabled")

    cycle_id = _cycle_id(
        gdev_run_id, train_run_id, date or datetime.now(UTC).date().isoformat()
    )
    with _IN_FLIGHT_LOCK:
        if cycle_id in _IN_FLIGHT_CYCLES:
            raise OrchestratorError(f"remediation cycle already in flight: {cycle_id}")
        _IN_FLIGHT_CYCLES.add(cycle_id)
    try:
        input_doc = build_remediation_cycle_input(
            gdev_run_id,
            train_run_id,
            world_seed=world_seed,
            date=date,
            runs_dir=runs_dir,
            models_dir=models_dir,
            rules_path=rules_path,
            drafts_path=drafts_path,
            flags=flags,
        )
        decision = recommend_remediation_action(input_doc, provider, flags=flags)
        return apply_remediation_decision(
            input_doc,
            decision,
            flags=flags,
            drafts_path=drafts_path,
            ledger_path=ledger_path,
        )
    finally:
        with _IN_FLIGHT_LOCK:
            _IN_FLIGHT_CYCLES.discard(cycle_id)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()