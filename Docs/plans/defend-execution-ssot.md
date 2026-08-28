# AegisLoop Defend — Execution SSOT (agent implement this)

**Audience:** a coding agent that has not read the council chat.  
**Repo:** `/home/aarush_linux/projects/Mastercard`  
**Status:** LOCKED 2026-08-28. If another doc disagrees, **this file wins for how to code**. Architecture *meaning* still lives in `Docs/plans/defense-architecture.md`.  
**Do not reopen locked tables.** Do not invent a fifth option at runtime.

**Read this order before writing code:**

0. Cursor plan `defend_peak_implementation_d6545d76.plan.md` (which file to open). Repo index: `Docs/plans/README-defend.md`.
1. This file (how, constants, tickets). **§13 overrides earlier sections of this file.**
2. `Docs/plans/defend-test-tracker.md` — write named tests RED first.
3. `Docs/plans/defend-dev-keepinminds.md` — do-nots.
4. The source files named in the ticket.

---

## 0. Locked product (do not reopen)

| Item | Locked meaning |
|---|---|
| Champion | ONE `HistGradientBoostingClassifier`, `y = label_family` (6 classes). Family AP is a metric, not five models. |
| Specialists | Zero this sprint. Do not add OVR adapters. |
| HPO | Optuna on inner-val only. AutoGluon never on path. |
| Loop M | Clickable miss → extra Generate → refit → G-test seed 43. `catalog_solved: False` always. |
| Loop T | **MUST.** Tree mine → deterministic gates → HITL queue → human approve → versioned YAML. |
| Loop G | **DO NOT BUILD.** Not a ticket. |
| Rules | 9 v0 stay `status: live`. New rules start `draft`. Never auto-promote. |
| LLM | Off auth path. Loop T may name `id`+`reason` only. If LLM missing, auto-id. Pipeline never waits on LLM. |
| Headline metrics | G-test `world_seed=43` only. Same-run eval is `diagnostic`. |
| Demo scale | Plan 08: `n_customers=2400`, `n_merchants=120`, `sim_days=90`. CI pytest default stays small. |

**Forbidden this sprint:** five models, AutoGluon, GNN, Featuretools, CaseScore LLM on auth, auto-`solved`, Loop G, Featuretools products on APP/invoice stamps, train-on-eval, FN harvest from seed 43.

---

## 1. Frozen constants (copy into `models/features.json` as you implement; do not retune)

Write these keys into `models/features.json` when the matching ticket lands. Values below are **final**.

```json
{
  "estimator": "HistGradientBoostingClassifier",
  "y": "label_family",
  "random_state": 42,
  "max_depth": 3,
  "max_iter": 80,
  "learning_rate": 0.08,
  "early_stopping": false,
  "operating_point_fpr": 0.01,
  "tpr_at_fpr": [0.001, 0.005, 0.01],
  "n_pos_not_comparable_below": 30,
  "inner_val": {
    "method": "last_20pct_train_calendar",
    "fraction": 0.20
  },
  "loop_m": {
    "ap_equal_eps": 0.05,
    "genuine_fpr_eps": 0.02,
    "extra_row_cap_frac": 0.15,
    "extra_seed_offset": 10007
  },
  "loop_t": {
    "fold": "gdev44",
    "max_depth": 3,
    "min_samples_leaf": 10,
    "min_leaf_precision": 0.70,
    "max_candidates": 5,
    "max_predicates": 4,
    "jaccard_duplicate": 0.80,
    "min_fn": 10,
    "min_genuine": 30,
    "rule_promote_genuine_fpr_eps": 0.002,
    "fp_inbox_threshold": 0.005,
    "fp_recall_floor": 0.80
  },
  "isolation_forest": {
    "enabled_default": false,
    "n_estimators": 100,
    "contamination": 0.01,
    "random_state": 42,
    "iso_p_normal_floor": 0.95,
    "iso_genuine_fpr_floor": 0.05
  },
  "calibration": {
    "stage1_binary": true,
    "stage2_per_family_min_n_pos": 50
  },
  "bootstrap": {
    "n_resamples_ci": 200,
    "n_resamples_submission": 1000
  },
  "optuna": {
    "n_trials": 40,
    "n_trials_ci": 10,
    "timeout_sec": 600,
    "max_depth": [2, 3, 4, 5],
    "learning_rate_log_low": 0.02,
    "learning_rate_log_high": 0.2,
    "max_iter_low": 40,
    "max_iter_high": 200
  }
}
```

