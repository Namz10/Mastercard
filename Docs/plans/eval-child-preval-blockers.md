# Child 1 — Pre-validation blockers (`model_freeze_id`)

**Parent:** [Master validation protocol](../../.cursor/plans/external_holdout_validation_64f9d54e.plan.md)  
**Audit:** [`evaluation-validity-audit.md`](evaluation-validity-audit.md) (BLOCKER Check 1 / Check 8; RISK metrics / IF / histogram)  
**SSOT:** [`defend-execution-ssot.md`](defend-execution-ssot.md) §1–§2  
**This is the only code ticket in the validation workstream.** It is scientific integrity, not a product feature (no adapter, no new package, no scale bump).

**MUST land before any headline `score_run(..., all_rows=True)` on seed 43.** Stage 1 then Stage 2 Optuna on the same G-test population is **invalid** until this ships.

**Do not:** bump `2400×120×90`; add SAML-D/Xente code; add Makefile Stage-4 targets; change PSI constants in this ticket (align later or update VALIDATION.md — not a G-test BLOCKER).

---

## Why (was broken; Child 1 fixes)

| Was true (audit) | Fix in Child 1 |
|---|---|
| `_recipe_hash` = features.json only | Unchanged; **`model_freeze_id`** is now the G-test key |
| G-test could rescore after Optuna on same dir | `dest_run_id` + freeze mismatch refuse + early cache return |
| Missing binary metrics / histogram on photograph | `binary_ap`, P/R, confusion matrix, `action_histogram` persisted |
| IF defaults wrong | `enabled_default: false`, `contamination: 0.01` |

If G-test was already opened during development: treat those numbers as **exploratory**. After this child: new freeze ids, photograph on 43 if that freeze was never opened; if the **same** freeze was peeked, use seed **45**.

---

## Scope (do this, nothing else)

### 1. `model_freeze_id`

Define:

```
model_freeze_id = SHA-256(
  features.json canonical bytes
  + canonical JSON of best_params used in champion.joblib
  + canonical op_threshold
)
```

- Stage 1 (no Optuna): `best_params` = recipe defaults (`max_depth`, `learning_rate`, `max_iter`, `random_state`, `early_stopping`).
- After Optuna: the `best_params.json` payload that was actually fit.
- `op_threshold` is the inner-val threshold stored on the champion (not G-eval, not G-test).
- Persist `model_freeze_id` on `model_manifest.json`, `metrics.json`, `gtest_protocol.json`, and G-test score JSON.
- Keep `recipe_hash` as today (features-only) for existing tests; **G-test policy keys on `model_freeze_id`**.

Canonicalization: sorted keys, stable float repr, UTF-8. Same inputs ⇒ same hex. Test it.

### 2. Refuse rescore 43 on freeze mismatch

On `score_run(..., all_rows=True)` when sidecar `world_seed==43`:

1. Load `models/{model_run_id}/gtest_protocol.json`.
2. Compute current `model_freeze_id` from the champion being scored.
3. If protocol has `gtest_opened_at` and stored `model_freeze_id` **equals** current: **refuse a second photograph** of the same freeze (or return the persisted score JSON if you implement idempotent read — do not recompute a new headline). Preferred: refuse with a clear error pointing at the existing `gtest_score.json`.
4. If protocol has `gtest_opened_at` and stored `model_freeze_id` **differs**: **refuse**. Message: params/threshold/features changed after G-test open; use a **new** `model_run_id` for the new freeze, or `make-gconfirm` seed 45 if the operator peeked and mutated in place.
5. If no `gtest_opened_at`: record `gtest_opened_at`, `model_freeze_id`, `recipe_hash`, `gtest_run_id`, `world_seed`. This is the first photograph of **this** freeze on **this** `model_run_id`.

**Loop M exception (allowed by protocol):** [`loop_m.py`](../../packages/eval/loop_m.py) scores the same `gtest_id` twice with **different** `model_run_id` (parent vs augmented). Each directory has its own `gtest_protocol.json`. Do **not** add a global “seed 43 may only be opened once in the lab” lock. Same `gtest_id`, different freeze / different `model_run_id` is the closed-loop.

