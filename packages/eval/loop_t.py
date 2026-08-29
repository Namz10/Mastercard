"""Loop T — decision-tree FN mining, backtest gate, HITL candidates (Phase 5 / Ticket 7)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

from packages.eval.fit import (
    _encode,
    _fraud_score,
    _proba_map,
    _recipe_hash,
    load_champion,
    load_recipe,
    run_paths,
)
from packages.policy.rule_hitl import DEFAULT_DRAFTS_PATH, load_drafts, save_drafts
from packages.policy.rules import (
    ALLOWED_RULE_FIELDS,
    EXTRA_ROW_FIELDS,
    Rule,
    evaluate_rules,
    flatten_row,
    load_v0_rules,
    parse_predicate,
    predicate_holds,
    rule_fires,
)
from packages.sim.ablation import APP_FLAG_COLS
from packages.sim.export import RUNS_DIR
from packages.sim.ledger import LABEL_FAMILIES

FRAUD_FAMILIES = LABEL_FAMILIES - {"normal"}

FAMILY_TO_APPLIES_TO: dict[str, str] = {
    "mule": "mule",
    "app_fraud": "APP",
    "invoice_fraud": "BEC",
    "ato": "ATO",
    "identity_burst": "ATO",
}

# Locked tree features: numeric/bool in allowlist minus APP flags, minus invoice stamps, minus rail/kyc_tier
TREE_FEATURE_ALLOWLIST = tuple(
    sorted(
        ALLOWED_RULE_FIELDS
        - set(APP_FLAG_COLS)
        - set(EXTRA_ROW_FIELDS)
        - {"rail", "kyc_tier", "label_family"}
    )
)

_IN_FLIGHT_MINES: set[tuple[str, str, str]] = set()

# applies_to -> the canonical fraud family the rule's applies_to targets (reverse map).
APPLIES_TO_FAMILY: dict[str, str] = {
    "APP": "app_fraud",
    "BEC": "invoice_fraud",
    "ATO": "ato",
    "mule": "mule",
}


def _cd_config(recipe: dict[str, Any]) -> dict[str, Any]:
    """Calm-down (FP) mining bounds. Not a new metric — thresholds only."""
    block = (recipe.get("loop_t") or {})
    return {
        "max_depth": int(block.get("max_depth", 3)),
        "min_samples_leaf": int(block.get("min_samples_leaf", 10)),
        "min_leaf_precision": float(block.get("min_leaf_precision", 0.70)),
        "max_candidates": int(block.get("max_candidates", 5)),
        "max_predicates": int(block.get("max_predicates", 4)),
        "jaccard_duplicate": float(block.get("jaccard_duplicate", 0.80)),
        "cd_min_genuine_coverage": float(block.get("cd_min_genuine_coverage", 0.70)),
        "cd_max_over_calm": float(block.get("cd_max_over_calm", 0.05)),
        "cd_rule_augment_fpr_eps": float(block.get("cd_rule_augment_fpr_eps", 0.002)),
        "max_cd_rules": int(block.get("max_cd_rules", 3)),
    }


def mine_fp_calmdown_candidates(
    gdev_run_id: str,
    rule_id: str,
    *,
    train_run_id: str | None = None,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    rules_path: Path | None = None,
) -> dict[str, Any]:
    """FP calm-down mining (Phase 8 / Orchestrator prerequisite §2).

    Fits a decision tree on *genuine-fire rows* for ONE already-live rule flagged
    by :func:`fp_inbox`, learning the predicate clause that isolates genuine rows
    the live rule currently fires on. The candidate is a ``calm_down``-kind draft
    whose ``when`` is that extra clause — when a human approves it, a genuinely-
    flagged row that also satisfies the clause stops triggering a hard action.

    Same tree grammar / gates as :func:`mine_fn_rules` (parse_predicate validity,
    forbidden-field exclusion, Jaccard novelty, 30% G-dev gate backtest), mirrored
    for the calm-down direction. Never writes to drafts.json — this phase's
    orchestrator decides what a human sees, so candidates are returned, not queued.
    """
    if "43" in str(gdev_run_id) or "gtest" in str(gdev_run_id).lower():
        raise ValueError(f"Loop T FP calm-down mining must run on G-dev seed 44, never seed 43 / gtest ({gdev_run_id})")

    cfg = _cd_config(load_recipe())
    runs = runs_dir or RUNS_DIR
    gdev_paths = run_paths(gdev_run_id, runs)
    gdev_train = pd.read_parquet(gdev_paths["train"])
    gdev_split = pd.read_parquet(gdev_paths["split"])

    live_rules = load_v0_rules(rules_path)
    target = next((r for r in live_rules if r.status == "live" and r.id == rule_id), None)
    if target is None:
        raise KeyError(f"rule_id not live in v0_rules: {rule_id}")

    records = gdev_train.to_dict(orient="records")
    fire_mask = np.array([rule_fires(target, rec) for rec in records], dtype=bool)
    if not fire_mask.any():
        return {"status": "skipped", "reason": "no_fire", "rule_id": rule_id, "candidates": []}

    is_genuine = gdev_train["label_family"].astype(str).to_numpy() == "normal"
    gen_fire = fire_mask & is_genuine
    # True fires = rows of the rule's target family that the rule fires on.
    target_family = APPLIES_TO_FAMILY.get(target.applies_to, target.applies_to)
    true_fire = fire_mask & ~is_genuine
    if target_family not in FRAUD_FAMILIES:
        return {"status": "skipped", "reason": "no_target_family", "rule_id": rule_id, "candidates": []}

    n_gen_fire = int(gen_fire.sum())
    n_true_fire = int(true_fire.sum())
    if n_gen_fire < int(load_recipe().get("loop_t", {}).get("min_genuine", 30)):
        return {"status": "skipped", "reason": "insufficient_genuine_fire", "rule_id": rule_id,
                "n_genuine_fire": n_gen_fire, "candidates": []}
    if n_true_fire < int(load_recipe().get("loop_t", {}).get("min_fn", 10)):
        return {"status": "skipped", "reason": "insufficient_true_fire", "rule_id": rule_id,
                "n_true_fire": n_true_fire, "candidates": []}

    # Calendar 70/30 cut on G-dev (identical to mine_fn_rules).
    ts = pd.to_datetime(gdev_split["event_ts"], utc=True, format="ISO8601")
    t0, t1 = ts.min(), ts.max()
    cut = t0 + (t1 - t0) * 0.70
    mine_mask = (ts < cut).to_numpy()
    gate_mask = (ts >= cut).to_numpy()
    mine_ids = set(gdev_split.loc[mine_mask, "event_id"].astype(str))
    gate_ids = set(gdev_split.loc[gate_mask, "event_id"].astype(str))
    assert mine_ids.isdisjoint(gate_ids), "G-dev mine and gate event IDs must be disjoint"

    tree_cols = [c for c in TREE_FEATURE_ALLOWLIST if c in gdev_train.columns]
    assert set(tree_cols).isdisjoint(set(APP_FLAG_COLS) | set(EXTRA_ROW_FIELDS)), "Stamp columns must not be in tree feature list"

    # Build a tree distinguishing genuine-fire rows (y=1) from true-fire rows (y=0).
    pos_idx = np.where(gen_fire & mine_mask)[0]
    neg_idx = np.where(true_fire & mine_mask)[0]
    if len(pos_idx) == 0 or len(neg_idx) == 0:
        return {"status": "skipped", "reason": "insufficient_mine_split", "rule_id": rule_id, "candidates": []}

    if len(neg_idx) > 3 * len(pos_idx):
        rng = np.random.default_rng(42)
        neg_idx = rng.choice(neg_idx, size=3 * len(pos_idx), replace=False)
        neg_idx.sort()

    mine_indices = np.concatenate([pos_idx, neg_idx])
    X_mine = gdev_train.iloc[mine_indices][tree_cols].copy()
    for c in X_mine.columns:
        if X_mine[c].dtype == bool:
            X_mine[c] = X_mine[c].astype(int)
        else:
            X_mine[c] = pd.to_numeric(X_mine[c], errors="coerce").fillna(0)

    y_mine = np.zeros(len(mine_indices), dtype=int)
    y_mine[: len(pos_idx)] = 1

    dt = DecisionTreeClassifier(
        max_depth=int(cfg["max_depth"]),
        min_samples_leaf=int(cfg["min_samples_leaf"]),
        random_state=42,
    )
    dt.fit(X_mine.to_numpy(), y_mine)

    # Extract leaves predicting the genuine-fire class (y=1) with decent precision.
    tree_ = dt.tree_
    feature_names = list(tree_cols)
    raw_clauses: list[tuple[tuple[str, ...], float, int]] = []

    def _recurse(node: int, current_path: list[str]):
        if tree_.feature[node] != -2:
            feat = feature_names[tree_.feature[node]]
            thresh = float(tree_.threshold[node])
            is_bool = gdev_train[feat].dtype == bool
            if is_bool:
                _recurse(tree_.children_left[node], current_path + [f"{feat} == false"])
                _recurse(tree_.children_right[node], current_path + [f"{feat} == true"])
            else:
                _recurse(tree_.children_left[node], current_path + [f"{feat} <= {thresh:.4g}"])
                _recurse(tree_.children_right[node], current_path + [f"{feat} >= {thresh:.4g}"])
        else:
            values = tree_.value[node][0]
            n_samples = int(values.sum())
            if n_samples >= int(cfg["min_samples_leaf"]):
                genuine_count = float(values[1])
                precision = genuine_count / n_samples
                if precision >= float(cfg["min_leaf_precision"]) and len(current_path) <= int(cfg["max_predicates"]):
                    raw_clauses.append((tuple(current_path), precision, n_samples))

    _recurse(0, [])

    if not raw_clauses:
        return {"status": "success", "rule_id": rule_id, "target_family": target_family,
                "genuine_fire_before": n_gen_fire, "candidates": []}

    gate_gen_recs = gdev_train.loc[gate_mask & is_genuine].to_dict(orient="records")
    gate_true_recs = gdev_train.loc[gate_mask & true_fire].to_dict(orient="records")
    n_gate_gen_fire = int((gate_mask & gen_fire).sum())
    n_gate_true_fire = int((gate_mask & true_fire).sum())

    live_calm_downs = [r for r in live_rules if r.status == "live" and r.kind == "calm_down"]
    r_hash = _recipe_hash()
    survived: list[dict[str, Any]] = []
    fam = target_family

    for clause, precision, n_samples in raw_clauses:
        valid = True
        cand_preds = []
        for expr in clause:
            try:
                cand_preds.append(parse_predicate(expr))
            except ValueError:
                valid = False
                break
        if not valid:
            continue

        # Novelty vs existing calm_down rules (Jaccard on the clause predicates).
        dup_id: str | None = None
        jac_max = 0.0
        for cr in live_calm_downs:
            j = _jaccard_similarity(clause, cr)
            jac_max = max(jac_max, j)
            if j > float(cfg["jaccard_duplicate"]):
                dup_id = cr.id
                break
        if dup_id:
            continue

        # Gate backtest (calm-down direction): coverage of genuine fires (good) and
        # over-calm on true fires (bad) on the 30% G-dev gate slice.
        clause_preds = tuple(cand_preds)
        if n_gate_gen_fire > 0:
            gen_covered = sum(
                1 for rec in gate_gen_recs
                if all(predicate_holds(p, flatten_row(rec)) for p in clause_preds)
            )
            calm_coverage = gen_covered / n_gate_gen_fire
        else:
            calm_coverage = 0.0
        if n_gate_true_fire > 0:
            true_covered = sum(
                1 for rec in gate_true_recs
                if all(predicate_holds(p, flatten_row(rec)) for p in clause_preds)
            )
            over_calm = true_covered / n_gate_true_fire
        else:
            over_calm = 0.0

        if calm_coverage < float(cfg["cd_min_genuine_coverage"]):
            continue
        if over_calm > float(cfg["cd_max_over_calm"]):
            continue

        when_exprs = list(clause)
        draft_id = f"loop-t-cd-{rule_id}-{hashlib.sha256(' AND '.join(when_exprs).encode()).hexdigest()[:8]}"
        candidate_obj = {
            "id": draft_id,
            "kind": "calm_down",
            "applies_to": "genuine",
            "family": fam,
            "when": when_exprs,
            "reason": f"calm-down extra AND for live rule {rule_id}: " + " AND ".join(when_exprs),
            "status": "proposed",
            "recipe_hash": r_hash,
            "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "source_rule_id": rule_id,
            "metrics": {
                "gate_genuine_fpr": over_calm,
                "gate_incremental_recall": calm_coverage,
                "gate_genuine_fire_n": n_gate_gen_fire,
                "gate_true_fire_n": n_gate_true_fire,
                "cd_calm_coverage": calm_coverage,
                "cd_over_calm": over_calm,
            },
            "leaf_precision": precision,
            "leaf_support": n_samples,
            "path_length": len(when_exprs),
            "jaccard_max_vs_live": jac_max,
            "duplicate_of_live_rule": dup_id,
            "forbidden_field_hit": False,
        }
        survived.append(candidate_obj)
        if len(survived) >= int(cfg["max_candidates"]):
            break

    return {
        "status": "success",
        "rule_id": rule_id,
        "target_family": target_family,
        "gdev_run_id": gdev_run_id,
        "genuine_fire_before": n_gen_fire,
        "candidates": survived,
    }


def fp_inbox(
    gdev_df: pd.DataFrame,
    rules: list[Rule] | None = None,
    threshold: float = 0.005,
) -> list[dict[str, Any]]:
    """Listed rules whose FPR on genuine rows exceeds threshold (default 0.005)."""
    live = rules if rules is not None else load_v0_rules()
    live = [r for r in live if r.status == "live"]
    mask = gdev_df["label_family"].astype(str) == "normal"
    genuine_df = gdev_df.loc[mask].reset_index(drop=True)
    if genuine_df.empty:
        return []
    records = genuine_df.to_dict(orient="records")
    n = len(records)
    flagged: list[dict[str, Any]] = []
    for r in live:
        hits = sum(1 for rec in records if rule_fires(r, rec))
        fpr = float(hits / n)
        if fpr > threshold:
            flagged.append({
                "id": r.id,
                "kind": r.kind,
                "applies_to": r.applies_to,
                "genuine_fpr": fpr,
                "threshold": threshold,
                "hits": hits,
                "total_genuine": n,
            })
    return flagged


def fn_opportunities(
    gdev_run_id: str,
    train_run_id: str,
    *,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    rules_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Per-family FN opportunity profile on G-dev (mirrors mine_fn_rules scoring).

    The Phase 8 orchestrator calls this once to size its verify set; it must not
    open a seed-43 / gtest world, exactly like :func:`mine_fn_rules`.
    """
    if "43" in str(gdev_run_id) or "gtest" in str(gdev_run_id).lower():
        raise ValueError(f"Loop T fn opportunities must run on G-dev seed 44, never seed 43 / gtest ({gdev_run_id})")

    runs = runs_dir or RUNS_DIR
    gdev_paths = run_paths(gdev_run_id, runs)
    gdev_train = pd.read_parquet(gdev_paths["train"])
    gdev_split = pd.read_parquet(gdev_paths["split"])

    live_rules = load_v0_rules(rules_path)
    live_hard_flags = [r for r in live_rules if r.status == "live" and r.kind == "hard_flag"]

    champ = load_champion(train_run_id, models_dir=models_dir)
    x_gdev_raw = gdev_train.drop(columns=["label_family"], errors="ignore")
    x_gdev_raw = x_gdev_raw.reindex(columns=champ.raw_columns, fill_value=0)
    x_gdev, _ = _encode(x_gdev_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x_gdev)
    scores = _fraud_score(pmap, len(gdev_train))
    op_thr = champ.op_threshold

    records = gdev_train.to_dict(orient="records")
    hard_flag_hits = np.zeros(len(gdev_train), dtype=bool)
    for i, rec in enumerate(records):
        eval_res = evaluate_rules(rec, live_hard_flags)
        if eval_res.hits:
            hard_flag_hits[i] = True

    caught = (scores >= op_thr) | hard_flag_hits
    y_gold = gdev_train["label_family"].astype(str).to_numpy()
    gen_mask = y_gold == "normal"

    ts = pd.to_datetime(gdev_split["event_ts"], utc=True, format="ISO8601")
    cut = ts.min() + (ts.max() - ts.min()) * 0.70
    gate_mask = (ts >= cut).to_numpy()

    out: list[dict[str, Any]] = []
    for fam in sorted(FRAUD_FAMILIES):
        fn_mask = y_gold == fam
        out.append({
            "family": fam,
            "applies_to": FAMILY_TO_APPLIES_TO.get(fam, fam),
            "n_fn": int((fn_mask & ~caught).sum()),
            "n_genuine": int(gen_mask.sum()),
            "n_genuine_gate": int((gen_mask & gate_mask).sum()),
        })
    return out


