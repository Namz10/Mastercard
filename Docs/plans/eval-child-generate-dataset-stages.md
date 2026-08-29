# Child 2 — generate-dataset Stages 0–3b

**Parent:** [Master validation protocol](../../.cursor/plans/external_holdout_validation_64f9d54e.plan.md)  
**Prerequisite:** [`eval-child-preval-blockers.md`](eval-child-preval-blockers.md) merged and green. **Gate:** `pytest tests/test_validation_protocol.py -q` must pass before first headline `defend-gtest`. **Do not photograph seed 43 before that.**  
**n_pos after Stage 1:** [`eval-child-npos-scale.md`](eval-child-npos-scale.md)  
**Stage 4:** [`eval-child-external-dataset.md`](eval-child-external-dataset.md)

**This child is operator SOP.** No new packages, no Stage orchestration module, no new Makefile product targets. Use existing Make + Python/API.

Terminology: **generate-dataset** only. Never “vault”.

---

## Runners (what exists)

| Step | Command | Notes |
|---|---|---|
| Train world 42 | `make generate-scale` | [`Makefile`](../../Makefile): `run_id='make-scale-fullmix'`, 2400×120×90, `world_seed=42`, asserts `event_count>50000` and `fidelity.pass` |
| Fit Stage 1 | `make defend-fit` | `fit_champion('make-scale-fullmix', world_seed=42)` |
| G-dev 44 | `make defend-gdev` | Generates `make-gdev` at sidecar n, then `score_run(..., all_rows=True)` |
| G-test 43 | `make defend-gtest` | Generates `make-gtest` seed 43 at sidecar n, then scores. **Headline.** After Child 1, persists JSON and enforces freeze |
| Optuna | `POST /defend/tune` or `tune_champion` | **No Make target** |
| Loop M | `POST /defend/loop-m` | Makefile `defend-loop-m` is echo-only |
| Loop T | `POST /defend/loop-t/mine` + approve; or `run_remediation_cycle` | `defend-remediate` is echo-only. Kill switch: `remediation.orchestrator_enabled` in `features.json` |

Scale pin: [`packages/config/scale.py`](../../packages/config/scale.py). Split: [`packages/eval/split.py`](../../packages/eval/split.py). Fit/score: [`packages/eval/fit.py`](../../packages/eval/fit.py). Loop M: [`packages/eval/loop_m.py`](../../packages/eval/loop_m.py). Loop T: [`packages/eval/loop_t.py`](../../packages/eval/loop_t.py), [`packages/eval/loop_t_orchestrator.py`](../../packages/eval/loop_t_orchestrator.py).

---

## STAGE 0 — Worlds at frozen scale

**Required. Once. Do not scale up preemptively** (no extra customers “just in case” mule is thin).

| World | `world_seed` | `run_id` | Scale |
|---|---|---|---|
| Train | 42 | `make-scale-fullmix` | 2400 × 120 × 90 |
| G-dev | 44 | `make-gdev` | Copy n from train sidecar |
| G-test | 43 | `make-gtest` | Copy n from train sidecar |

`make defend-gdev` / `defend-gtest` already copy `n_customers` / `n_merchants` / `sim_days` from `data/runs/make-scale-fullmix/sidecar.json`. If sidecar is missing they default to 2400×120×90 — **fail the checklist** if you scored against a silent default after a partial generate.

`pin=True` on those Makefile paths.

Independent worlds: [`packages/sim/runner.py`](../../packages/sim/runner.py) `run_population` per seed; parquet bytes differ (audit pass). `event_id` strings **overlap** across worlds (`evt-0000000001` in each). Do not claim global id disjointness.

### 0.1 Split protocol (generate-dataset)

- `split.parquet` has `event_ts`.
- Protocol: `time_cut_2_3_plus_entity_holdout`.
- Inner-val: last 20% of **outer train** calendar (`inner_folds_from_train`). Not shuffle.
- **Fail** if published split used `sklearn.model_selection.train_test_split(shuffle=True)` on the fit path.

### 0.2 Train schema

**Allowlist (X + y)** — SSOT §3.1 / `TRAIN_ALLOWLIST`:

`rail`, `kyc_tier`, `account_age_days`, `payee_history_count`, `amount_vs_p30`, `fan_in_1h`, `fan_out_1h`, `fan_in_unique_payers_1h`, `is_new_payee`, `is_new_device`, `burst_velocity`, APP four flags, invoice booleans, `label_family`. `rule__*` bits appended in fit.