**Two FPR epsilons — never collapse them:**

| Name | Value | Used for |
|---|---|---|
| `operating_point_fpr` | 0.01 | Champion threshold / TPR@FPR curves |
| `loop_m.genuine_fpr_eps` | 0.02 | Loop M before/after slack (noisy, especially n=20) |
| `loop_t.rule_promote_genuine_fpr_eps` | 0.002 | HITL rule promotion on G-dev 44 genuine |
| `loop_t.fp_inbox_threshold` | 0.005 | Which live rules enter the FP inbox |

---

## 2. Frozen run_ids and seeds

| Purpose | `run_id` | `world_seed` | Scale |
|---|---|---|---|
| Train world | `make-scale-fullmix` | 42 | 2400×120×90 (Makefile). CI tests: 16–20 customers. |
| G-test photographer | `make-gtest` | 43 | Same n as the train sidecar being scored |
| G-dev (harvest, Loop T backtest, ECE, permutation, IF abort check) | `make-gdev` | 44 | Same n as train sidecar for submission; n=20 allowed in unit tests |
| Confirmation if 43 was peeked | `make-gconfirm` | 45 | Only if protocol broken |
| Loop M extras | `{train_run_id}-lm` | train_seed + 10007 | Capped at 15% of train rows |

**G-test rule:** first score of seed 43 for a recipe hash logs `gtest_opened_at`. After that, do not change features/params and rescore 43. If you already peeked, headline moves to seed 45.

---

## 3. Frozen feature contract (Ticket 1)

### 3.1 `TRAIN_ALLOWLIST` after Ticket 1 (exact tuple)

```
rail, kyc_tier, account_age_days, payee_history_count, amount_vs_p30,
fan_in_1h, fan_out_1h, fan_in_unique_payers_1h,
is_new_payee, is_new_device, burst_velocity,
call_active_flag, copy_paste_payee_flag, pause_ms, urgency_pressure,
beneficiary_changed, gstin_checksum_ok, lookalike_domain_flag,
label_family
```

`label_family` is y, never X (`build_matrix` already drops it).  
`rule__<id>` bits are appended later in `fit.py` and are allowed on X.

### 3.2 `TRAIN_DENYLIST` — do not edit except if a new leak column appears

Keep: `vector_id, injector_id, technique_id, simulatable_signals, persona_type, world_seed, transcripts, is_authorized_push, economic_class, label_class, gstin, payload`.

### 3.3 Invoice booleans — exact code path

**Bug (verified):** `doc_beneficiary` writes flags into `ev["payload"]`. `replay_features` rebuilds `features_auth` from graph/session only and **drops** payload flags. `train_rows()` never sees them.

**Fix — do both:**

1. In `replay_features` after `computed = fc.snapshot_and_apply(...)` and before `new_ev["features_auth"] = computed`:

```python
payload = ev.get("payload") or {}
for key in ("beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag"):
    computed[key] = bool(payload.get(key, False))
```

2. In `export.train_rows()`, copy the same three keys from `fa` with default `False`.

3. Add the three names to `TRAIN_ALLOWLIST`.

4. Do **not** export `gstin` or raw `payload`.

**Honesty:** after this fix, invoice inject rows will almost always have both `beneficiary_changed=True` and `gstin_checksum_ok=True`, genuine rows False. Invoice AP is **stamp skill**. Report it, do not call it “BEC detection in the wild.”

### 3.4 Unique in-degree + burst_velocity — exact semantics (no “or drop”)

**Do not drop `burst_velocity`.** Redefine it. Keep YAML `seasoning-burst` predicate `burst_velocity >= 4`.

Change `AccountRuntime` deques:

- Replace `inbound_ts: deque[datetime]` with `inbound_edges: deque[tuple[datetime, str]]` storing `(ts, payer_id)`.
- Replace `outbound_ts: deque[datetime]` with `outbound_edges: deque[tuple[datetime, str]]` storing `(ts, payee_id)`.
- Keep `amount_history` as-is.

Prune by `ts` on the tuple’s first element.

After prune, **before** appending the current edge:

| Feature | Formula |
|---|---|
| `fan_in_1h` | `len(payee_acc.inbound_edges)` |
| `fan_in_unique_payers_1h` | `len({pid for _, pid in payee_acc.inbound_edges})` |
| `fan_out_1h` | `len(payer_acc.outbound_edges)` |
| `burst_velocity` | `float(len({pid for _, pid in payer_acc.outbound_edges}))` |

