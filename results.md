# Validation run log

Protocol: [external_holdout_validation plan](.cursor/plans/external_holdout_validation_64f9d54e.plan.md)  
Scale: **2400 × 120 × 90** (frozen)  
Order: refit-then-photograph (G-test on Photography Day only)

---

## Stage 0 — generate-dataset train (seed 42)

**Command:** `make generate-scale` (pre-existing run)  
**Artifact:** `data/runs/make-scale-fullmix/`  
**Sidecar:** `n_customers=2400`, `n_merchants=120`, `sim_days=90`, `world_seed=42`

| Check | Status |
|---|---|
| `_DONE` marker | present |
| Fidelity pass | yes |
| event_count | >50k |

---

## Stage 1 — Base HGB fit (seed 42)

**Command:** `make defend-fit`  
**Date:** 2026-08-29  
**Wall time:** ~43s (`bootstrap_ci` 9.1s)  
**Artifacts:** `models/make-scale-fullmix/champion.joblib`, `metrics.json`

| Field | Value |
|---|---|
| `model_run_id` | `make-scale-fullmix` |
| `recipe_hash` | `19ec558dd466815531f4fb4390a858ff7a7ad32b46376ed50faeaab84c87b65e` |
| `model_freeze_id` | `cc177e2643d122891da3fa0c6bfd4075f7b76e2bd5221784c8d4a377e204c074` |
| `n_train` | 280,623 |
| `n_eval` | 113,640 |
| `binary_ap` | 0.985 |
| `precision_at_op` | 0.190 |
| `recall_at_op` | 0.991 |
| `genuine_fp` (eval) | 3.7% |
| `op_threshold` | 0.000118 |
| `operating_point_fpr` | 0.01 (tuned on inner_val) |

### Eval-fold per-family (diagnostic — not headline G-test)

| Family | AP | n_pos | comparable |
|---|---|---|---|
| app_fraud | 1.00 | 600 | yes |
| invoice_fraud | ~1.00 | 370 | yes |
| mule | 0.060 | 24 | **no** (<30) |
| ato | NaN | 0 | no |
| identity_burst | NaN | 0 | no |

### Red flags (documented)

- Near-perfect AP on app_fraud / invoice_fraud (lab separability).
- Mule thin (n_pos=24); expect `not_comparable` on G-test.
- ato/identity_burst absent from eval fold (entity holdout).
- genuine_fp 3.7% on eval vs 1% inner_val tuning target.

---

## Stage 1b — G-dev (seed 44) + family pick

**Command:** `score_run('make-gdev', model_run_id='make-scale-fullmix', all_rows=True)` after world gen  
**Artifact:** `data/runs/make-gdev/`  
**Pick file:** `data/validation/stage1/loop_m_family_pick.json`

### G-dev per-family

| Family | AP | n_pos |
|---|---|---|
| app_fraud | 1.00 | 1,577 |
| invoice_fraud | ~1.00 | 752 |
| identity_burst | 0.350 | 104 |
| **ato** (picked) | **0.263** | 105 |
| mule | 0.031 | 29 (excluded, <30) |

**Loop M target:** `ato` (lowest G-dev AP among n_pos ≥ 30)

### n_pos proxy

**File:** `data/validation/stage1/npos_proxy.json`  
**mule eval n_pos:** 24 → **proceed** (≥15 proxy threshold)

---

## Stage 3 — Loop M

**Command:** `run_loop_m('make-scale-fullmix', 'ato', family_chosen_from_slice='gdev44', ...)`  
**Date:** 2026-08-29  
**Wall time:** ~6.8 min  
**Artifact:** `data/validation/stage3/loop_m_result.json`

| Field | Value |
|---|---|
| `miss_family` | `ato` |
| `model_run_id_before` | `make-scale-fullmix` |
| `model_run_id_after` | `make-scale-fullmix__loopm-train` |
| `gtest_run_id` | `make-scale-fullmix__gtest` (Loop M internal world, **not** `make-gtest`) |
| `n_extra` | 106 rows (cap 59,139 / 15%) |
| **pass** | **true** |

### Before / after on Loop M `__gtest` (seed 43 synthetic)

| Metric | Before | After | Verdict |
|---|---|---|---|
| ato AP | 0.426 | 0.487 | **improved** (+0.061) |
| genuine_fp | 5.0% | 6.7% | ok (within ε=0.02) |
| mule n_pos | 29 | 29 | not_comparable |

### Notes

- Parent `models/make-scale-fullmix/` refit in place (expected per protocol).
- Headline `make-gtest` photograph deferred to Photography Day.

---

## Stage 2 — Optuna