**Denylist** (any present = invalid generate-dataset): `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, `transcripts`, `is_authorized_push`, `economic_class`, `label_class`, `gstin`, `payload`.

Enforced: [`packages/sim/export.py`](../../packages/sim/export.py) `assert_train_schema`, `assert_no_x_leak`.

Fraud-rate band: lab oversample **0.5–3.5%** on 42 (Plan 08 mix). Mix shares in [`packages/sim/inject/mix.py`](../../packages/sim/inject/mix.py): mule 0.40, identity_burst 0.25, ato 0.05, app_fraud 0.20, invoice_fraud 0.10.

**Practical order (Stage 0 only):** `make generate-scale` (world 42). Do **not** generate 43/44 until Stage 1. See [Sequence](#sequence-one-page) for full pipeline.

**Gate:** world 42 at 2400×120×90; split + denylist pass; Child 1 pytest green → Stage 1.

---

## STAGE 1 — Base HGB

**Required.**

### 1.1 Fit

`make defend-fit`.

- Multiclass HGB, `y = label_family` (6 classes). Family AP is a metric, not five models.
- Outer train seed 42. Recipe default hyperparams. `early_stopping: false`.
- `op_threshold` from **inner_val** at `operating_point_fpr = 0.01` only.

IF: `enabled_default` must already be **false** (Child 1). Do not turn it on for the headline run.

### 1.2 Freeze

Record `model_freeze_id`, `recipe_hash`, default `best_params`, `train_fingerprint = make-scale-fullmix` (no Loop M extras). **Do not** later write Optuna into this `model_run_id`.

### 1.3 Score once (headline)

`make defend-gtest` **or** generate `make-gtest` then `score_run('make-gtest', model_run_id=<stage1>, all_rows=True)` if the world already exists.

**G-test `all_rows` is the photograph.** Eval-fold can show `n_pos=0` for ato/identity; quoting those fold APs as headline is a protocol fail.

### 1.4 Required fields (every generate-dataset headline JSON)

After Child 1 the persisted file must include:

- `protocol`: `g_test_full_population`
- `inner_val_protocol`: `last_20pct_train_calendar`
- `model_freeze_id`, `recipe_hash`, `gtest_opened_at`
- `ap_by_family` + `n_pos` per family including `normal`
- `not_comparable` where `n_pos < 30` (`n_pos_not_comparable_below`)
- `binary_ap`, `precision_at_op`, `recall_at_op`, `f1_at_op`, `confusion_matrix`
- `genuine_fp` on `label_family == normal`
- `tpr_at_fpr` keys `"0.001"`, `"0.005"`, `"0.01"`
- `app_ablation` with `app_ablation_source: champion_fit` (copied from seed-42 diagnostic — **do not** slide this as “G-test ablation”)
- `mule_entity_recall`
- `action_histogram` (+ `cost_sketch`)
- `authgate_ms` p50/p99
- `diagnostic_*` from seed-42 G-eval if present on champion metrics — store, **do not lead**

### 1.5 Loop M family pick (G-dev 44 only) — after Stage 1 photograph

Run **after** Stage 1 G-test photograph and n_pos gate (see [Sequence](#sequence-one-page)). Score on G-dev only — never seed 43.

```bash
make defend-gdev   # generates make-gdev + scores; capture ap_by_family / n_pos from stdout or models/make-scale-fullmix metrics
```

**Pick rule:** among fraud families (`!= normal`), choose **lowest** `ap_by_family` on G-dev `all_rows` among families with `n_pos >= 30`. Tie-break: lower `n_pos` first (thinner support = weaker estimate), then alphabetical family name. If **no** family has `n_pos >= 30`, set `target_family: null`, document `not_comparable`, Loop M may still run if you justify a family — default is skip Loop M target.

Write `data/validation/stage1/loop_m_family_pick.json` (canonical path):

```json
{
  "family_chosen_from_slice": "gdev44",
  "target_family": "<family>",
  "gdev_ap_by_family": {},
  "n_pos": {},
  "chosen_at_stage": 1,
  "stage1_model_freeze_id": "<hex>"
}
```

**Forbidden values** for `family_chosen_from_slice`: `gtest`, `43`, anything derived from Stage 2/3 G-test. Code already rejects `gtest`/`43` in [`loop_m.py`](../../packages/eval/loop_m.py). This SOP is stricter than the code: **do not** use `inner_val` or `diagnostic` for the **submission** pick even though the API allows them.

Read-only after Stage 1. Optuna must not change the pick.

### 1.6 n_pos gate (two-pass)

**Early proxy (before Loop M):** read `models/make-scale-fullmix/metrics.json` → eval-fold `n_pos` by family. If mule `n_pos < 15` on eval fold, the G-test will almost certainly be `not_comparable`. Bump `sim_days` / mule share, regenerate, refit, restart before touching Loop M or Optuna.

**Confirmation (after Photography Day):** read `models/make-scale-fullmix/gtest_score.json` → `n_pos`. If 15–29: `not_comparable`; document and optionally bump. Write `data/validation/npos_gate.json`. See [`eval-child-npos-scale.md`](eval-child-npos-scale.md) for the bump protocol.

If you regenerate worlds you must refit and restart from Stage 1. All Loop M / Optuna work is invalidated.

**Gate:** early-proxy check done and no show-stopper → proceed to Loop M. Confirmation happens on Photography Day (see §Sequence).

---

## STAGE 2 — Optuna hyperparameter tune (required as a recorded stage)

**Required stage.** You always produce a Stage 2 artifact — even when the search itself is skipped.

### 2.0 Prerequisites

- `data/validation/stage3/loop_m_result.json` exists (**Loop M completed first**).
- `data/validation/stage1/loop_m_family_pick.json` exists.
- n_pos proxy checked (eval fold); no regeneration triggered.
- `pytest tests/test_validation_protocol.py -q` still green.

> **Why not Stage 1 G-test first?** `fit_champion` refuses to overwrite `models/make-scale-fullmix/` after its photograph. Loop M calls `fit_champion("make-scale-fullmix")` — so Loop M must complete before the Stage 1 photograph. Optuna writes to a different `model_run_id` and has no conflict. All G-test photographs happen together on Photography Day (see §Sequence). Stage 2 Optuna only reads seed-42 train parquet; it never opens seed 43.

### 2.1 What Optuna does (code truth)

| Item | Value |
|---|---|
| Data opened | **Only** `make-scale-fullmix` train parquet (seed 42); inner_fit for fit, inner_val for objective |
| Never opened | seed 43 (`tune_champion` raises), seed 44, `make-gtest` |
| Search space | `max_depth` ∈ {2,3,4,5}; `learning_rate` log-uniform [0.02, 0.2]; `max_iter` ∈ [40, 200] |
| Trials / timeout | `n_trials=40`, `timeout_seconds=600` from [`models/features.json`](../../models/features.json) (`n_trials_ci=10`, `timeout_ci=60` for CI) |
| Objective | `binary_AP(inner_val) - 10.0 * max(0, genuine_fp - 0.01)` at `operating_point_fpr=0.01` |
| Skip gate | If inner_val fraud `n_pos < 50`: writes recipe defaults to `best_params`, sets `optuna_skipped_small_n: true` — **still run tune into new dest** |
| After study | `fit_champion` refits **full outer train** with tuned params; **recomputes** `op_threshold` on that model’s inner_val → new `model_freeze_id` |
| Writes | `models/make-scale-fullmix-stage2/best_params.json`, `champion.joblib`, `metrics.json` |

**Locked IDs:** train `run_id` = `make-scale-fullmix`; Stage 2 `model_run_id` = `make-scale-fullmix-stage2`. Stage 1 directory stays immutable.

### 2.2 Run tune (distinct `model_run_id`)

Child 1 **refuses** in-place tune/score on `models/make-scale-fullmix/` after its G-test photograph.

**Option A — Python (no API needed):**

```python
from packages.eval.fit import tune_champion