Then append current `(ts, payer)` to payee inbound and `(ts, payee)` to payer outbound (same order as today: snapshot then apply).

**Update every `inbound_ts` / `outbound_ts` reader** (`fidelity.py` recomputes from events, not these deques — still check `features.py` only).

**`COVERAGE_EQUIV`:** add `"fan_in_unique_payers_1h": frozenset({"fan_in_unique_payers_1h"})`.

**Fixture that must pass:** two inbound payments from the **same** payer to the same payee inside 1h → `fan_in_1h == 2` and `fan_in_unique_payers_1h == 1`. On a mule with 6 distinct senders, unique ≥ 6 and `burst_velocity != fan_out_1h` is not required on mule inbound (burst is outbound uniqueness). Assert `burst_velocity != fan_out_1h` on a payer who sent 3 payments to the **same** payee in 1h: `fan_out_1h==3`, `burst_velocity==1.0`.

---

## 4. Frozen validation protocol (Ticket 3)

### 4.1 Outer split (already coded — do not replace)

`assign_folds`: time cut first 2/3 calendar train-candidate; last 1/3 eval; plus entity holdout 30% mule payees / 15% customers. Protocol string: `time_cut_2_3_plus_entity_holdout`.

Never `train_test_split(shuffle=True)` as published protocol.

### 4.2 Inner split (add `inner_folds_from_train`)

Input: rows where outer `fold=="train"`.  
Sort by `event_ts`. Cut at last **20% of calendar span** (same style as `calendar_cut`, fraction 0.20 from the end).  
Label those rows `inner_val`; the rest of outer-train `inner_fit`.

**Do not randomly split inner-val.**

### 4.3 What uses which slice (NO triple-dip — sequenced, not three-way partition)

| Job | Slice | Forbidden |
|---|---|---|
| Fit for HPO / first champion | `inner_fit` | G-test 43 |
| Optuna objective + `op_threshold` | `inner_val` | G-test 43 |
| Refit after freeze | full outer `train` (`inner_fit`+`inner_val`) | — |
| Same-run outer eval | `eval` fold of seed 42 | Headline slide |
| Loop T mine + FPR backtest + FP inbox | **G-dev seed 44** | inner-val (already used by Optuna), G-test 43 |
| Isolation Forest train | `inner_fit` rows with `label_family==normal`, stamp-free cols | G-test, APP/invoice cols |
| IF FPR abort | `inner_val` genuine | G-test |
| Isotonic Stage 1 | `inner_val` | G-test |
| Permutation importance | `inner_val` | G-test for selection |
| Headline AP / Loop M before-after | G-test 43 | Using 43 to pick miss family |

**Loop T fold is G-dev 44, not inner-val.** That is the lock that prevents Optuna and rule mining from sharing one holdout.

### 4.4 `op_threshold` (current bug)

Today `fit_champion` computes TPR@FPR and `thr` on **outer eval**. Move:

1. Fit HGB on `inner_fit` with `sample_weight` from `_class_weight` (already exists — keep).
2. Compute `op_threshold` from `inner_val` scores at `operating_point_fpr=0.01`.
3. Set `HistGradientBoostingClassifier(..., early_stopping=False)` always.
4. Refit on full outer train with the **same** hyperparameters (recipe or Optuna best). Keep the frozen `op_threshold` from step 2 (do not recompute on outer eval).
5. Outer eval metrics go under `diagnostic_*` keys. `metrics["pass"]` may still check diagnostic sanity, but walkthrough headline is G-test.

---

## 5. Frozen metrics contract (every `metrics.json`)

`_metrics_pass` must require these keys after Ticket 2. Missing key → `pass: False`.

| Key | Ticket | Rule |
|---|---|---|
| `ap_by_family` | exists | OVR AP; NaN if n_pos=0 |
| `n_pos` | T2 | int per family including `normal` |
| `not_comparable` | T2 | `{fam: n_pos[fam] < 30}` for fraud families |
| `tpr_at_fpr` | exists | keys `"0.001"`, `"0.005"`, `"0.01"` |
| `genuine_fp` | exists | FPR on `normal` rows at `op_threshold` |
| `f1_at_op` | exists | same threshold |
| `app_ablation` | exists + T2 on G-test score | `with_app_flags`, `without_app_flags`, `app_metric_died_without_synthetic_flags` |
| `authgate_ms` | exists | p50/p99/batch_1k laptop |
| `mule_entity_recall` | exists | gold mule payees caught ≥1 inbound |
| `protocol` | exists | `time_cut_2_3_plus_entity_holdout` |
| `inner_val_protocol` | T3 | `last_20pct_train_calendar` |
| `diagnostic_ap_by_family` | T3 | outer eval; not headline |
| `recipe_hash` | T3 | sha256 of `features.json` bytes |
| `ece_before` / `ece_after` | T9 | binary fraud score; omit until T9 |
| `iso_genuine_notify_rate` | T8 | omit until IF enabled |
| `bootstrap_ci` | T10 | omit until T10 |
| `loop_t_drafts_proposed` | T7 | 0 until a mine run |