**Command:** `tune_champion('make-scale-fullmix', dest_run_id='make-scale-fullmix-stage2')`  
**Date:** 2026-08-29  
**Wall time:** ~4.5 min (40 trials + refit)  
**Artifacts:** `models/make-scale-fullmix-stage2/`, `data/validation/stage2/tune_summary.json`

| Field | Value |
|---|---|
| `optuna_skipped_small_n` | false |
| `inner_val_fraud_pos` | 651 |
| `n_trials` | 40 |
| **best_params** | max_depth=5, lr=0.046, max_iter=82 |
| `model_freeze_id` | `fd3902c0c082bdbc5fd60a487c41f4ce98d480c32ece81bc8191ab8ee5dbf4ff` |

### Stage 1 vs Stage 2 (eval fold — diagnostic)

| Metric | Stage 1 | Stage 2 | Δ |
|---|---|---|---|
| binary_ap | 0.985 | 0.985 | ~flat |
| genuine_fp | 3.7% | **10.0%** | **+6.3pp** ⚠️ |
| mule AP | 0.060 | 0.071 | +0.011 |

### Red flags

- **genuine_fp doubled** on eval (3.7% → 10%) — Optuna chased inner_val AP; outer eval FPR worsened. Record in delta; Stage 1 may win on FPR for write-up.
- `max_depth=5` at search boundary — possible noise-chase flag per protocol.

G-test photograph deferred to Photography Day.

---

## Stage 3b — Loop T

**Command:** `mine_fn_rules('make-scale-fullmix', 'make-gdev', 'ato')`  
**Date:** 2026-08-29  
**Artifact:** `data/validation/stage3b/loop_t_result.json`

| Field | Value |
|---|---|
| status | **skipped** |
| reason | `insufficient_fn` |
| n_fn | **0** |
| n_genuine | 387,538 |
| `loop_t_drafts_proposed` | 0 |
| `loop_t_drafts_approved` | [] |
| `live_rules_digest` | `8ff77520da7817c8b0972c31d9f771825c06c6dba73bcbead4620635be4618bd` |

Stage 1 champion already catches every ato FN on G-dev. No drafts, no YAML change. **3b complete.** Photography Day uses current `v0_rules.yaml`.

---

## Photography Day — G-test (seed 43)

**Date:** 2026-08-29  
**World:** `data/runs/make-gtest/` (390,967 events)  
**Artifacts:** `models/*/gtest_score.json`, `data/validation/photography_day.json`, `data/validation/npos_gate.json`, `data/validation/stage2/delta_vs_stage1.json`

Loop M had already written `gtest_score.json` for Stage 1 / Loop M on `__gtest`. Those files were archived to `gtest_score.loopm_internal.json` so this pass scored **`make-gtest`**.

### Headline table (same G-test population)

| Model | binary_ap | genuine_fp | precision | recall | ato AP | identity_burst AP | mule AP |
|---|---|---|---|---|---|---|---|
| Stage 1 `make-scale-fullmix` | **0.9925** | **5.0%** | 0.116 | 0.995 | 0.426 | **0.481** | 0.025 |
| Stage 2 Optuna | 0.9920 | **14.3%** | 0.044 | 1.000 | 0.489 | 0.457 | 0.021 |
| Stage 3b Loop M + live rules | 0.9926 | 6.7% | 0.090 | 1.000 | **0.487** | **0.392** | 0.022 |

### n_pos (all three rows share this)

| Family | n_pos | comparable |
|---|---|---|
| app_fraud | 1,578 | yes |
| invoice_fraud | 762 | yes |
| ato | 108 | yes |
| identity_burst | 108 | yes |
| mule | **29** | **no** |

**npos_gate:** `not_comparable` — mule 29 < 30. No scale bump this pass (operator choice: proceed with documented `not_comparable`).

### Stage 1 vs 2 delta

| | |
|---|---|
| binary_ap Δ | −0.0005 |
| genuine_fp Δ | **+9.3pp** |
| verdict | **`stage2_fp_worse`** |
| noise-chase | `max_depth=5` at search bound |
| `stage3_parent` | **1** (always) |

### Check (this pass)

**Keep Stage 1 as the headline champion.** Optuna did not help binary AP and blew FPR. Loop M improved ato AP (0.426 → 0.487) with genuine_fp still within ε of parent on the Loop M comparison; on `make-gtest` FPR is 5.0% → 6.7%. That pass is **not** strictly better: **identity_burst AP fell 0.481 → 0.392** (−18.6% relative) with n_pos=108 (comparable). Loop M's miss-family gate did not check other families on this run. Mule stays `not_comparable`. Loop T added no rules. Do not rescore seed 43 after recipe changes.

---

## Stage 4 — external-dataset

_Status: pending (`blocked_no_adapter`; fill `Docs/validation/stage4-external-block.md` when you want). New G-test after this recipe is seed **48**, never 43._
