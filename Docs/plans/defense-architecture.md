# AegisLoop — Defend Architecture SSOT

**System:** AegisLoop — Mastercard GFF 2026 Closed-Loop Red/Blue Lab  
**Challenge:** Mastercard Innovation Challenge @ GFF 2026  
**Author:** ML Expert review (Sonnet), 2026-08-28  
**Status:** FINAL. This document supersedes all claims in `Docs/defense_architecture.md` (AutoGluon, five live models, nine working loops). That file is archived and its claims are not reproducible from current code.  
**Repo root:** `/home/aarush_linux/projects/Mastercard`

---

## 1. Purpose and SSOT hierarchy

This document is the single source of truth for Defend architecture decisions, locked rulings, and the new proposals evaluated below.

**What it supersedes:**

- `Docs/defense_architecture.md` — claimed AutoGluon/FLAML/LightGBM on the live path, an LLM case extractor scoring live payments, ~12–18 rules, "all loops". None of that is in the codebase. Do not copy from it.
- `Docs/feedback-loop.md` — nine named loops (I, R, T, M, A, F, C, H, G). Only I, C (read), M are coded. The rest are named as roadmap.
- `Docs/ARCHITECTURE.md` — LoopGovernor, Canary Vault live, LangGraph defend story. None is in `defend.py` or `loop_m.py`.
- `Docs/plans/02-generate-defend-loop-lock.md` — architecture names only; not Defend SSOT.

**Read in this order:**

1. `Docs/plans/README-defend.md` — index.
2. `Docs/plans/defend-execution-ssot.md` — how to code (§13 wins).
3. This file — architecture meaning (not ticket order).
4. `Docs/plans/defend-test-tracker.md` — RED tests.
5. `Docs/plans/defend-dev-keepinminds.md` — PR do-nots.
6. `VALIDATION.md` — G1–G7.
7. `Docs/plans/defend-peak-handoff.md` — disk inventory only; tickets 7–8 stale.

**Locked one-liners (do not reopen):**

| Locked item | Exact meaning |
|---|---|
| AuthGate | ONE `HistGradientBoostingClassifier`, `y = label_family`, multiclass. Family AP is a **metric**, not five heads. |
| Specialists | **Zero this sprint.** Do not add OVR adapters. |
| Loop G | **Do not build.** Not a ticket. |
| AutoML | Optuna nested on train-only. AutoGluon = overnight write-up challenger only; never on demo path. |
| Loop M | The clickable closed loop. Miss → Generate extra → retrain → new-seed G-test. |
| Rules | 9 YAML rules stay `status: live`. Drafts from Loop I and **Loop T (MUST)**. HITL promote. No auto-on. |
| Forbidden live | AutoResearch, GNN live, Featuretools/DFS on events, CaseScore LLM on auth, auto-`solved`. |
| G-test | seed 43 — used once per reported number. seed 44 = G-dev for harvest/decisions. seed 45 = confirmation if 43 peeked. |

---

## 2. Honest system map (24 → 4 → 1 taper)

```
Identify (LangGraph, 24 TechniqueId, HITL)
    Scout → Curator → Extractor → Grounder → TierScorer → Corroborator → Librarian
    → proposed rows → HITL approve/reject/edit → open
         │
         │  default Generate does NOT consume Atlas recipes
         │  vector_id set → one family + simulatable_signals into one mix key
         ▼
Generate (ShadowRail, 4 injectors, 5 fraud families)
    quiet Poisson world → apply_mix (DEFAULT_SIGNALS unless vector_id)
    → causal FeatureComputer O(n) → PSI/fidelity gate
    → train.parquet + split.parquet + sidecar.json
         │
         ▼
Defend (no LangGraph)
    9 YAML rules [step 1]
    → 1 multiclass HGB (rule__ bits on X) [step 2]
    → [Isolation Forest notify, if GO] [step 3, conditional]
    → Brake: policy_action enum [step 4]
    Loop I drafts rules (API coded)
    Loop C reads coverage map (API coded)
    Loop M miss → Generate extra → refit → new-seed G-test (API coded)
    Loop T (MUST): G-dev FN trees → gates → HITL queue → versioned YAML (not coded yet)
```

**24 → 4 → 1 taper (honest):**

| Layer | Count | Reality |
|---|---|---|
| Taxonomy (Identify) | 24 `TechniqueId` | Coverage cells, not 24 detectors |
| Seed rows | 29 | Duplicates on T13/T02/T11/T24 |
| `generate_mode = name_only` | T06, T07, one T19, T20–T23, high dual-use | Cannot be simulated at payment time |
| Injector engines | **4** | `graph_mule`, `identity_trajectory`, `app_session`, `doc_beneficiary` |
| `label_family` | **6** incl. normal | `normal \| mule \| identity_burst \| ato \| app_fraud \| invoice_fraud` |
| Live YAML rules | **9** | `data/rules/v0_rules.yaml`; `coverage_status=live_rule` is feature-name overlap, not fire-rate |
| Champion | **1** multiclass HGB | `ap_by_family` is OVR AP from one head, not five pickled models |

**Family ← injector mapping** (from `runner.py`): `graph_mule → mule`; `app_session → app_fraud`; `doc_beneficiary → invoice_fraud`; `identity_trajectory` + T12 → `ato`; else → `identity_burst`. T08/T09/T10 generate cards collapse to `identity_burst` — not a KYC detector.

---

## 3. ASCII architecture diagram

```
Payment event at auth time
         │
         ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  G(t−) feature snapshot (O(n) deques, past edges only)     │
 │  fan_in_1h, fan_out_1h, account_age_days, payee_history,   │
 │  is_new_payee, is_new_device, amount_vs_p30, rail,          │
 │  kyc_tier, burst_velocity [→ redefine Ticket 1]            │
 │  + invoice booleans [beneficiary_changed, gstin_checksum_ok,│
 │    lookalike_domain_flag] from ev["payload"] [Ticket 1]     │
 │  + APP session flags [call_active_flag, copy_paste_payee,   │
 │    pause_ms, urgency_pressure] only on app_fraud rows       │
 └──────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
 ┌──────────────────────────────────────────────────────────┐
 │  STEP 1: 9 YAML rules (v0_rules.yaml)                   │
 │  Row predicates → hits: {hard_flag, nudge, calm_down}   │
 │  rule__<id> bits appended to X for champion             │
 └──────────────────────┬───────────────────────────────────┘
                        │ rule bits + features
                        ▼
 ┌──────────────────────────────────────────────────────────┐
 │  STEP 2: Champion HGB multiclass                        │
 │  HistGradientBoostingClassifier (y=label_family)        │
 │  predict_proba → pmap[family]                           │
 │  fraud_score = 1 - pmap["normal"]                       │
 │  pred_family = argmax over classes                      │
 └──────────────────────┬───────────────────────────────────┘
                        │ pred_family, score, rule hits
                        ▼
 ┌──────────────────────────────────────────────────────────┐
 │  STEP 3 (conditional): Isolation Forest notify          │
 │  ONLY if: pred_family == "normal" AND                   │
 │           pmap["normal"] >= 0.95 (iso_p_normal_floor)   │
 │  Features: STAMP-FREE subset (no APP flags, no invoice) │
 │  Train: quiet-world genuine rows (pre-inject)           │
 │  Output: iso_anomalous bool (never overrides fraud call)│
 └──────────────────────┬───────────────────────────────────┘
                        │ pred_family, score, rule hits, iso flag
                        ▼
 ┌──────────────────────────────────────────────────────────┐
 │  STEP 4: Brake (brake.py)                               │
 │  Priority order:                                        │
 │  1. mule → mule_credit_restrict                        │
 │  2. calm_down + no hard_flag → allow                   │
 │  3. app_hit → hold (hard/score≥0.65) or notify         │
 │  4. invoice_hit → hold or case                         │
 │  5. ato_hit → decline (hard/score≥0.5) or step_up     │
 │  6. identity_burst → step_up or notify                 │
 │  7. score_elevated ≥ 0.65 → notify                    │
 │  [iso_anomalous AND action==allow → upgrade to notify] │
 │  8. else → allow                                       │
 └──────────────────────────────────────────────────────────┘
```