**Walkthrough headline block (must be a separate JSON file or key `gtest`):**

- `world_seed: 43`
- `run_id: make-gtest`
- `ap_by_family` + `n_pos` + `not_comparable`
- `genuine_fp`, `tpr_at_fpr`, `app_ablation`
- `mule_entity_recall`, `authgate_ms`
- Loop M: `gtest_before` / `gtest_after` with the same fields

**Never quote diagnostic AP in the walkthrough headline slot.**

**Lab cost sketch (Ticket 2, simple, no India prevalence):**

```
cost_sketch = {
  "unit": "lab_not_india",
  "miss_weight": 10.0,
  "fp_notify_weight": 1.0,
  "fp_hold_weight": 3.0,
  "fp_decline_weight": 8.0
}
```

Compute `expected_cost = miss_weight * FN_rate + weighted FP by Brake action histogram` on G-test. Put in metrics. Do not claim rupees.

---

## 6. Execution spine (one ticket at a time, in this order)

**Stop if the previous gate is red.** Do not “just start Optuna.”

```
T1A → T1B → T2 → T3 → T4
                         ├→ T5 (SHOULD; skip if clock dying after T7)
                         ├→ T6 (MUST polish)
                         └→ T7 (MUST Loop T; needs T3 + a seed-44 parquet)
After T5+T7 green, time permitting: T8 → T9 → T10
Docs patches: continuous, but a dedicated pass after T3
```

**Sprint success bar (strong Defend):** T1–T4 + T6 + T7 green on CI, plus one Plan 08 G-test metrics JSON with `n_pos` filled. T5/T8/T9/T10 are strength add-ons, not an excuse to skip T7.

---

## 7. Tickets — files, exact behavior, tests, stop-gates

### Ticket 1A — Invoice booleans on `features_auth` and parquet

**Touch:** `packages/sim/features.py` (`replay_features`), `packages/sim/export.py` (`TRAIN_ALLOWLIST`, `train_rows`), tests.  
**Do not touch:** injectors, Brake, fit hyperparameters.

**Tests (add to `tests/test_sim_export.py` and `tests/test_sim_inject.py`):**

- Invoice inject event after replay: `features_auth["beneficiary_changed"] is True`.
- Genuine event: all three flags False.
- Parquet columns include the three names; `gstin` not in parquet columns.
- `assert_train_schema` still passes.

**Stop-gate:** pytest for those tests green. If invoice injector test has zero invoice rows, fix mix in the **test fixture**, not by faking columns.

---

### Ticket 1B — Unique fan-in + redefine `burst_velocity`

**Touch:** `packages/sim/features.py` (`AccountRuntime`, `snapshot_and_apply`, prune), `packages/sim/export.py` allowlist + `train_rows`, `packages/policy/rules.py` `COVERAGE_EQUIV` only.  
**Do not change** `seasoning-burst` YAML id or threshold unless a test proves the new `burst_velocity` never reaches 4 (if so, keep threshold 4; unique outbound of 4 is still a burst).

**Tests:** unique-payer fixture above; burst vs fan_out fixture; causal order still “prune → snapshot → append” (existing inject tests must stay green). `fidelity.py` fan_in recompute still matches stored `fan_in_1h` (event count).

**Stop-gate:** `burst_velocity == fan_out_1h` is **false** on the same-payee-3x fixture.

---

### Ticket 2 — `n_pos` + G-test ablation keys + cost sketch

**Touch:** `packages/eval/fit.py` (`fit_champion`, `score_run`, `_metrics_pass`).  
**Add** `_n_pos_by_family(y) -> dict[str, int]` for all of `LABEL_FAMILIES`.

**Tests in `tests/test_eval_fit.py`:** `"n_pos" in metrics`; `not_comparable` True when n_pos < 30; `score_run` JSON also has `n_pos` and `app_ablation`.

**Stop-gate:** no AP table without `n_pos` can be produced by `fit_champion`.