out = tune_champion(
    "make-scale-fullmix",
    world_seed=42,
    dest_run_id="make-scale-fullmix-stage2",
)
print(out["optuna_skipped_small_n"], out["best_params"])
# DO NOT call score_run here — G-test photograph happens on Photography Day
```

**Option B — API** (`make api` in another terminal):

```bash
curl -s -X POST http://localhost:8000/defend/tune \
  -H 'Content-Type: application/json' \
  -d '{"run_id":"make-scale-fullmix","dest_run_id":"make-scale-fullmix-stage2"}'
```

**Do not** use `make defend-gtest` for Stage 2 — it hardcodes `model_run_id=make-scale-fullmix`. The Stage 2 G-test photograph is `score_run("make-gtest", model_run_id="make-scale-fullmix-stage2", all_rows=True)` executed on Photography Day.

### 2.3 Stage 2 artifacts

| File | Purpose |
|---|---|
| `models/make-scale-fullmix-stage2/best_params.json` | Study result + `optuna_skipped_small_n` |
| `models/make-scale-fullmix-stage2/gtest_score.json` | **Headline** photograph (one call only) |
| `data/validation/stage2/delta_vs_stage1.json` | Operator-written delta (see template below) |
| `data/validation/stage2/stage3_parent.json` | Which model Loop M uses |

**Delta template** (`data/validation/stage2/delta_vs_stage1.json`):

```json
{
  "stage1_model_run_id": "make-scale-fullmix",
  "stage2_model_run_id": "make-scale-fullmix-stage2",
  "optuna_skipped_small_n": false,
  "binary_ap_delta": 0.0,
  "genuine_fp_delta": 0.0,
  "ap_by_family_delta": {},
  "noise_chase_flags": [],
  "verdict": "improved | equal | regressed | skipped_search"
}
```

Noise-chase flags (document if true): `max_depth` at 2 or 5; `learning_rate` at 0.2; `max_iter` at 200.

### 2.4 Record `stage3_parent` (retrospective — written after Photography Day)

`stage3_parent` is **always 1** in this protocol. Loop M already ran from `models/make-scale-fullmix/` (Stage 1) before Photography Day. Code does not accept `parent_model_run_id` on `run_loop_m`. Write this after you have both G-test JSONs so the delta is filled in:

```json
{
  "stage3_parent": 1,
  "parent_model_run_id": "make-scale-fullmix",
  "reason": "Loop M pre-dates G-test photographs; Stage 1 is always parent. Stage 2 delta recorded below."
}
```

If Stage 2 G-test `binary_ap` beats Stage 1 and `genuine_fp` is not worse by > 0.02, note it in `delta_vs_stage1.json` with `"verdict": "stage2_would_have_been_preferred"`. No code change needed; Loop M result stands.

**Gate:** `best_params.json` + Loop T draft outcome → Photography Day.

---

## STAGE 3 — Loop M (required)

Family **only** from Stage 1 pick file.

```
POST /defend/loop-m
{
  "run_id": "make-scale-fullmix",
  "miss_family": "<target_family>",
  "family_chosen_from_slice": "gdev44",
  "n_customers": 2400,
  "n_merchants": 120,
  "sim_days": 90,
  "pin": true
}
```

Scale fields: pass the sidecar n so extras generate at the same 2400×120×90 (or post-npos `sim_days`). `pin=true`.

**Headline row:** Loop M scores `{run_id}__gtest` internally (SSOT §13.2). For the comparison table, also persist Loop M response to `data/validation/stage3/loop_m_result.json`. If the table requires `make-gtest` parity, run one additional `score_run('make-gtest', model_run_id='<loopm_model_run_id>', all_rows=True)` and archive `models/<loopm_model_run_id>/gtest_score.json`.

Mechanics (already coded):

- Extra generate-dataset rows: `train_seed + 10007`.
- Cap ≤ 15% of original train length; truncation in `_write_augmented`.
- `label_source = loop_m`; extras never written into `make-gtest`.
- Extra event ids ∩ G-test event ids = ∅.
- Refit same hyperparams/features as parent; new `model_run_id` = `{run_id}__loopm-train` (e.g. `make-scale-fullmix__loopm-train`).
- Scores **`{run_id}__gtest`** before/after (synthetic seed-43 world), **not** `make-gtest`. Different population from Stages 1/2/3b — label clearly in comparison table.

**Ordering invariant:** `run_loop_m` calls `fit_champion("make-scale-fullmix")` on the parent as part of its before/after comparison. After the Stage 1 G-test photograph, `fit_champion` refuses to overwrite that `model_run_id` (Child 1 guard). Therefore Loop M **must run before Photography Day** — this is enforced by the sequence in §Sequence. The parent model directory (`models/make-scale-fullmix/`) may have joblib bytes rewritten by Loop M; that is expected and does not affect G-test integrity (`model_freeze_id` is derived from features + params + threshold, not joblib bytes).

### Verdict fields

- Target family `ap_verdict`: `improved | equal | regressed | not_comparable` (`ap_equal_eps = 0.05`; `not_comparable` if G-test `n_pos < 30` for that family)
- Other families: relative AP drop ≤ 5% or document exception
- `genuine_fp` ≤ parent + **0.02**
- `catalog_solved`: **false** always (hardcoded)

Honest `regressed` / `not_comparable` is a **valid** Stage 3 result.

**Gate:** Stage 3 G-test JSON (after) → Stage 3b. Do not skip 3b.

---

## STAGE 3b — Loop T (required)

Mine on G-dev **only**. Never seed 43. Never inner_val.

- **Family:** `target_family` from `data/validation/stage1/loop_m_family_pick.json`.
- `POST /defend/loop-t/mine` with `train_run_id` + `gdev_run_id='make-gdev'` + family (or orchestrator).
- Gate FPR / incremental recall on G-dev; `rule_promote_genuine_fpr_eps = 0.002` (do not confuse with Loop M `0.02`).
- Approve: `GET /defend/rules/drafts` → `POST /defend/rules/approve/{draft_id}`.
- [`FORBIDDEN_RULE_FIELDS`](../../packages/policy/rules.py): no `technique_id`, `injector_id`, `world_seed`, etc.
- Drafts stay `draft` until HITL approve. Never auto-promote.
- After approve: live YAML has the rule. **Do not refit** GBDT.
- `live_rules_digest` = SHA-256 of live `v0_rules.yaml` bytes at approve time.
- After approve (or confirming zero candidates), record `live_rules_digest`.
- The Stage 3b G-test photograph is taken on Photography Day:

```python
from packages.eval.fit import score_run
# Live rules are loaded automatically from v0_rules.yaml by score_run
score_run("make-gtest", model_run_id="make-scale-fullmix__loopm-train", all_rows=True)
# → models/make-scale-fullmix__loopm-train/gtest_score.json
```

This call is included in the Photography Day sequence — it must be the **first and only** `make-gtest` photograph for `make-scale-fullmix__loopm-train`. Rules change rule-bit scores but do not change `model_freeze_id`; a second call returns cached JSON. Ensure rules are approved *before* Photography Day starts.

If mine produces zero candidates that pass the gate: `loop_t_drafts_proposed: 0`. Proceed to Photography Day with the current `v0_rules.yaml`. Stage 3b score equals Stage 3 (rules unchanged). **Completes 3b.**

Orchestrator off (`remediation.orchestrator_enabled: false`): still run **manual** mine + record the empty-or-draft outcome. 3b is not optional.

**Gate:** Live rules approved (or `loop_t_drafts_proposed: 0` recorded) → Photography Day → Stage 4 ([`eval-child-external-dataset.md`](eval-child-external-dataset.md)).

---

## Sequence (authoritative — refit-then-photograph)

### Why this order

`fit_champion` refuses to overwrite any `model_run_id` after its G-test photograph (Child 1 guard). `loop_m.py` calls `fit_champion(run_id)` on the parent — so Loop M **must run before** the parent's G-test photograph. The solution: complete all training/tuning/rule-mining first, then photograph G-test for every model in one pass ("Photography Day"). `make-gtest` is never touched until Photography Day.

```
# ── GATE ──────────────────────────────────────────────────────────────────────
pytest tests/test_validation_protocol.py -q     # Child 1 must be green