**LLM position:** Never on the scoring path above. LLM is used only for analyst case-tab text and Loop I rule-name packaging. LLM off auth path is verified by code inspection of `defend.py`.

---

## 4. Scoring path — one payment, numbered order

For a single inbound payment `e` at time `t`:

1. **Feature snapshot.** `FeatureComputer.snapshot_and_apply(e, t)` prunes deques to `G(t−)` (past edges only), reads `fan_in_1h`, `fan_out_1h`, `account_age_days`, `payee_history_count`, `amount_vs_p30`, `is_new_payee`, `is_new_device`, `burst_velocity`. Invoice booleans copied from `ev["payload"]` after Ticket 1. APP flags read from `features_auth` only on `app_fraud`-labelled rows; zero-valued on all others.

2. **Rules evaluation.** `evaluate_rules(flat_row, live_rules)` → `RuleEval(hits, kinds)`. `FORBIDDEN_RULE_FIELDS` validated by `parse_predicate`. Results: `hard_flag` → mandatory action; `calm_down` → suppress if no hard flag; `nudge` → optional score bump. Rule bits `rule__<id>` are appended to the feature vector before model scoring.

3. **Champion predict.** `champion.model.predict_proba(x)` → `pmap[family]`. `fraud_score = 1 - pmap["normal"]`. `pred_family = argmax`. Threshold `op_threshold` (from `recipe.operating_point_fpr = 0.01`) is frozen at inner-val.

4. **Isolation Forest notify (conditional, if GO).** Only triggered when `pred_family == "normal"` AND `pmap["normal"] >= iso_p_normal_floor` (0.95, frozen on inner-val). IF is queried on STAMP-FREE features. If `iso.predict(x_stampfree) == -1` (anomalous), sets `iso_notify = True`.

5. **Brake.** `brake(pred_label_family, score, hits, payee)` maps to `PolicyAction`. Mule check fires first. If `action == "allow"` and `iso_notify is True`, upgrades to `"notify"` with reason code `"iso_anomalous"`. APP is never silently declined.

6. **Reason codes.** `BrakeDecision.reason_codes` exposed to analyst UI and case tab. LLM may format prose from reason codes; does not alter them.

---

## 5. Champion specification

### 5.1 Target and label contract

- `y = label_family` ∈ `{normal, mule, identity_burst, ato, app_fraud, invoice_fraud}`. Never a technique ID. Enforced by `build_matrix` assertions in `split.py`.
- Multiclass `HistGradientBoostingClassifier`. One joblib artifact: `champion.joblib`.
- `ap_by_family` is computed OVR: for family `k`, AP = `average_precision_score(y == k, pmap[k])`. It is a metric, not a per-family model head.

### 5.2 Feature allowlist (X) and denylist

**Current allowlist** (`packages/sim/export.py` `TRAIN_ALLOWLIST`):
```
rail, kyc_tier, account_age_days, payee_history_count, amount_vs_p30,
fan_in_1h, fan_out_1h, is_new_payee, is_new_device, burst_velocity,
call_active_flag*, copy_paste_payee_flag*, pause_ms*, urgency_pressure*,
label_family (→ y, not X)
rule__<id> bits added by _attach_rule_bits()
```
`*` = only non-zero for `app_fraud` rows; always 0 for genuine rows in `export.py train_rows()`.