---

### Ticket 3 — Nested inner-val + frozen threshold + `early_stopping=False`

**Touch:** `packages/eval/split.py` (new `inner_folds_from_train`), `packages/eval/fit.py`, `models/features.json` (`inner_val` block, `early_stopping: false`).

**Tests in `tests/test_eval_split.py` / `test_eval_fit.py`:**

- Inner-val rows are a suffix of train calendar, not a shuffle.
- Mock/spy: threshold function is called with inner-val y only (or assert event_ids used for thr ⊆ inner_val ids).
- `diagnostic_ap_by_family` present; headline fields may still exist for diagnostic but labeled.
- HGB constructed with `early_stopping=False`.

**Stop-gate:** a unit test fails if someone passes outer-eval labels into threshold selection.

---

### Ticket 4 — Makefile full mix + G-test + G-dev

**Touch:** `Makefile` only (and a 10-line comment in README if one already documents `generate-scale`).

**Replace `generate-scale`:** **remove** `vector_id='t13-upi-impersonation-app'`. Call `run_population(db, run_id='make-scale-fullmix', n_customers=2400, n_merchants=120, sim_days=90, world_seed=42, pin=True, ...)` with **no** vector_id so `DEFAULT_SIGNALS` full mix runs.

**Keep** `generate-validate` as the small T13 smoke (do not break CI).

**Add targets:**

- `defend-fit`: `fit_champion("make-scale-fullmix", world_seed=42)`
- `defend-gtest`: `run_population(..., run_id='make-gtest', world_seed=43, same n as sidecar)` then `score_run`
- `defend-gdev`: same at seed 44 / `make-gdev`
- `defend-loop-m`: documents required body `miss_family` + `family_chosen_from_slice=gdev44`

CI: `generate-scale` is slow; do not put it in `validate-all`.

**Stop-gate:** reading the Makefile shows no T13 pin on `generate-scale`.

---

### Ticket 5 — Optuna (SHOULD; after T3)

**Touch:** `pyproject.toml` add `optuna>=3.0` to `[project.optional-dependencies] dev` (sklearn already there). `packages/eval/fit.py` new `tune_champion`. `apps/api/routes/defend.py` `POST /defend/tune`. `models/{run_id}/best_params.json`.

**Objective (locked, not min-family AP):**  
`objective = binary_AP(inner_val) - 10.0 * max(0, genuine_fp - 0.01)`  
If inner-val fraud positives `< 50`, skip Optuna, log `optuna_skipped_small_n`, use recipe defaults.

**Search:** `max_depth` categorical {2,3,4,5}; `learning_rate` log-uniform [0.02, 0.2]; `max_iter` int [40, 200]. `n_trials=40` (CI: 10). `timeout=600`. `random_state=42`.

**Must not** open any parquet whose sidecar `world_seed==43`. Test with a monkeypatch/sentinel.

**After study:** write `best_params.json`; refit full outer train; keep inner-val `op_threshold`.

**Stop-gate:** study pickle is not required to `score_run`.

---

### Ticket 6 — Loop M polish (MUST)

**Touch:** `packages/eval/loop_m.py`, `LoopMRequest` in `defend.py`.

**Add to comparison JSON:** `n_pos` before/after per family; `family_chosen_from_slice` required enum `inner_val | diagnostic | gdev44`. **Reject** `gtest` / `43`.

Keep existing: extras `evt-lm-*`, disjoint from G-test ids, `catalog_solved: False`, extra seed offset 10007, cap 0.15.

**Stop-gate:** existing `tests/test_eval_loop_m.py` still green + new field assertions.

---

### Ticket 7 — Loop T + HITL (MUST)

**New files:**

- `packages/eval/loop_t.py` — mine + backtest + package
- `packages/policy/rule_hitl.py` — queue IO + approve/reject/edit/rollback
- `data/rules/drafts.json` — `{"drafts": []}`
- `data/rules/versions.json` — `{"versions": [{"version": 0, "note": "v0 baseline"}]}`
- `tests/test_loop_t.py`

**Modified:** `apps/api/routes/defend.py`, `packages/policy/rules.py` (`promote_from_draft` that writes YAML via existing parser).

**Do not** auto-write YAML from mine. **Do not** use LLM to choose thresholds.

#### 7.1 Mine (`mine_fn_rules`)

Inputs: `gdev_run_id` (seed 44 parquet+split+champion from train recipe), `family`, champion joblib from the **train** `run_id`.

Steps (deterministic):