# ── STAGE 0 ───────────────────────────────────────────────────────────────────
make generate-scale                             # world 42, frozen 2400×120×90
                                                # artifact: data/runs/make-scale-fullmix/

# ── STAGE 1 FIT ───────────────────────────────────────────────────────────────
make defend-fit                                 # fits models/make-scale-fullmix/
                                                # do NOT touch this dir after Loop M starts

# ── G-DEV + FAMILY PICK ───────────────────────────────────────────────────────
make defend-gdev                                # world 44 + score on Stage 1 champion
# Read models/make-scale-fullmix/metrics.json eval_ap to get n_pos proxy
# If mule n_pos < 15 on eval fold → bump sim_days/mule share, regenerate, refit, restart
# Write: data/validation/stage1/loop_m_family_pick.json

# ── STAGE 3 LOOP M (before G-test) ────────────────────────────────────────────
POST /defend/loop-m  {                          # refits parent + augmented; photographs __gtest
  "run_id": "make-scale-fullmix",
  "miss_family": "<from pick file>",
  "family_chosen_from_slice": "gdev44",
  "n_customers": 2400, "n_merchants": 120, "sim_days": 90, "pin": true
}
# Save: data/validation/stage3/loop_m_result.json

# ── STAGE 2 OPTUNA (before G-test) ────────────────────────────────────────────
from packages.eval.fit import tune_champion
tune_champion("make-scale-fullmix", dest_run_id="make-scale-fullmix-stage2")
# artifact: models/make-scale-fullmix-stage2/  (no G-test yet)