def _jaccard_similarity(cand_preds: tuple[str, ...], live_rule: Rule) -> float:
    cand_pairs = set()
    for p_str in cand_preds:
        try:
            p = parse_predicate(p_str)
            cand_pairs.add((p.field, p.op))
        except ValueError:
            pass

    live_pairs = {(p.field, p.op) for p in live_rule.predicates}
    if not cand_pairs or not live_pairs:
        return 0.0
    union = cand_pairs | live_pairs
    inter = cand_pairs & live_pairs
    return len(inter) / len(union)


def mine_fn_rules(
    train_run_id: str,
    gdev_run_id: str,
    family: str,
    *,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    drafts_path: Path | None = None,
    rules_path: Path | None = None,
    llm_packager: Any | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    fam = str(family)
    if fam not in FRAUD_FAMILIES:
        raise ValueError(f"family must be a fraud label_family, got {fam}")

    # Stop-gate: never open seed-43 / gtest
    if "43" in str(gdev_run_id) or "gtest" in str(gdev_run_id).lower():
        raise ValueError(f"Loop T mining must run on G-dev seed 44, never seed 43 / gtest ({gdev_run_id})")

    key = (train_run_id, gdev_run_id, fam)
    if key in _IN_FLIGHT_MINES:
        raise RuntimeError(f"mine already in flight for {key}")

    _IN_FLIGHT_MINES.add(key)
    try:
        return _mine_fn_rules_impl(
            train_run_id=train_run_id,
            gdev_run_id=gdev_run_id,
            family=fam,
            runs_dir=runs_dir,
            models_dir=models_dir,
            drafts_path=drafts_path,
            rules_path=rules_path,
            llm_packager=llm_packager,
            persist=persist,
        )
    finally:
        _IN_FLIGHT_MINES.discard(key)


def _mine_fn_rules_impl(
    train_run_id: str,
    gdev_run_id: str,
    family: str,
    *,
    runs_dir: Path | None = None,
    models_dir: Path | None = None,
    drafts_path: Path | None = None,
    rules_path: Path | None = None,
    llm_packager: Any | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    runs = runs_dir or RUNS_DIR
    gdev_paths = run_paths(gdev_run_id, runs)
    gdev_train = pd.read_parquet(gdev_paths["train"])
    gdev_split = pd.read_parquet(gdev_paths["split"])

    live_rules = load_v0_rules(rules_path)
    live_hard_flags = [r for r in live_rules if r.status == "live" and r.kind == "hard_flag"]

    # Score G-dev with champion trained on train_run_id (do NOT fit on G-dev)
    champ = load_champion(train_run_id, models_dir=models_dir)
    x_gdev_raw = gdev_train.drop(columns=["label_family"], errors="ignore")
    x_gdev_raw = x_gdev_raw.reindex(columns=champ.raw_columns, fill_value=0)
    x_gdev, _ = _encode(x_gdev_raw, encoder=champ.encoder, cat_cols=champ.cat_cols, fit=False)
    pmap = _proba_map(champ.model, x_gdev)
    scores = _fraud_score(pmap, len(gdev_train))
    op_thr = champ.op_threshold

    # Determine caught status per G-dev row
    records = gdev_train.to_dict(orient="records")
    hard_flag_hits = np.zeros(len(gdev_train), dtype=bool)
    for i, rec in enumerate(records):
        eval_res = evaluate_rules(rec, live_hard_flags)
        if eval_res.hits:
            hard_flag_hits[i] = True

    caught = (scores >= op_thr) | hard_flag_hits
    y_gold = gdev_train["label_family"].astype(str).to_numpy()

    fn_mask = (y_gold == family) & (~caught)
    gen_mask = y_gold == "normal"

    n_fn = int(fn_mask.sum())
    n_gen = int(gen_mask.sum())

    if n_fn < 10 or n_gen < 30:
        return {
            "status": "skipped",
            "reason": "insufficient_fn",
            "n_fn": n_fn,
            "n_genuine": n_gen,
            "candidates": [],
        }

    # Calendar 70/30 cut on G-dev
    ts = pd.to_datetime(gdev_split["event_ts"], utc=True, format="ISO8601")
    t0, t1 = ts.min(), ts.max()
    cut = t0 + (t1 - t0) * 0.70

    mine_mask = (ts < cut).to_numpy()
    gate_mask = (ts >= cut).to_numpy()

    mine_ids = set(gdev_split.loc[mine_mask, "event_id"].astype(str))
    gate_ids = set(gdev_split.loc[gate_mask, "event_id"].astype(str))
    assert mine_ids.isdisjoint(gate_ids), "G-dev mine and gate event IDs must be disjoint"

    n_gen_gate = int((gen_mask & gate_mask).sum())
    if n_gen_gate < 30:
        return {
            "status": "skipped",
            "reason": "insufficient_gate",
            "n_genuine_gate": n_gen_gate,
            "candidates": [],
        }

    # Prepare tree features
    tree_cols = [c for c in TREE_FEATURE_ALLOWLIST if c in gdev_train.columns]
    assert set(tree_cols).isdisjoint(set(APP_FLAG_COLS) | set(EXTRA_ROW_FIELDS)), "Stamp columns must not be in tree feature list"

    # Prepare mining sample (70% mine slice)
    fn_mine_idx = np.where(fn_mask & mine_mask)[0]
    gen_mine_idx = np.where(gen_mask & mine_mask)[0]

    if len(fn_mine_idx) == 0:
        return {"status": "skipped", "reason": "insufficient_fn", "n_fn": 0, "candidates": []}

    # Subsample genuines if > 3x FN
    if len(gen_mine_idx) > 3 * len(fn_mine_idx):
        rng = np.random.default_rng(42)
        gen_mine_idx = rng.choice(gen_mine_idx, size=3 * len(fn_mine_idx), replace=False)
        gen_mine_idx.sort()

    mine_indices = np.concatenate([fn_mine_idx, gen_mine_idx])
    X_mine = gdev_train.iloc[mine_indices][tree_cols].copy()
    for c in X_mine.columns:
        if X_mine[c].dtype == bool:
            X_mine[c] = X_mine[c].astype(int)
        else:
            X_mine[c] = pd.to_numeric(X_mine[c], errors="coerce").fillna(0)

    y_mine = np.zeros(len(mine_indices), dtype=int)
    y_mine[: len(fn_mine_idx)] = 1

    dt = DecisionTreeClassifier(max_depth=3, min_samples_leaf=10, random_state=42)
    dt.fit(X_mine.to_numpy(), y_mine)

    # Extract rules from leaf nodes predicting class 1
    tree_ = dt.tree_
    feature_names = list(tree_cols)
    raw_candidates: list[dict[str, Any]] = []

    def _recurse(node: int, current_path: list[str]):
        if tree_.feature[node] != -2:  # internal node
            feat = feature_names[tree_.feature[node]]
            thresh = float(tree_.threshold[node])
            is_bool = gdev_train[feat].dtype == bool
            if is_bool:
                _recurse(tree_.children_left[node], current_path + [f"{feat} == false"])
                _recurse(tree_.children_right[node], current_path + [f"{feat} == true"])
            else:
                _recurse(tree_.children_left[node], current_path + [f"{feat} <= {thresh:.4g}"])
                _recurse(tree_.children_right[node], current_path + [f"{feat} >= {thresh:.4g}"])
        else:  # leaf node
            values = tree_.value[node][0]
            n_samples = int(values.sum())
            if n_samples >= 10:
                fn_count = float(values[1])
                precision = fn_count / n_samples
                if precision >= 0.70 and len(current_path) <= 4:
                    raw_candidates.append({
                        "when": tuple(current_path),
                        "leaf_precision": precision,
                        "leaf_support": n_samples,
                    })

    _recurse(0, [])

    applies_to = FAMILY_TO_APPLIES_TO.get(family, family)
    live_rules_for_applies = [r for r in live_rules if r.status == "live" and r.applies_to == applies_to]

    # Filter candidates by validity, novelty (Jaccard), and backtest on 30% gate
    gate_gen_recs = gdev_train.loc[gen_mask & gate_mask].to_dict(orient="records")
    gate_fn_mask = fn_mask & gate_mask
    gate_fn_recs = gdev_train.loc[gate_fn_mask].to_dict(orient="records")
    n_gate_fn = len(gate_fn_recs)

    survived_candidates: list[dict[str, Any]] = []
    r_hash = _recipe_hash()

    for raw_cand in raw_candidates:
        cand_when = raw_cand["when"]
        # 1. Parse validation
        valid = True
        cand_preds = []
        for clause in cand_when:
            try:
                p = parse_predicate(clause)
                cand_preds.append(p)
            except ValueError:
                valid = False
                break
        if not valid:
            continue

        # 2. Novelty check vs live rules
        is_dup = False
        dup_of: str | None = None
        jac_max = 0.0
        for live_r in live_rules_for_applies:
            j = _jaccard_similarity(cand_when, live_r)
            jac_max = max(jac_max, j)
            if j > 0.80:
                is_dup = True
                dup_of = live_r.id
                break
        if is_dup:
            continue

        # 3. Backtest Genuine FPR on gate slice
        gate_gen_hits = sum(1 for rec in gate_gen_recs if all(rule_fires(Rule("tmp", "hard_flag", applies_to, cand_when, tuple(cand_preds)), rec) for _ in [0]))
        cand_fpr = gate_gen_hits / max(1, len(gate_gen_recs))
        if cand_fpr > 0.002:  # rule_promote_genuine_fpr_eps
            continue

        # 4. Backtest Incremental Recall on gate slice
        cand_rule = Rule("tmp", "hard_flag", applies_to, cand_when, tuple(cand_preds))
        recalled_by_hard = 0
        recalled_by_union = 0
        for rec in gate_fn_recs:
            hard_hit = bool(evaluate_rules(rec, live_hard_flags).hits)
            cand_hit = rule_fires(cand_rule, rec)
            if hard_hit:
                recalled_by_hard += 1
            if hard_hit or cand_hit:
                recalled_by_union += 1

        incremental_recall = (recalled_by_union - recalled_by_hard) / max(1, n_gate_fn)
        if incremental_recall <= 0:
            continue

        draft_id = f"loop-t-{family}-{hashlib.sha256(' AND '.join(cand_when).encode()).hexdigest()[:8]}"
        default_reason = " AND ".join(cand_when)

        candidate_obj = {
            "id": draft_id,
            "kind": "hard_flag",
            "applies_to": applies_to,
            "family": family,
            "when": list(cand_when),
            "reason": default_reason,
            "status": "proposed",
            "recipe_hash": r_hash,
            "created_at": pd.Timestamp.now(tz="UTC").isoformat(),
            "metrics": {
                "gate_genuine_fpr": cand_fpr,
                "gate_incremental_recall": float(incremental_recall),
            },
            "leaf_precision": raw_cand["leaf_precision"],
            "leaf_support": raw_cand["leaf_support"],
            "path_length": len(cand_when),
            "jaccard_max_vs_live": jac_max,
            "duplicate_of_live_rule": dup_of,
            "forbidden_field_hit": False,
        }

        # Optional LLM packaging (must NOT mutate when)
        if llm_packager is not None:
            try:
                llm_out = llm_packager({"when_clauses": list(cand_when), "applies_to": applies_to, "family": family})
                if isinstance(llm_out, dict):
                    if "id" in llm_out and isinstance(llm_out["id"], str):
                        candidate_obj["id"] = llm_out["id"]
                    if "reason" in llm_out and isinstance(llm_out["reason"], str):
                        candidate_obj["reason"] = llm_out["reason"]
            except Exception:
                pass

        # Locked assertion: when clause must ALWAYS equal the tree's predicate list
        assert candidate_obj["when"] == list(cand_when), "LLM cannot mutate when clause"
        survived_candidates.append(candidate_obj)

        if len(survived_candidates) >= 5:
            break

    # Persist proposed drafts to drafts.json (skipped when persist=False — the
    # Phase 8 orchestrator collects candidates and decides the queue itself).
    if persist:
        d_path = drafts_path or DEFAULT_DRAFTS_PATH
        existing_drafts = load_drafts(d_path)
        existing_ids = {d["id"] for d in existing_drafts}
        for c in survived_candidates:
            if c["id"] not in existing_ids:
                existing_drafts.append(c)

        save_drafts(existing_drafts, d_path)

    return {
        "status": "success",
        "train_run_id": train_run_id,
        "gdev_run_id": gdev_run_id,
        "family": family,
        "candidates": survived_candidates,
    }