1. Load G-dev train.parquet + split.parquet. Score with frozen champion (`score_run` or in-memory predict). **Do not fit on G-dev.**
2. FN rows: `label_family == family` AND not caught.  
   **Caught (locked):** `score >= op_threshold` **OR** any hit with `kind==hard_flag`.
3. Negatives: `label_family==normal` on G-dev. If more than 3× n_FN, subsample with `random_state=42`.
4. If `n_fn < 10` or `n_genuine < 30`: return `{"status":"skipped","reason":"insufficient_fn"}`.
5. Feature columns for the tree = numeric/bool columns in `ALLOWED_RULE_FIELDS` **minus** APP flag cols **minus** invoice three booleans (those are stamps). Include `fan_in_1h`, `fan_out_1h`, `fan_in_unique_payers_1h`, `burst_velocity`, `account_age_days`, `payee_history_count`, `amount_vs_p30`, `is_new_payee`, `is_new_device`. Categorical `rail`/`kyc_tier` **out of the tree** this sprint (keep rules human and numeric).
6. `DecisionTreeClassifier(max_depth=3, min_samples_leaf=10, random_state=42)`.
7. For each leaf with predicted class FN (positive): if precision ≥ 0.70 and n ≥ 10 and path length ≤ 4, convert sklearn threshold path to strings `field >= x` / `field <= x` / `field == true` using the same grammar as `parse_predicate` in `rules.py`. If `parse_predicate` fails → drop leaf.
8. Novelty: Jaccard of `(field, op)` pairs vs each live rule with same `applies_to` (map family→applies_to: mule→mule, app_fraud→APP, invoice_fraud→BEC, ato→ATO, identity_burst→ATO). If Jaccard > 0.80 → `duplicate_of_live_rule`.
9. Keep ≤ 5 candidates.

#### 7.2 Backtest (auto, before queue)

On **G-dev 44 genuine** (same fold you mined — this is allowed because G-dev is not G-test; do **not** retune on 43):

- `candidate_genuine_fpr > 0.002` → `fpr_exceeds_eps`
- incremental recall vs union of live hard_flags on this family ≤ 0 → `no_incremental_recall`

Survivors enqueue.

#### 7.3 LLM packaging (optional)

Call only after backtest survive. Prompt input JSON: `{when_clauses, applies_to, family, reason_examples}` where examples are existing live `reason` strings.  
Expected output JSON: `{id, reason}` only.  
Then **assert** `draft.when == candidate.when`. If LLM missing, timeout, or schema fail: `id = f"loop-t-{family}-{sha256(when)[:8]}"`, `reason = " AND ".join(when)`.

#### 7.4 HITL

`approve(draft_id)`:

1. Re-`parse_predicate` every clause (forbidden fields abort).
2. Append rule to `v0_rules.yaml` with `status: live`.
3. Bump `_meta.version` **or** if YAML has no `_meta`, add:

```yaml
_meta:
  version: 1
```