# ── STAGE 3b LOOP T (before G-test) ───────────────────────────────────────────
POST /defend/loop-t/mine  train_run_id=make-scale-fullmix  gdev_run_id=make-gdev  family=<pick>
GET  /defend/rules/drafts                       # review candidates
POST /defend/rules/approve/{draft_id}           # HITL — if any pass gate; else record 0 candidates
# live_rules_digest = sha256(data/rules/v0_rules.yaml)

# ── PHOTOGRAPHY DAY (G-test; every model, once each) ──────────────────────────
# NOTE: make defend-gtest hardcodes model_run_id=make-scale-fullmix (Stage 1 only).
# Use Python score_run for Stages 2 and 3b.

from packages.eval.fit import score_run

# Stage 1
score_run("make-gtest", model_run_id="make-scale-fullmix", all_rows=True)
# → models/make-scale-fullmix/gtest_score.json

# Stage 2
score_run("make-gtest", model_run_id="make-scale-fullmix-stage2", all_rows=True)
# → models/make-scale-fullmix-stage2/gtest_score.json

# Stage 3b (Loop M augmented champion + live rules)
score_run("make-gtest", model_run_id="make-scale-fullmix__loopm-train", all_rows=True)
# → models/make-scale-fullmix__loopm-train/gtest_score.json