**After Ticket 1** (first blocker, must land before any champion metric is quoted in the walkthrough):
```
+ beneficiary_changed   (from ev["payload"], default false on non-invoice rows)
+ gstin_checksum_ok     (from ev["payload"], default false on non-invoice rows)
+ lookalike_domain_flag (from ev["payload"], default false on non-invoice rows)
+ fan_in_unique_payers_1h (causal O(n), unique sender ids on payee in last hour)
burst_velocity → REDEFINE as a different causal quantity (e.g. unique outbound payees 1h)
               OR drop from allowlist; update seasoning-burst rule accordingly
```
`gstin` string, `payload`, `is_authorized_push`, `label_class`, `economic_class`, `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, `transcripts` remain on `TRAIN_DENYLIST`. Enforced by `assert_no_x_leak` and `assert_train_schema`.

**Hard denylist for rules, same as model X denylist:** `FORBIDDEN_RULE_FIELDS` in `rules.py`. `parse_predicate` rejects them before backtest.

**APP flag ablation is mandatory.** Report AP with and without the four session flag columns (`call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`). If `app_metric_died_without_synthetic_flags` is true, document it as an honest finding, not a failure. Do not glue session flags onto genuine rows.

### 5.3 Class weights

HGB `class_weight` parameter: **sklearn's `HistGradientBoostingClassifier` does not accept `class_weight` as a constructor argument in all sklearn versions.** This parameter was added in sklearn 1.2 (Dec 2022). The `_app_ablation` function in `fit.py` line 193 uses `class_weight="balanced"` directly. **VERIFY IN REPO:** check `pyproject.toml` for `scikit-learn >= 1.2`. If uncertain, convert the ablation to use `sample_weight` (the pattern already used in `fit_champion`).

**Current champion path (verified in fit.py lines 362–370):** `_class_weight(y_tr)` computes `n / (k × count_k)` per class, then passes via `model.fit(X, y, sample_weight=per_row_weights)`. This is equivalent to balanced class weighting and is correct regardless of sklearn version. The recipe field `"class_weight": "balanced_from_this_run"` documents this.

**Why sample_weight before any adapter:** Imbalanced families (ato at 5% mix share, invoice_fraud at 10%) must receive upweighting before any specialist OVR attempt. Do not skip this step thinking the OVR adapter will compensate — the HGB head will already be biased toward majority classes without sample weighting.

### 5.4 Early stopping

**Current status:** No early stopping. Fixed `max_iter=80` from recipe. This is correct for reproducibility.

**sklearn HGB `validation_fraction` early stopping MUST NOT be used as the published protocol.** It creates a random internal holdout, which (1) ignores temporal ordering, (2) can include future-time rows in "validation" relative to some training rows, and (3) is invisible to the outer split protocol. The result would be an artifact-dependent model with a split that was not time-cut.

**Correct approach for Optuna (Ticket 5):** treat `max_iter` as an integer hyperparameter in the Optuna search space (range 40–200). Search on inner-val (time-respecting). Freeze the best `max_iter` into `features.json`. Refit on full outer train with frozen `max_iter`. Never run Optuna on G-test.

**If `validation_fraction` appears in any Optuna trial setup: MODIFY.** Disable it (`early_stopping=False`). Use `max_iter` as the tuned hyperparameter instead.

### 5.5 Optuna (Ticket 5)

**Why this not grid search:** Bayesian optimization finds better hyperparameters in fewer trials on a 30–50 trial budget than grid search on the same inner-val.

**Setup:**
- Search space: `max_depth` ∈ {2, 3, 4, 5}, `learning_rate` ∈ [0.02, 0.2] log-scale, `max_iter` ∈ [40, 200] int.
- Objective: binary-fraud AP (`average_precision_score(y_bin, 1-pmap["normal"])`) on inner-val. Do NOT use min-family AP — it optimizes on `ato`/`invoice` sampling noise when `n_pos` is small. If you want family AP sensitivity, add it as a secondary metric, not the primary objective.
- Constraint: penalize `genuine_fp > 0.01` in the objective (`binary_AP - 10 * max(0, genuine_fp - 0.01)`). Soft penalty, not hard prune.
- Trial cap: 30–50 trials. Wall-clock cap: 90 seconds (adjust to machine speed).
- Scope: Optuna study touches **inner-fit and inner-val only**. Never opens G-test parquet. Test enforces this.
- Refit: after study, refit champion on full outer train with frozen best params.
- Storage: `models/<run_id>/best_params.json`. Study pickle not required for scoring.
- Recipe field `"optuna": {"n_trials": 40, "wall_clock_s": 90}` is the freeze record.

**Sanity check:** if best `max_depth` is 1 or best `learning_rate` > 0.18, it likely chased inner-val noise. Check `n_pos` on inner-val before trusting the objective value.

### 5.6 Freeze and refit protocol

After Optuna (or after Ticket 3 with default params), the recipe `models/features.json` is frozen. Post-freeze steps:
1. Refit champion on full outer train (not just inner-fit) with frozen params.
2. Log `recipe_hash` = hash of `features.json`. Any score JSON without matching `recipe_hash` is not from the frozen run.
3. `gtest_opened_at` timestamp is logged the first time seed 43 metrics are computed for this `run_id`. Further optimization after that timestamp = protocol violation. Confirmation world is seed 45.

---

## 6. Rules v0 + Loop I + Loop T (MUST)

### 6.1 v0 — 9 live rules (verified in `data/rules/v0_rules.yaml`)

| Rule ID | Kind | Applies to | Key predicates | TechniqueIds |
|---|---|---|---|---|
| `call-and-paste-new-payee` | hard_flag | APP | call ∧ paste ∧ new_payee | T13,T14–T19 |
| `new-payee-large-new-device` | hard_flag | ATO | new_payee ∧ new_device ∧ amount_vs_p30≥2 | T12 |
| `mule-fan-in-burst` | hard_flag | mule | fan_in_1h≥6 | T01,T03,T05 |
| `invoice-beneficiary-swap` | hard_flag | BEC | beneficiary_changed ∧ gstin_checksum_ok | T24,T16,T18 |
| `smurf-under-cap` | nudge | mule | fan_in_1h≥4 ∧ amount_vs_p30≤1.0 | T03 |
| `rail-hop-burst` | nudge | mule | fan_out_1h≥4 | T04,T02 |
| `seasoning-burst` | nudge | ATO | burst_velocity≥4 ∧ account_age_days≥7 | T11 |
| `pause-paste-session` | nudge | APP | pause_ms≥1500 ∧ paste | T13,T19 |
| `calm-down-known-usual-device` | calm_down | genuine | !new_payee ∧ !new_device ∧ 0.4≤amount_vs_p30≤2.5 | — |

**NOTE on invoice rule:** `invoice-beneficiary-swap` can fire on a flattened auth row via `EXTRA_ROW_FIELDS` in `rules.py`. However, until Ticket 1 copies invoice booleans from `ev["payload"]` through `replay_features`, this rule cannot fire on train Parquet rows (`train_rows()` does not include these columns yet). Do not report invoice YAML hard_flag recall until Ticket 1 is green.

**NOTE on seasoning-burst:** uses `burst_velocity`. After Ticket 1 redefines or drops `burst_velocity`, update this rule's predicate name or threshold.

### 6.2 Loop I — rule drafting from catalog

`packages/policy/loop_i.py` `draft_rule_from_spec(spec)`:
- Named-gap check: T06, T07, T20–T23, high-dual-use, Cat 4 → `coverage_status: named_gap`.
- APP session shape (T13–T19 with call+paste+new_payee features) → drafts `call-and-paste-new-payee`.
- Mule fan-in → drafts `mule-fan-in-burst`.
- Invoice beneficiary → drafts `invoice-beneficiary-swap`.
- Observable features, no template → `case_only`.
- No observable auth features → `named_gap`.

**Drafts are not written to `v0_rules.yaml` today.** The API returns a dict. A human HITL click is required to promote. Drafts stay `status: draft` until promotion.

### 6.3 Loop T (MUST — implement from `defend-execution-ssot.md` Ticket 7)

Mine on **G-dev seed 44**, not inner-val (inner-val is reserved for Optuna / `op_threshold`). Train a short decision tree on G-dev FN vs genuine, extract ≤4-predicate paths, package as draft YAML. Hard rules:
- Maximum **5** draft rules per Loop T run.
- Maximum **4** predicates per rule.
- Minimum leaf support: reject any leaf with < 10 rows (not 3-row memorization).
- Generator-id conditions (`injector_id`, `technique_id`, `persona_type`) are forbidden by `FORBIDDEN_RULE_FIELDS` and caught by `parse_predicate`.
- Trees run on train-only misses. Never on G-test rows.
- LLM packages names and rationale; it does not invent `when` predicates. The tree-extracted predicate tuples must match `parse_predicate` output from the LLM `when` string — mismatch → reject draft, not "fix by trusting English."
- Two inboxes: FN/recall drafts (Loop I, Loop T on train misses) and FP/friction calm-downs (extra AND on genuine holdout). Never mix.
- APP and ATO must not share one `applies_to`.
- Do not mix APP and ATO in one rule.

### 6.4 HITL promotion gate

Mirror the Identify verbs (`approve | reject | reject_unsafe | edit`):
1. Evaluate candidate genuine FPR on **G-dev 44 `gdev_gate` only**. If `genuine_fpr > rule_promote_genuine_fpr_eps = 0.002` → reject or convert to nudge.
2. Incremental recall on the same `gdev_gate` fakes. **Never G-test 43.** Never the `gdev_mine` rows used to fit the tree.
3. Human click to promote. **Never auto-click**, including demos. Tests call `approve()` as the stand-in human.
4. Version the YAML; keep previous file.
5. `v0` rules stay `status: live` permanently; only new rows start as `draft`.

**Two distinct epsilon values (do not confuse):**
- `rule_promote_genuine_fpr_eps = 0.002` for HITL rule promotion on genuine holdout.
- `loop_m.genuine_fpr_eps = 0.02` for Loop M retrain comparison (noisier, smaller n).
Both are frozen in the recipe, not anonymous floats.

---

## 7. Brake actions

`packages/eval/brake.py` implements the following priority table. **Mule check fires first.**

| Priority | Trigger | Action | Rationale |
|---|---|---|---|
| 1 | `pred_family == mule` OR `"mule" in applies` | `mule_credit_restrict` | Disrupts receiving network, not just sender detection |
| 2 | `calm_down` hit AND no `hard_flag` | `allow` | Genuine kirana/rent; rules say it is safe |
| 3 | `app_hit` AND (`hard_flag` OR `score ≥ 0.65`) | `hold` | Victim authorized; do not decline. RBI cooling-period analog |
| 3b | `app_hit` AND low score | `notify` | Weak signal; alert only |
| 4 | `invoice_hit` AND (`hard_flag` OR `score ≥ 0.5`) | `hold` | BEC: corporate, not individual. Do not hard-decline open invoices |
| 4b | `invoice_hit` AND low score | `case` | Analyst review |
| 5 | `ato_hit` AND (`hard_flag` OR `score ≥ 0.5`) | `decline` | Credential stolen; no authorization |
| 5b | `ato_hit` AND low score | `step_up` | Soft friction |
| 6 | `pred_family == identity_burst` | `step_up` or `notify` | Velocity spike on new identity |
| 7 | `score ≥ 0.65` (no family match) | `notify` | Elevated model score without typology hit |
| 8 | else | `allow` | Low score, no rules |
| Override | `action == decline` AND `app_hit` AND NOT `mule_hit` | → `hold` | APP is NEVER hard-declined (victim authorized) |

**Isolation Forest insertion (if GO):** After step 8 (`allow`), if `iso_notify is True`, upgrade `allow` to `notify` with `reason_codes += ["iso_anomalous"]`. The iso cannot undo steps 1–7. Mule restrict and APP hold are never downgraded.

**Latency note:** `brake()` is pure Python row logic, O(1). No network. Latency is negligible relative to model inference.

---

## 8. Isolation Forest — MODIFIED GO

### 8.1 Decision: GO with mandatory modifications

**Rationale:** The proposal for a confidence-based anomaly check has real value for the "unknown unknowns" gap — genuine payments that look nothing like training distribution but where the champion correctly outputs high P(normal). Without this, novel attack patterns that slip through the champion with high confidence return `allow` silently. The Brake has no path to `notify` for a confident miss without IF or a hard rule.

**Why not KILL:** The feature-space and leakage concerns below are resolvable. The latency concern is negligible (sklearn IF on 1 row is sub-millisecond).

**Why not plain GO:** The original proposal uses the same X as champion. This introduces the stamp cheat (see below).

### 8.2 Critical modifications required

**Modification 1 — STAMP-FREE feature subset (mandatory, blocks GO if skipped):**

Training the IF on champion X is wrong because `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure` are always zero on genuine rows and always non-zero on `app_fraud` rows (injector always writes them). The IF trained on quiet-world genuine rows (where these flags are 0) will learn that the "normal" manifold has these flags = 0. Any row where they are non-zero (i.e., any app_fraud row) is anomalous to the IF — but this is the stamp cheat again, not genuine anomaly detection.

**IF input feature set must exclude:**
- `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure` (APP stamps)
- `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag` (invoice stamps, always-true on invoice rows)
- `rule__*` bits (computed from the above; derivative stamps)

**IF input feature set should include** (stamp-free numerics and categoricals):
- `fan_in_1h`, `fan_in_unique_payers_1h` (after Ticket 1), `fan_out_1h`
- `account_age_days`, `payee_history_count`, `amount_vs_p30`
- `is_new_payee`, `is_new_device`
- `burst_velocity` (or its replacement after Ticket 1)
- `rail`, `kyc_tier`

Freeze this list in recipe as `iso_feature_cols`. Do not add any column that is near-constant on genuine rows but non-zero on a specific fraud family.

**Modification 2 — Train on quiet-world (pre-inject) genuine rows:**

Post-mix "normal" rows are the complement of injected fraud. They are NOT a clean unsupervised sample — they include the entire quiet world except the explicit fraud injects. However, they may still contain genuine behavioral anomalies (large one-off genuine payments) that look odd and inflate FPR. The cleanest unsupervised sample is the quiet world **before** `apply_mix` is called.

In practice: from the train parquet, use rows where `label_family == "normal"` and filter to the **first 2/3 of the calendar** (inner-fit only). Do not train IF on G-test. Do not train IF on the eval fold.

**Never train IF on G-test data (seed 43 or 44). Never use G-test to set the contamination parameter.**

**Modification 3 — Contamination parameter:**

IsolationForest `contamination` is the expected fraction of anomalies in the training data. If we train on genuine rows only, contamination represents unlabeled genuine spend anomalies (unusual-but-legitimate transactions). Setting contamination too low → more anomalies flagged → higher FPR. Setting it too high → very few flags.

Pick the largest contamination where `genuine_fp_rate < iso_genuine_fpr_floor` (default **0.05**; freeze in recipe). If no contamination satisfies the floor even at 0.005, do not deploy IF.

Freeze: `iso_contamination` and `iso_n_estimators` (default 100) in `models/features.json` under `"isolation_forest"`. Do not tune on G-test.

**Modification 4 — Champion confidence gate definition:**

"High confidence normal" = `pmap["normal"] >= iso_p_normal_ceiling`. This is NOT the same as `score < threshold`. It is a high-confidence ALL-CLEAR from the champion. Define `iso_p_normal_ceiling` on inner-val: find the P(normal) above which >95% of genuine rows fall. If this fraction is too broad (i.e., the champion is never very confident normal on genuine rows), this gate fires rarely and iso is effectively disabled — which is acceptable.

Freeze `iso_p_normal_ceiling` in recipe. Log the fraction of genuine rows above this gate on inner-val and G-dev 44.

**Modification 5 — Mixed-scale tabular (bools + counts):**

sklearn IsolationForest is tree-based (uses random splits, not distances). No explicit scaling is needed. However, integer-valued features with high range (e.g., `fan_in_1h` 0–50, `account_age_days` 0–365) will produce splits at different granularities. This is acceptable for IF — the trees randomly split at random thresholds regardless of scale. No StandardScaler required.

### 8.3 What IF honestly covers and does NOT cover

**Covers (honestly):** Payment rows that fall outside the manifold of normal payments as defined by the stamp-free training features. This catches "unknown unknown" novel attack patterns that affect velocity, new-payee behavior, amount ratios, or timing — but which do not match any known fraud family signature in the champion.

**Does NOT cover:**
- **T06 (merchant collusion):** Merchant settlement cycles are not in the feature space. A merchant-routing attack row has no unusual features at the individual payment level — it looks like a normal payment.
- **T07 (BIN testing):** UPI-shaped events have no BIN field. Card authentication events are not simulated.
- **T20 (invoice-timed impersonation via voice clone):** IF cannot detect this because the feature tells are the session flags (APP) and beneficiary flags (invoice) — both excluded from the IF input.
- **T21 (voice-clone BEC):** Same as above.
- **T22/T23 (adversarial evasion / poisoning):** T22 is explicitly designed to fool row-level detectors. An adversarial row that passes the champion's feature distribution will also pass the IF — by design.

**Named gap remains named gap.** IF does not eliminate the T06/T07/T20–T23 named gaps. It is "unusual-pattern-on-this-X" detection, not a technique-specific sensor.

### 8.4 Ablate genuine FPR with/without iso notify

Required metric in score JSON: `iso_genuine_notify_rate` = fraction of genuine rows where `iso_notify = True`. Report alongside `genuine_fp` (champion FPR). If `iso_genuine_notify_rate > iso_genuine_fpr_floor`, abort deployment and log.

Required metric: `iso_triggered_rate` = fraction of all rows where IF is even consulted (i.e., fraction where champion returns confident normal). This should be small (mostly genuine rows) — a high rate means the champion is uncertain everywhere, which is a separate problem.

### 8.5 Brake insertion point

In `brake()`, after step 8 (`action = "allow"`, `reasons = ["low_score"]`):
```python
if iso_notify and action == "allow":
    action = "notify"
    reasons = ["iso_anomalous", *reasons]