**Stage 2 implication:** `tune_champion` must **not** overwrite the Stage 1 directory after that directory’s G-test. Operator SOP: copy or fit tuned champion to a new `model_run_id`. If you add a `dest_run_id` argument, keep it minimal. Do not build a stages framework.

### 3. Persist G-test score JSON

Write the full `score_run` result (metrics **and** `action_histogram`, plus `cost_sketch` already inside metrics) to a stable path, e.g.:

- `models/{model_run_id}/gtest_score.json`, and/or
- `data/runs/make-gtest/score.json` keyed by `model_run_id` / `model_freeze_id`

Update [`Makefile`](../../Makefile) `defend-gtest` so the score is **written**, not only printed. No new product target name required; extend the existing `-c` snippet.

### 4. Binary fraud fields on the photograph

On G-test `all_rows` metrics (and preferably all `score_run` paths for consistency):

| Field | Definition |
|---|---|
| `binary_ap` | Average precision, `y = (label_family != normal)` vs `scores` |
| `precision_at_op` | Precision at `op_threshold` |
| `recall_at_op` | Recall at `op_threshold` |
| `f1_at_op` | Already present; keep |
| `confusion_matrix` | `tn, fp, fn, tp` at `op_threshold` on the binary label |

`genuine_fp` stays mean(`score >= thr` on `label_family == normal`) — not `1 - precision`.

### 5. Persist `action_histogram`

Today it is a sibling of `metrics` in the HTTP/Python body ([`fit.py`](../../packages/eval/fit.py) `score_run` return). Copy it into the persisted G-test JSON (top-level or under metrics — pick one, document in the JSON `schema_version` bump if you bump).

### 6. Isolation Forest defaults

- [`models/features.json`](../../models/features.json): `isolation_forest.enabled_default` → **`false`**. Add `"contamination": 0.01` next to existing IF keys (SSOT §1).
- [`packages/eval/iso_check.py`](../../packages/eval/iso_check.py): read contamination from recipe / `features.json`; **do not** hardcode `0.05`. Default if missing: `0.01`.

Do not run Plan 08 IF abort-gate as part of this child. IF stays off until that gate is logged.

### 7. Tests (named, RED then green)

Extend [`tests/test_eval_phase6.py`](../../tests/test_eval_phase6.py) / [`tests/test_validation_protocol.py`](../../tests/test_validation_protocol.py) / fit tests:

- `model_freeze_id` changes when `best_params` or `op_threshold` change; unchanged when only comments… (features bytes change **should** change both hashes).
- After first seed-43 `all_rows` score, mutating `best_params` on the **same** `model_run_id` → `score_run` **raises**.
- Second score of the **same** freeze on the same `model_run_id` → refuse (or idempotent persisted read).
- Two `model_run_id`s scoring the same gtest parquet → both allowed.
- Persisted JSON contains `binary_ap`, `precision_at_op`, `recall_at_op`, `confusion_matrix`, `action_histogram`.
- `iso_enabled_flag` with `enabled_default: false` stays off; IF constructor uses 0.01 from config.

Do not weaken existing `recipe_hash` mismatch tests on `features.json` change.

---

## Out of scope (do not sneak in)

- Entity-holdout disjoint-ID CI, parquet invoice-flag isolation, Loop M `assert len(extra_tr) <= cap` (audit COSMETIC/RISK).
- Recomputing `app_ablation` on G-test rows (keep copy-from-champion; slides must say `app_ablation_source: champion_fit`).
- PSI 0.25/0.35 vs VALIDATION.md 0.2.
- Namespacing `event_id` with `world_seed`.
- Hard-fail `run_population` on `fidelity.pass == false`.
- Any external-dataset adapter.

---

## Gate to Child 2

Pytest for the above is green. `features.json` IF default is false. Operator may run `make generate-scale` / `make defend-fit` / `make defend-gdev` / `make defend-gtest` as the generate-dataset SOP.

Next: [`eval-child-generate-dataset-stages.md`](eval-child-generate-dataset-stages.md).