at the top. Parser must ignore `_meta` (today `load_v0_rules` loads a list — **keep list-root YAML**. Store version **only** in `data/rules/versions.json`, not inside the rule list. **Locked:** do not change YAML root type. Versioning is `versions.json` + file copy `data/rules/v0_rules.yaml.bak.{n}`.

4. Copy previous YAML to `data/rules/backups/v0_rules.v{n}.yaml`.
5. Mark draft `approved`.

`rollback(version)` restores backup file.

#### 7.5 API (exact)

| Method | Path | Body / result |
|---|---|---|
| POST | `/defend/loop-t/mine` | `{train_run_id, gdev_run_id, family}` → candidates |
| GET | `/defend/rules/drafts` | `{status?}` |
| POST | `/defend/rules/approve/{draft_id}` | HITL |
| POST | `/defend/rules/reject/{draft_id}` | `{note}` |
| POST | `/defend/rules/edit/{draft_id}` | `{when}` then **re-backtest**; if fail, stay proposed with `verdict` |
| GET | `/defend/rules/fp-inbox` | live rules with genuine FPR > 0.005 on G-dev |
| POST | `/defend/rules/fp-propose` | `{rule_id}` extra AND from a tree on genuine-fire rows; same queue `source=loop_t_fp` |

#### 7.6 Tests (`tests/test_loop_t.py`) — all required

- Tiny synthetic FN matrix → at least one parsed predicate.
- Jaccard duplicate rejected.
- All-APP-flag candidate cannot be produced (those cols are excluded from the tree).
- High-FPR candidate rejected.
- Approve writes YAML; rollback restores.
- `mine_fn_rules` does not read `make-gtest` / seed 43 path (patch `run_paths` or pass explicit dirs).
- Draft `when` unchanged after a fake LLM that returns a different `when`.

**Stop-gate:** a draft cannot appear in `load_v0_rules()` until `approve`.

---

### Ticket 8 — Isolation Forest (SHOULD, after T5)

**New** `packages/eval/iso_check.py`. Stamp-free cols locked:

`account_age_days, payee_history_count, amount_vs_p30, fan_in_1h, fan_out_1h, fan_in_unique_payers_1h, burst_velocity, is_new_payee, is_new_device`

(encode bools as 0/1). **Exclude** APP flags, invoice flags, `rule__*`.

Train on `inner_fit` genuine only. Infer only if `pred_family==normal` AND `pmap["normal"] >= 0.95`. Brake: if action is `allow` and `iso_notify`, upgrade to `notify` + reason `iso_anomaly`. Never downgrade mule/hold/decline.

If `iso_genuine_notify_rate > 0.05` on inner-val: leave `isolation_forest.enabled_default=false` and do not call IF in `score_run`.

**Do not** change coverage map named_gaps.

---

### Ticket 9 — Isotonic + ECE (SHOULD)

Stage 1: `IsotonicRegression` on inner-val `fraud_score` vs binary y. Apply before comparing to `op_threshold` **or** freeze threshold on calibrated scores (locked: **fit threshold on calibrated inner-val scores**).  
Stage 2: skip family if `n_pos < 50`. Renormalize.  
ECE: 10-bin reliability on G-dev 44 for walkthrough; inner-val for CI.

---

### Ticket 10 — Cluster bootstrap + permutation (SHOULD)

Permutation on inner-val, `scoring="neg_log_loss"`, `n_repeats=10`, `random_state=42`. Replace correlation `_top_features`.  
Bootstrap: resample **payee** ids for mule/invoice rows, **payer** ids otherwise; `n_resamples=200` in tests, 1000 in submission Makefile note. Write `bootstrap_ci[fam].low/high`.

Do not drop features from G-test importances.

---

## 8. What not to touch

- Identify LangGraph, catalog HITL, Scout.
- Injector math except if a test proves Ticket 1 broke fidelity (then fix replay only).
- `packages/sim/injectors.py` stub — do not train from it.
- Brake order except the IF notify insert (T8).
- G-test seed 43 usage for mining/HPO.
- Adding `optuna` to default (non-dev) dependencies if it makes `validate-all` install huge — keep in `dev` extra; Makefile `defend-tune` uses the venv that already has sklearn.

---

## 9. Test matrix the agent must keep green

**Always (every ticket):**  
`pytest tests/test_sim_export.py tests/test_sim_inject.py tests/test_eval_fit.py tests/test_eval_split.py tests/test_eval_loop_m.py tests/test_eval_rules_brake.py tests/test_policy_coverage.py -q`  
(adjust names if files differ — glob `tests/test_eval*.py tests/test_sim*.py tests/test_policy*.py`).

**After T7:** `pytest tests/test_loop_t.py -q`

**E2E (small, not Plan 08):** generate n=16–20 full mix seed 42 → fit → score; generate seed 43 n=same → score_run; assert `n_pos` keys exist. Invoice family may be `not_comparable` on n=20 — that is OK.

**Plan 08:** human/Makefile, not default pytest.

---

## 10. Kill switches (if this, skip that)

| If | Then |
|---|---|
| T1A/T1B red | Do not quote invoice AP or unique-fan-in. Stop before T5. |
| Loop M `not_comparable` on n=20 | Expected. Do not fake improvement. Still ship T7. |
| APP AP collapses without flags | Write ablation. Do not copy flags onto genuine rows. |
| Loop T skipped insufficient_fn on n=20 G-dev | Expected. Prove pipeline with a **fixture** tree in `test_loop_t.py`, and run mine on Plan 08 G-dev for the demo. |
| IF genuine notify > 5% | Keep IF off. |
| Optuna > 10 min on laptop | `n_trials=10` or skip T5. |
| Clock dying | Ship T1–T4, T6, T7. Skip T5/T8/T9/T10. |

---

## 11. Doc map (what each file is for)

| File | Role after this lock |
|---|---|
| **This file** | How to implement. Ticket numbers. Constants. |
| `defense-architecture.md` | Why the system looks like this. Must not contradict this file. |
| `defense-why.md` | Judge-facing rationale. Loop T is MUST, not optional. |
| `defend-peak-handoff.md` | File inventory. Tickets 7–8 there are **stale** (Loop G). Ignore them; use this file. |
| `defend-dev-keepinminds.md` | PR checklist. |
| `VALIDATION.md` | Metric definitions / G1–G7. |
| `Docs/plans/architecture-defense-doc.md` | Judge-facing Defend architecture note (stack, mermaid, metrics). |
| `Docs/plans/defend-test-tracker.md` | Unit / ML / HTTP / Generate→Defend test matrix. |

---

## 12. Agent working agreement

1. Execute **one** ticket per change-set.
2. If a constant is in §1, do not pick a “better” number.
3. If two docs disagree, follow **this file** and patch the other doc in the same change-set.
4. Do not add endpoints, models, or loops not listed.
5. Do not use G-test 43 for decisions.
6. LLM cannot emit `when`.
7. Done means tests in that ticket’s list are green, not “looks plausible.”
8. Section 13 overrides earlier sections of this file.

---

## 13. Locked addendum (overrides anything above)

Grok senior review 2026-08-28. If an earlier section disagrees, **this section wins**.

1. **`features.json` is MERGE-only.** Do not replace the file. Keep existing `hang_guard_seconds_1k`, `app_flag_cols`, `split`, `rule_hit_prefix`, `class_weight`, `objective`, `note`. Add new keys from §1 beside them.

2. **Loop M run_ids stay as coded:** `{run_id}__extra-{family}`, `{run_id}__gtest`, `{run_id}__loopm-train` in `packages/eval/loop_m.py`. Do not invent `{train_run_id}-lm`.

3. **G-test scoring:** `score_run(..., all_rows=True)` always for `make-gtest`. Default `all_rows=False` is diagnostic outer-eval only.

4. **G-test `app_ablation`:** do not re-fit on seed 43. Copy `app_ablation` from the champion `metrics.json` and set `app_ablation_source: "champion_fit"`. Ticket 2: those keys exist on the G-test JSON via copy; `n_pos` is computed on G-test rows.

5. **After T3, `fit_champion` metrics:** `ap_by_family` on the outer eval is diagnostic. Also write `diagnostic_ap_by_family` as a duplicate. Walkthrough headline is only the G-test `score_run(all_rows=True)` blob (`world_seed: 43`). `_metrics_pass` may still use diagnostic AP for CI sanity.

6. **YAML versioning:** `v0_rules.yaml` remains a YAML **list**. Never add `_meta`. Version only via `data/rules/versions.json` plus copy to `data/rules/backups/v0_rules.v{n}.yaml`. One backup path only.

7. **G-dev mine vs gate:** On seed-44 events, split by `event_ts`: first 70% = `gdev_mine` (fit tree), last 30% = `gdev_gate` (FPR + incremental recall). Event_ids must be disjoint. If `gdev_gate` genuines < 30, return `insufficient_gate`.

8. **Caught / FN:** `detection_fn` = family row AND NOT (`score >= op_threshold` OR any `hard_flag` hit). This is not Brake-action FN. Include `loop_t_catch_split` `{score_only, hard_flag_only, both}` in metrics.

9. **Tree → `when`:** sklearn left = `field <= {thr:.6g}`; right = `field > {thr:.6g}`. Bool 0/1 with thr in (0,1): left `field == false`, right `field == true`. Every clause must pass `parse_predicate` (`==|!=|>=|<=|>|<`). Path length > 4 → drop leaf.

10. **HITL HTTP this sprint (four only):** `POST /defend/loop-t/mine`, `GET /defend/rules/drafts`, `POST /defend/rules/approve/{draft_id}`, `POST /defend/rules/reject/{draft_id}`. No edit HTTP. No fp-propose HTTP.

11. **Optuna:** `binary_AP - 10 * max(0, genuine_fp - 0.01)`. Soft penalty. Not min-family AP. Not hard prune.

12. **Loop T only after frozen `op_threshold`.** T5/T9 changing scores invalidates drafts — re-mine. Do not approve drafts whose `recipe_hash` ≠ current recipe.

13. **sklearn** stays in `[dev]` extra. Run tests in that env.

14. **Sequence:** T1A→T1B→T2→T3→T4→T6→T7, then T5 if time, then T8→T9→T10. Clock dying: stop after T7.

15. **`loop_t.fold: gdev44`** means the G-dev **world**, not a value of `assign_folds`.