```
This must execute AFTER the mule/calm-down/APP/invoice/ATO/identity-burst checks. An iso flag cannot undo `mule_credit_restrict`, `hold`, `decline`, `step_up`, or an existing `notify`.

---

## 9. Calibration, bootstrap CI, permutation importance

### 9.1 Isotonic calibration (MODIFIED GO)

**Problem:** `predict_proba` from an HGB on a multiclass problem is not per-class calibrated. A score of 0.7 for `mule` does not mean 70% probability. The threshold `op_threshold` from inner-val may not transfer to G-test due to miscalibration.

**sklearn `CalibratedClassifierCV` pitfalls with HGB multiclass:**
- `CalibratedClassifierCV(estimator=hgb, method="isotonic", cv="prefit")` wraps the already-fit HGB. In multiclass mode, it uses OVR internally — one binary calibrator per class.
- After calibration, the per-class calibrated probabilities may not sum to 1. **Renormalization is mandatory.**
- Fitting on G-test is forbidden. Use inner-val.

**Recommended approach — two-stage:**

Stage 1 (binary fraud score calibration, mandatory): Fit an isotonic regression mapping `fraud_score = 1 - pmap["normal"]` → `true_fraud_binary` on inner-val genuine + fraud rows. This calibrates the operating-point threshold without touching per-family probabilities.

Stage 2 (per-family calibration, optional for walkthrough ECE): For each family `k`, fit isotonic regression on `pmap[k]` → `I(y == k)` on inner-val. After fitting all 6 calibrators, renormalize the calibrated probability vector to sum to 1 (`p_cal[k] /= sum(p_cal)`). If the renormalized `p_cal["normal"]` is negative (can happen due to isotonic constraint relaxation), clamp to 0 and renormalize again.

**Calibration validation:** Compute ECE on G-dev (seed 44) before quoting in the walkthrough. Report ECE before and after calibration. ECE < 0.05 = well-calibrated; 0.05–0.10 = acceptable with disclaimer; ≥0.10 = do not present as a probability in the UI.

**Why before any OVR adapter:** The calibration baseline is the raw HGB. Attaching an OVR adapter after calibration changes the probability distribution and invalidates the calibrators. Calibrate the base HGB first, then decide on OVR based on G-dev family AP, then re-calibrate if needed.

### 9.2 Bootstrap CI on G-test AP (MODIFIED)

**IID bootstrap is wrong for this data.** Payment rows from the same mule payee account are correlated — they share the same `fan_in_1h` trajectory, same target payee, same account_age. Resampling individual rows independently treats these correlated observations as independent, which artificially narrows the confidence interval.

**Required modification — cluster bootstrap by payee entity:**
1. Group G-test rows by payee `VID-SIM-*` entity.
2. Sample entities with replacement (not rows).
3. For each bootstrap resample, take all rows belonging to sampled entities.
4. Compute AP from the resulting row set.
5. Repeat n=1000 times. Report 2.5th and 97.5th percentile as 95% CI.

**Honest reporting language:** "Bootstrap CI computed by cluster-resampling payee entities (n=1000). IID row bootstrap would produce a narrower CI by ignoring within-entity correlation. Entity-clustered CI is wider and more conservative."

**Why still useful:** Even an inflated CI establishes a lower bound: if the 2.5th percentile cluster-bootstrap AP is 0.65, then even accounting for entity correlation, the AP is unlikely to be below 0.65. This is an honest lower bound for the judge.

**Implementation note:** For `normal` rows (genuine payments), group by payer or use individual rows as single-element clusters. Mule/ATO/APP entities are fewer in number; cluster bootstrap CI will be wide on small families — this is correct, not a bug.

### 9.3 Permutation importance

**Where to compute:** G-dev (seed 44) or inner-val. NOT on G-test (seed 43).

**Why not G-test:** Permutation importance on G-test is using the headline fold for feature attribution after freeze. This is permissible in principle (it does not affect training), but there is a practical risk: observing that a feature is low-importance on G-test may tempt re-running without it, which amounts to using G-test for feature selection. Avoid this by computing on G-dev/inner-val before freeze.

**Protocol:**
1. After champion is fit on inner-fit, compute permutation importance on inner-val or G-dev 44.
2. Log as `top_features` in `metrics.json` (already present in `fit.py _top_features()` as correlation ranking; replace with permutation importance if Ticket 5 is done).
3. Freeze the feature list. Do not add/remove features based on G-test importances.
4. Include top-5 features by importance in the walkthrough for explainability story.
5. Permutation importance on G-test after freeze is allowed for analyst reporting, but must be labeled "post-freeze, informational only; no re-selection from this output."

---

## 10. Validation protocol

**Named seeds — non-negotiable:**

| Seed | Name | Allowed uses | Forbidden |
|---|---|---|---|
| 42 | Train world + `random_state` + fold RNG | `run_population(world_seed=42)`, `assign_folds(seed=42)`, `fit_champion(world_seed=42)` | Headline AP; HPO seed shopping |
| 43 | **G-test photographer** | One-shot headline AP, genuine FPR, Loop M before/after. `score_run(all_rows=True)` on gtest population | Family pick, specialist attach, Optuna, FE gating, rule mining, FN harvest, "just peek" |
| 44 | **G-dev** | FN harvest, OVR attach decision gating, rule recall backtest, IF contamination ablation, permutation importance, ECE confirmation | Headline slide; use after peeking 43 to avoid shopping |
| 45 | Confirmation world | ONLY if 43 was peeked (HPO/FE/attach ran after 43 was opened) | Using as a third shopping catalog |
| 99 | Canary convention | FinCEN chain / `run_canary` vault | Training champion; Loop M extras; quoting canary AP as G-test |
| 42 + 10007 | Loop M extra population | Extra family mix for train copy only (`loop_m.py`) | Same seed as G-test; appending onto 43 parquet |

**`gtest_opened_at`:** First time seed 43 metrics are computed for a `run_id`, log this timestamp. Any subsequent G-test run for the same `run_id` that changes model parameters, features, or recipe version after this timestamp = protocol violation. Confirmation world is then seed 45.

**Split protocol (verified in `split.py assign_folds`):**
- Sort by `event_ts`. First 2/3 calendar = train candidate. Last 1/3 = eval.
- Entity holdout: 30% of mule payees (`VID-SIM-U-*`, `VID-SIM-APP-*`, `VID-SIM-CHAIN-*`) and 15% of customers (`VID-SIM-C-*`) go to eval regardless of time.
- Never `train_test_split(shuffle=True)` as the published protocol.
- Protocol string: `time_cut_2_3_plus_entity_holdout`.

**Nested inner-val (Ticket 3):**
1. From the outer train fold, take the **last 20% of train calendar** as inner-val. Remainder = inner-fit.
2. Optuna search on inner-fit → score on inner-val.
3. Refit champion on full outer train with frozen params.
4. Same-run outer eval = diagnostic only. Label it `diagnostic` in metrics JSON. Never quote it in the walkthrough headline slot.
5. G-test population: same `n_customers`, `n_merchants`, `sim_days`, `pin`; `world_seed=43`. Persist `run_id`.
6. APP ablation: computed on inner-val during fit, AND on G-test 43 score JSON (add via Ticket 2).
7. Seeds: train 42, G-test 43, G-dev 44, Loop M extra 42+10007.

**Triple-dip on inner-val prevention:** If Optuna runs on inner-val AND Loop T mines rules on inner-val AND FE products are gated on inner-val, they compete for the same holdout. Either (a) partition inner-val into sub-slices: inner-HPO / inner-rules / inner-FE (three disjoint last-calendar chunks), or (b) time-box and sequence: HPO first (freezes recipe), then rules on G-dev 44, then FE on G-dev 44. Document which slices are used in the recipe.

**Required metrics table — every score JSON must include:**

| Field | Notes |
|---|---|
| `ap_by_family[fam]` | OVR AP from multiclass scores |
| `n_pos[fam]` | Number of positive examples per family in eval set. **Must add Ticket 2.** NaN AP without n_pos is uninterpretable. |
| `tpr_at_fpr` | Dict keyed by "0.001", "0.005", "0.01" |
| `genuine_fp` | FPR on `label_family == normal` rows |
| `f1_at_op` | F1 at same threshold as `tpr_at_fpr[0.01]` |
| `app_ablation` | `with_app_flags`, `without_app_flags`, `app_metric_died_without_synthetic_flags` |
| `authgate_ms` | `p50_ms_per_row`, `p99_ms_per_row`, `batch_seconds_1k` |
| `mule_entity_recall` | Fraction of gold mule payees caught on ≥1 inbound |
| `protocol` | Split protocol string |
| `iso_genuine_notify_rate` | If IF is deployed |
| `bootstrap_ci[fam]` | Cluster-bootstrap 95% CI per family (after Ticket 5 / calibration) |

**Cat 4 exclusion:** `y` must never be `T01`–`T24`. Enforced by `build_matrix` in `split.py`. Cat 4 rows must not appear in G-test.

---

## 11. Loop M — the clickable closed loop

**Status:** Code exists in `packages/eval/loop_m.py` and `POST /defend/loop-m`. Must work once for demo.

**What Loop M does (verified from code):**

1. Accept `run_id` + `miss_family` (one of the 5 fraud families).
2. Generate extra family mix: `run_population(families={miss_family}, world_seed=train_seed+10007)`. No Atlas; no knob search. Same injector, different seed.
3. Append extra rows to train copy (augmented run_id), capped at `extra_row_cap_frac=0.15` of original train length. Extra `event_id` pattern `evt-lm-*`.
4. Refit original champion (before, `world_seed=42`) and augmented champion (after).
5. Generate G-test population at `gtest_seed=43` (same scale as train sidecar). Assert `extra_ids ∩ gtest_event_ids == ∅`.
6. Score both champions on G-test: `score_run(all_rows=True)`.
7. Report `comparison.ap_verdict` ∈ {improved, equal, regressed, not_comparable} and `genuine_fp_ok`.
8. Return `catalog_solved: False` always.

**Family pick must NOT use G-test 43.** Pick the miss family from inner-val or G-dev 44. If you already used G-test to identify the miss family, the confirmation number moves to seed 45.

**Winner's curse prevention:** Picking the lowest-AP family from G-test and immediately generating extras for a second Loop M reported on the same 43 is selection bias. One-shot 43: run Loop M with a family identified from inner-val/G-dev 44, rescore 43 once, report the result whether it improves or not.

**n_pos honesty:** Loop M on `n_customers=20` (CI fixture) will almost always return `ap_verdict: not_comparable` due to tiny `n_pos`. Report that string. Do not fake a G-test win from the CI fixture.

**Loop G distinction:** Loop M calls `run_population(families={miss_family}, world_seed=new_seed)` — more rows from the same injector at the same default signals. This is NOT Loop G. Loop G would vary `signals=` (knob search). `packages/eval/loop_g.py` does not exist. Do not claim Loop G in the walkthrough.

---

## 12. Features — Ticket 1, windows, gated FE

### 12.1 Ticket 1 — Honesty floor (must land first)

**Invoice booleans (currently broken):** `doc_beneficiary.py` writes `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag` to `ev["payload"]`. `world.rebuild_features()` → `replay_features` rebuilds `features_auth` from graph/session only and **does not copy payload**. Therefore `train_rows()` in `export.py` never reads these booleans. The YAML rule `invoice-beneficiary-swap` fires on `EXTRA_ROW_FIELDS` at rule-evaluation time (via `flatten_row()` which reads `ev["payload"]`) but NOT on champion X. Invoice AP is noise until this is fixed.

**Fix:** In `replay_features` / `snapshot_and_apply`, after rebuilding graph features, copy boolean flags from `ev["payload"]` at `t−` into `features_auth`: `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag`. Default False on non-invoice rows. Add these three names to `TRAIN_ALLOWLIST` and include in `train_rows()`.

**Do NOT export:** `gstin` string (GSTIN identity leak), raw `payload` dict (stays on TRAIN_DENYLIST).

**Unique in-degree (currently broken):** `fan_in_1h = len(payee_acc.inbound_ts)` is an event count, not unique-sender count. `burst_velocity == float(fan_out_1h)` is a duplicate column.

**Fix:** Add `fan_in_unique_payers_1h` (unique payer IDs in `payee_acc.inbound_ts` last-hour window). Extend `AccountRuntime` with a `deque[tuple[datetime, str]]` of `(ts, counterparty_id)`. The snapshot prunes by time then counts unique ids. Keep `fan_in_1h` as event count (mule funnel uses volume). Redefine `burst_velocity` as `unique outbound payees 1h` (distinct payee ids in `outbound_ts` equivalent), OR drop it from the allowlist and update `seasoning-burst` rule to use `fan_out_1h` directly.

**Invoice stamp acknowledgment:** After Ticket 1, `beneficiary_changed` and `gstin_checksum_ok` are always True on `doc_beneficiary` inject rows and always False on genuine rows. This is a stamp. The ablation should document this. Invoice AP after Ticket 1 reflects the stamp's discriminative power, not general BEC detection capability. Do not call it "BEC detection skill."

### 12.2 Feature windows

All windows use `AccountRuntime` O(n) deques. Time slices:
- `1h` window: prune by `now - timedelta(hours=1)`.
- `30d` amount window: prune by `now - timedelta(days=30)`.
- **Never** re-scan full history per row before the Plan 08 50k-row run.

**Causal ordering (verified in `features.py snapshot_and_apply`):** Deques are pruned to `G(t−)`, then snapshot taken, then current event appended. Any new feature must maintain this ordering. Test: tiny synthetic-clock fixture (two inbound at `t+1s` and `t−1s` relative to the scored event) must compute window counts correctly.

### 12.3 Gated interaction features (≤5, optional, after Tickets 1–5)

Only after inner-val lift vs base allowlist is confirmed. Products of **allowlisted numerics** only (e.g., `fan_in_1h * account_age_days`). Hard rules:
- Never Featuretools or any DFS on the event log.
- Never products of APP-flag columns (these are near-labels; interaction products are the stamp cheat squared).
- Never products of invoice-flag columns for the same reason.
- Check correlation with main features before adding: a product that tracks `fan_in_1h` is not a new measurement.
- Gate on inner-val AND same-run diagnostic eval (both must show lift). Never gate on G-test 43.
- Self-median/mean ratios (`amount_vs_p30`) are more informative than random pairwise products. Prefer missing measurements (invoice envelope, unique in-degree) over products of existing columns.

### 12.4 Denylist — permanently forbidden on X

`vector_id`, `world_seed`, `technique_id`, `injector_id`, `simulatable_signals`, `persona_type`, `is_authorized_push`, `economic_class`, `label_class`, `gstin`, `payload`, `transcripts`, `liveness_score` or `doc_consistency` on non-onboarding rows (these are onboarding-only fields in the ledger), embeddings.

---

## 13. Coverage map honesty

### 13.1 What `live_rule` means

`packages/policy/coverage.py` `build_coverage_map` calls `match_rules_to_features(spec.features_expected, v0_rules)`. A technique has `coverage_status = live_rule` if any live rule's predicates overlap with the technique's `features_expected` via `COVERAGE_EQUIV` aliases. **This is feature-name overlap, not fire-rate on that technique's traffic.** T14–T19 all share `app_session` flag features, so they all match `call-and-paste-new-payee` — but that does not mean the rule fires on 6 distinct behaviors. Do not say "24 detectors" or sell coverage fire-rates per TechniqueId in the walkthrough.

### 13.2 Named gaps (name_only techniques)

The following techniques are `generate_mode = name_only` in the seed catalog. They cannot be detected at payment-auth time with available rail signals:

| TechniqueId | Name | Gap reason |
|---|---|---|
| T06 | Synthetic merchant collusion | Requires merchant settlement node graph not in sim |
| T07 | Card / BIN testing | UPI-shaped events; no BIN field; card auth rail not simulated |
| T20 | Invoice-timed impersonation | Dual-channel attack; no separate telephony or voice-clone rail signal |
| T21 | Voice-clone BEC | No audio generation; no distinct payment-time tell beyond beneficiary swap |
| T22 | Detector evasion (Cat 4) | Offline Loop A; no public evasion API |
| T23 | Training-data poisoning (Cat 4) | Offline / trust-tier gate; not in population runs |

**These named gaps are correct, not failed, answers.** A system that claims to detect all 24 at payment time is lying.

### 13.3 What IF does and does NOT cover in the coverage map

IF covers "payments that fall outside the quiet-world stamp-free feature manifold." This is a **supplemental unnamed category**, not a replacement for named gaps. It does NOT:
- Close T06 (no merchant cycle in feature space)
- Close T07 (no card features)
- Close T20/T21 (these attacks use APP and invoice stamp features, which are excluded from IF input by design)
- Close T22/T23 (adversarial attacks are designed to evade exactly these manifold detectors)

The correct walkthrough language: "For techniques outside the injection taxonomy, IF provides a `notify` signal when payment-time features are unusual relative to the genuine manifold. This is a bounded mitigation for unknown unknowns, not a closure of named gaps."

### 13.4 24 → 4 → 1 taper for walkthrough

Correct language: "Atlas maps 24 GenAI fraud techniques across 5 categories, with 7 named as payment-rail-observable and 5 as named gaps. ShadowRail injects 5 fraud families through 4 engines. AuthGate is one multiclass GBDT plus 9 YAML rules; family AP is a measurement, not five separate heads."

Incorrect language (forbidden): "We detect 24 attacks." "22 generate-mode cards train the model." "Five live models." "Nine loops close the system."

---

## 14. Required metrics in every score JSON

Every call to `fit_champion` or `score_run` must produce a `metrics.json` with these fields (enforced by `_metrics_pass`). Missing fields = `pass: False`.

| Field | Status | Notes |
|---|---|---|
| `ap_by_family` | exists | OVR AP per family, NaN if n_pos=0 |
| `n_pos` per family | **ADD Ticket 2** | Without n_pos, NaN AP is uninterpretable |
| `tpr_at_fpr["0.001/0.005/0.01"]` | exists | Binary fraud vs normal |
| `genuine_fp` | exists | FPR on `label_family==normal` rows |
| `f1_at_op` | exists | F1 at same threshold as TPR@1% FPR |
| `app_ablation` | exists | `with_app_flags`, `without_app_flags`, `app_metric_died_without_synthetic_flags` |
| `authgate_ms` | exists | `p50_ms_per_row`, `p99_ms_per_row`, `batch_seconds_1k`. Note: laptop in-process only. |
| `mule_entity_recall` | exists | Fraction of gold mule payees caught |
| `protocol` | exists | Split protocol string |
| `app_ablation` on G-test | **ADD Ticket 2** | Currently only on fit eval fold; must be in G-test score JSON |
| `iso_genuine_notify_rate` | ADD if IF deployed | |
| `bootstrap_ci` | ADD after Ticket 5 | Cluster bootstrap per family |
| `ece_before_cal / ece_after_cal` | ADD after calibration | Binary fraud score ECE |
| Lab cost sketch | ADD MUST | Miss $ vs decline $ vs APP hold $ at operating point. Lab units; not India prevalence. |

**Headline field is G-test (seed 43), not same-run eval.** Label same-run outer eval `diagnostic` in the JSON. Walkthrough grabs the G-test blob (`gtest_before` / `gtest_after` in Loop M, or `score_run` on the 43 `run_id`).

---

## 15. Implementation tickets (sequenced)

**IMPLEMENTATION SSOT:** `Docs/plans/defend-execution-ssot.md`. Ticket map: 1A/1B honesty floor → 2 n_pos → 3 inner-val → 4 Makefile → 5 Optuna SHOULD → 6 Loop M → **7 Loop T MUST** → 8 IF SHOULD → 9 isotonic SHOULD → 10 bootstrap SHOULD. Loop G is not a ticket. The numbered subsections below may lag; do not implement from them if they conflict.

### Ticket 1 — Honesty floor: invoice X + unique in-degree + burst clone

**Blocker for any invoice AP or coverage fire-rate claim.**

Files: `packages/sim/features.py`, `packages/sim/world.py` (replay), `packages/sim/export.py`, `packages/policy/rules.py` (COVERAGE_EQUIV if adding fan_in_unique_payers_1h), `data/rules/v0_rules.yaml` (if burst_velocity redefined), `tests/test_sim_export.py`, `tests/test_sim_inject.py`, `tests/test_eval_rules_brake.py`, `tests/test_eval_fit.py`.

Done when: pytest passes; invoice parquet rows have `beneficiary_changed=True`, `gstin_checksum_ok=True`; genuine rows have both False; `gstin` absent; `fan_in_unique_payers_1h` computed (unique=1 when same payer twice in 1h, count=2); `burst_velocity` not equal to `fan_out_1h` on mule rows.

### Ticket 2 — n_pos + APP ablation on G-test in artifacts

Files: `packages/eval/fit.py` (add `n_pos` per family), `packages/eval/split.py` (assert entity holdout), `tests/test_eval_fit.py`.

Done when: `metrics.json` from `fit_champion` contains `n_pos[fam]` for every family key in `ap_by_family`; APP ablation keys present on G-test `/defend/score` JSON; no walkthrough sentence claims 24 live rules without named_gap.

### Ticket 3 — Nested protocol + frozen G-test seed

Files: `packages/eval/split.py` (add inner-val split function), `packages/eval/fit.py` (wire inner-val into HPO if Ticket 5 in scope), `models/features.json` (add protocol string), `tests/test_eval_split.py`, `tests/test_eval_fit.py`.

Done when: inner-val is last 20% of train calendar, not a random split; G-test `world_seed != train_seed` is asserted in `run_loop_m`; protocol string in metrics JSON; test fails if shuffle split is used as reported protocol; HPO (Ticket 5) cannot open G-test parquet.

### Ticket 4 — Volume for submission run

Files: `Makefile` (or documented CLI command), README.

Done when: one documented command runs full mix (2400×120×90, seed 42), then G-test (seed 43 at same scale). `run_id`s recorded. CI remains `n_customers=20`.

### Ticket 5 — Optuna freeze (SHOULD; after 1–4)

Files: `pyproject.toml` (add optuna to optional extras), `packages/eval/fit.py` (Optuna study on inner-val), `models/features.json` (add optuna section), new `models/<run_id>/best_params.json`, tests.

Bounds: 30–50 trials; `max_depth` ∈ {2,3,4,5}, `learning_rate` ∈ [0.02, 0.2] log, `max_iter` ∈ [40, 200]. Objective: binary AP + genuine-FPR floor. Disable `validation_fraction` early stopping in HGB. Refit on full outer train with frozen params. Done when: deterministic refit from frozen params; study pickle not required to score.

### Ticket 6 — Loop M demo (MUST; code exists)

Files: `packages/eval/loop_m.py` (polish; add `n_pos` to comparison output), UI/walkthrough chart.

Done when: one HTTP or CLI path produces before/after JSON on Plan 08-sized run; CI remains small; `not_comparable` reported honestly; `catalog_solved: False` always; extras not on G-test (existing assert).

### Ticket 8 — Isolation Forest (SHOULD after Ticket 5)

Files: new `packages/eval/iso_check.py`, `packages/eval/fit.py` (call iso after champion), `packages/eval/brake.py` (add iso_notify parameter), `models/features.json` (add `isolation_forest` section), tests.

Done when: IF trained on stamp-free quiet-world genuine rows from inner-fit; `iso_genuine_notify_rate` ≤ `iso_genuine_fpr_floor` on inner-val; `iso_contamination` frozen in recipe; Brake inserts notify only after allow; mule/APP/ATO actions not downgraded.

### Ticket 9 — Isotonic calibration + ECE (SHOULD after Ticket 5)

Files: `packages/eval/fit.py` (fit isotonic on inner-val), `packages/eval/split.py` (if inner-val split not already there), `models/features.json` (add calibration section), tests.

Done when: binary fraud score ECE reported before and after calibration on G-dev 44; per-family calibrated probabilities renormalized to sum to 1; ECE in score JSON.

### Ticket 10 — Bootstrap CI + permutation importance (SHOULD after Ticket 5)

Files: `packages/eval/fit.py` (add cluster bootstrap function), tests.

Done when: `bootstrap_ci[fam]` cluster-resampled by payee entity in G-test score JSON; permutation importance logged on G-dev 44 or inner-val; no feature re-selection from G-test importances.

### Ticket 7 — Loop T: Rule Mining HITL (MANDATORY — not "if time")

**Promoted from optional to MUST. This is the agentic HITL pipeline. Build after Phase 1 green.**

Files: new `packages/eval/loop_t.py`, new `packages/policy/rule_hitl.py`, new `data/rules/drafts.json`, new `data/rules/versions.json`, `packages/policy/rules.py` (add `promote_from_draft`), `apps/api/routes/defend.py` (four endpoints: mine, drafts, approve, reject), tests.

Pipeline: FN mining (depth-3 DT on **G-dev 44 `gdev_mine`** vs genuine) → Jaccard vs live rules → FPR + incremental recall on **`gdev_gate`** → LLM `id`+`reason` only → HITL queue → four HTTP routes (mine/drafts/approve/reject) → list-root YAML + `versions.json` backups.

FP inbox: live rules with excessive genuine-FPR → propose tighten/calm-down → same HITL queue (`source: "loop_t_fp"`).

Done when: `pytest tests/test_loop_t.py` passes; draft cannot become live without HITL approve; `rule_promote_genuine_fpr_eps = 0.002` frozen in recipe; rollback tested; coverage map gains `live_rule` cells after approve.

**Ticket numbering after this change:**
- Ticket 7 = Loop T HITL (MANDATORY, NEW)
- Ticket 8 = Isolation Forest (SHOULD, was Ticket 7)
- Ticket 9 = Isotonic calibration (SHOULD, was Ticket 8)
- Ticket 10 = Bootstrap CI + permutation importance (SHOULD, was Ticket 9)

The implementation file [`defend-execution-ssot.md`](defend-execution-ssot.md) is SSOT for ticket numbering. Ignore Cursor plan filenames.

---

## 16. Non-goals

The following will not be built and must not appear in the walkthrough or UI as claimed live features:

| Item | Reason |
|---|---|
| Five live family models / five pickled HGBs | Council overruled. One multiclass HGB. `champion.joblib` is one model. |
| AutoGluon / FLAML / LightGBM on demo path | AutoGluon = overnight write-up challenger only. Optuna is the HPO. |
| GNN at payment time | GNN inference 100ms–seconds; not feasible at payment time. Trees with graph features match GNN quality per Tide 2026. |
| Featuretools / DFS on event log | Creates O(n²) complexity; produces uninspectable features. |
| CaseScore LLM on live payment auth | LLM latency 500ms–5s. Off the scoring path by design. |
| Auto-`solved` from Loop M or any metric bump | `catalog_solved: False` hardcoded in `loop_m.py`. HITL only. |
| Auto-promote rules | HITL promote required. No auto-on. |
| Nine live feedback loops | Coded target this sprint: I, C, M, **T**. Named roadmap only: R, A, F, G, H. Do not add Loop G. |
| Loop G before Loop M is green | Loop M must be a clickable honest before/after first. |
| Cat 4 public red-team API | Offline loop only. No public `/attack` endpoint. |
| Train on eval fold | Forbidden by split protocol. CI enforces. |
| Harvest FN from G-test 43 then re-report on 43 | Protocol violation. Use G-dev 44. |
| Live UPI / India prevalence claims | Lab fraud rate 0.5–3.5% ≠ India sub-0.01%. Always state "lab oversample." |
| "Beats Mastercard production" | Research lab prototype framing throughout. |
| `injectors.py` as training source | Stub file with `label_family: T13`. Do not train from it; do not delete without import check. |

**Kill triggers (from handoff):**
- Loop M `not_comparable` on n=20: do not fake nine loops. Ship coverage honesty + invoice X + G-test table.
- APP AP dies without flags: document ablation, do not glue flags onto genuine traffic.
- Invoice AP noise after Ticket 1: no GSTIN identity features. Stamp AP is the expected result.
- Clock dying: skip Loop G, Optuna, five models. Keep honesty floor + Loop M chart.

---

## 17. Pointers to related documents

| Document | Role |
|---|---|
| `Docs/plans/defend-execution-ssot.md` | **How to implement. Ticket numbers. Constants. Wins on conflicts.** |
| `Docs/plans/defend-dev-keepinminds.md` | PR-time checklist. Tick items before merge. Encodes every live failure mode as a do-not. |
| `VALIDATION.md` | Testable metric thresholds, seven hard gates (G1–G7), coverage status definitions, pre-submission checklist. |
| `Docs/plans/architecture-defense-doc.md` | Judge-facing Defend note: stack, mermaid, metrics, named gaps. |
| `Docs/plans/defend-test-tracker.md` | Unit / ML / HTTP / Generate→Defend test matrix. |
| `Docs/plans/08-generate-world-build.md` | Plan 08 Generate scale pin (n=2400×120×90). CI uses n=20. Walkthrough metrics must use Plan 08 scale. |
| `data/rules/v0_rules.yaml` | 9 live rules. Source-controlled. Do not commit `champion.joblib`. |
| `models/features.json` | Frozen recipe. Every scoring run reads this. Recipe hash recorded in score JSON after freeze. |
| `packages/eval/fit.py` | `fit_champion`, `score_run`, `_app_ablation`, `_bench_ms`. The actual training code. Read before writing. |
| `packages/eval/loop_m.py` | Loop M implementation. Already asserts `extra_ids ∩ gtest_event_ids == ∅` and `catalog_solved: False`. |
| `packages/eval/brake.py` | Brake action table. Verified order: mule → calm → APP → invoice → ATO → identity_burst. |
| `packages/sim/export.py` | `TRAIN_ALLOWLIST`, `TRAIN_DENYLIST`, `train_rows()`. Ground truth for feature schema. |
| `packages/policy/rules.py` | `FORBIDDEN_RULE_FIELDS`, `COVERAGE_EQUIV`, `parse_predicate`, rule evaluation. |
| `Docs/plans/defense-why.md` | Decision rationale appendix for judges. Exists at this path. |
| `packages/eval/loop_t.py` | Loop T rule mining pipeline — `mine_fn_rules`, backtest gate, LLM packaging. New file — Ticket 7. |
| `packages/policy/rule_hitl.py` | HITL draft queue, approve/reject/rollback, YAML versioning. New file — Ticket 7. |
| `data/rules/drafts.json` | Loop T HITL queue (git-tracked). New file — Ticket 7. |
| `data/rules/versions.json` | YAML version log with sha pointers for rollback. New file — Ticket 7. |

---

*Verified file reads: MC_PS.md, defend-peak-handoff.md, VALIDATION.md, defend-dev-keepinminds.md, packages/eval/fit.py, packages/eval/split.py, packages/eval/loop_m.py, packages/eval/brake.py, packages/sim/features.py (head), packages/sim/export.py, packages/sim/inject/mix.py, packages/policy/rules.py, packages/policy/loop_i.py, packages/policy/coverage.py, data/rules/v0_rules.yaml, models/features.json. 2026-08-28.*