# ── N_POS GATE (confirm from G-test all_rows) ─────────────────────────────────
# Read models/make-scale-fullmix/gtest_score.json → metrics.n_pos
# If mule < 30: record not_comparable; optionally restart (bump → regenerate → refit → redo)
# Write: data/validation/npos_gate.json  {"mule_n_pos": N, "comparable": bool, "action": "proceed|bump"}

# ── DELTA + STAGE 3_PARENT ────────────────────────────────────────────────────
# Compare Stage 1 vs Stage 2 gtest_score.json; record delta
# stage3_parent is ALWAYS 1 (Loop M already ran from Stage 1)
# Write: data/validation/stage2/delta_vs_stage1.json

# ── STAGE 4 ───────────────────────────────────────────────────────────────────
# Fill Docs/validation/stage4-external-block.md
# (blocked_no_adapter; mapping + citations required)
```

### Gate artifacts

| Step | Required files before proceeding |
|---|---|
| Start Stage 1 fit | `data/runs/make-scale-fullmix/` + sidecar 2400×120×90; pytest green |
| Start Loop M | `data/validation/stage1/loop_m_family_pick.json`; Stage 1 `metrics.json` |
| Start Optuna | `data/validation/stage3/loop_m_result.json` |
| Start Loop T | `models/make-scale-fullmix-stage2/best_params.json` |
| Photography Day | Loop T draft outcome recorded; live rules approved or `loop_t_drafts_proposed: 0` |
| Write-up | All three `gtest_score.json` files + `npos_gate.json` + `delta_vs_stage1.json` |
| Stage 4 | `Docs/validation/stage4-external-block.md` |

Do **not** run tune between Stage 1 fit and Stage 1 G-test on the **same** freeze. Do not photograph 43, then tune **in place**, then photograph 43 again.

---

## Claims

**Allowed:** Stages 1–3b on seed 43 after Child 1; family from 44; Loop M before/after same `gtest_id`; `optuna_skipped_small_n` as Stage 2; empty Loop T as completed 3b.

**Forbidden:** Loop M family from G-test; HPO on 43/44; skipping Stage 2 or 3b; leading with diagnostic G-eval AP; calling `app_ablation` a G-test result; `catalog_solved: true`.
