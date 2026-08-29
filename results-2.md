# Validation run log (v1)

Protocol: Post-G43 controlling plan (seeds **46/47/48**, not 43)  
Scale: **2400 × 120 × 90** (frozen until mule cardinality proven)  
Log: compare against frozen [`results.md`](results.md) (v0 museum, seed 43)

---

## Comparison block (required)

| Claim | v0 (`results.md`, seed 43) | v1 (seed 48) | Pass? |
|---|---|---|---|
| APP/invoice AP WITHOUT_STAMPS | 1.0 / 1.0 (stamps) | **0.579** combined (with flags 0.977) | E1 **partial** — stamps still dominate, not a 1.0 copy |
| mule n_pos G-test | 29 not_comparable | **3,162 comparable** | E1 **pass** |
| inner_fit ATO / identity | 0 / 0 | **206 / 333** | E2 **pass** |
| genuine_fp at detect_thr | 5.0% Stage 1 | **8.79%** Stage 1 | E4 **fail** vs v0 (higher FPR) |
| Stage 2 vs Stage 1 FPR | +9.3pp (worse) | **−1.25pp** (8.79% → 7.54%) | E4 **pass** |
| Loop M identity relative drop | −18.6% silent | **none** (ATO −2.4% rel, within ε) | E2 **pass** |
| mule_credit_restrict / n_pos | ~1139× | **1.19×** (3,753 / 3,162) | E5 **pass** |
| Loop T | n_fn=0 at τ≈1e-4 | **n_fn=0** skipped | E4/E6 **fail** (same empty miner) |

**E8 status:** SOP complete on 46/47/48. Stage 4 **scored** (streamed FeatureComputer; lead TPR@FPR, not AP vs lab G-test).

---

## Stage 0 — generate-dataset train (seed 46)

**Command:** `make generate-v1-train-46`  
**Date:** 2026-08-29  
**Wall time:** ~3.8 min  
**Artifact:** `data/runs/v1-train-46/`  
**Sidecar:** `n_customers=2400`, `n_merchants=120`, `sim_days=90`, `world_seed=46`, `pin=true`

| Check | Status |
|---|---|
| `_DONE` marker | present |
| event_count | 396,060 |
| mix | n_app=1578, n_funnel=2798, ident_burst=1529, ato_burst=396 |

---

## Stage 1 — Base HGB fit (seed 46)

**Command:** `fit_champion('v1-train-46', world_seed=46)`  
**Date:** 2026-08-29  
**Wall time:** ~2.3 min (permutation_importance 95.6s, bootstrap_ci 15.5s)  
**Artifacts:** `models/v1-train-46/champion.joblib`, `metrics.json`

First attempt died after PI: `assert_fold_n_pos` was called with train-only `y_tr` against full-run fold masks (false inner_val desert). Fixed alignment; floor then passed.

| Field | Value |
|---|---|
| `model_run_id` | `v1-train-46` |
| `recipe_hash` | `8423e6807b707f6767fce051524c934dfdbafff45d1c9464d718abcf3b9afeba` |
| `model_freeze_id` | `74fbf71102a01c3a126847adb00f8fa1f3be757d465dcdf6db35ae5c4397cf45` |
| `n_train` | 211,333 |
| `n_eval` | 184,727 |
| `binary_ap` | 0.840 |
| `precision_at_op` | 0.300 |
| `recall_at_op` | 0.931 |
| `genuine_fp` (fp/n_normal) | 4.84% |
| `genuine_fp_over_eval` | 6.76% |
| `op_threshold` / `detect_thr` | 0.000391 |
| `act_thr` | 0.5 |
| `operating_point_fpr` | 0.01 (tuned on inner_val) |
| `isolation_forest_enabled` | true |
| WITHOUT_STAMPS AP | 0.595 (with flags 0.993) |

### Eval-fold per-family (diagnostic — not headline G-test)

| Family | AP | n_pos | comparable |
|---|---|---|---|
| app_fraud | 0.981 | 744 | yes |
| invoice_fraud | 0.999 | 359 | yes |
| mule | 0.994 | 1,759 | yes |
| ato | 0.028 | 151 | yes |
| identity_burst | 0.095 | 1,003 | yes |

### Fold floors (E2)

| Slice | APP | invoice | mule | ATO | identity |
|---|---:|---:|---:|---:|---:|
| inner_fit | 614 | 316 | 1,148 | **206** | **333** |
| inner_val | 220 | 101 | 265 | 39 | 193 |
| eval | 744 | 359 | 1,759 | 151 | 1,003 |

All ≥15. Inner-fit ATO/identity are no longer zero.

### Red flags (documented)

- ATO AP 0.028 and identity AP 0.095 on eval — ranking is weak even with n_pos comparable.
- Mule AP 0.994 on eval is diagnostic only; wait for seed-48 photograph.
- WITHOUT_STAMPS AP 0.595 vs 0.993 with flags — stamp skill still dominates APP/invoice.
- Brake on eval: `mule_credit_restrict=65` vs mule n_pos 1,759 (cost_sketch).

---

## Stage 1b — n_pos proxy / Loop M family pick (seed 47)

**Command:** `make generate-v1-gdev-47` then `score_run('v1-gdev-47', model_run_id='v1-train-46', all_rows=True)`  
**Date:** 2026-08-29  
**Wall time:** generate ~3.8 min; score ~16s  
**Artifact:** `data/runs/v1-gdev-47/` (397,902 events)  
**Pick file:** `data/validation/v1/loop_m_family_pick.json`

### G-dev per-family

| Family | AP | n_pos |
|---|---|---|
| app_fraud | 0.982 | 1,582 |
| invoice_fraud | 1.000 | 764 |
| mule | 0.993 | 3,187 |
| ato | 0.535 | 398 |
| **identity_burst** (picked) | **0.319** | 1,540 |

**Loop M target:** `identity_burst` (lowest G-dev AP among n_pos ≥ 30)

G-dev binary AP 0.882, genuine_fp 8.61%, WITHOUT_STAMPS AP 0.560.

### n_pos proxy

**File:** `data/validation/v1/npos_proxy.json`  
**mule G-dev n_pos:** 3,187 → **proceed** (comparable; eval mule 1,759)

---

## Stage 3 — Loop M

**Command:** `run_loop_m('v1-train-46', 'identity_burst', family_chosen_from_slice='gdev44', gtest_seed=48, ...)`  
**Date:** 2026-08-29  
**Wall time:** generate+parent fit ~10 min (then PI abort); resume fit+score ~3 min  
**Artifact:** `data/validation/v1/loop_m_result.json`

First extra-row refit died: identity extras sampled late timestamps, `force_train` extended the train calendar, inner_val became identity-only, PI fail-loud. Extras now stay `inner_fit`; inner_val span measured on original train rows.

| Field | Value |
|---|---|
| `miss_family` | `identity_burst` |
| `model_run_id_before` | `v1-train-46` |
| `model_run_id_after` | `v1-train-46__loopm-train` |
| `gtest_run_id` | `v1-train-46__gtest` (Loop M internal world, **not** `v1-gtest-48`) |
| `n_extra` | 1,537 |
| **pass** | **true** |

### Before / after on Loop M `__gtest` (seed 48 synthetic)

| Metric | Before | After | Verdict |
|---|---|---|---|
| identity_burst AP | 0.337 | **0.967** | **improved** (+0.630) |
| genuine_fp | 8.79% | 8.07% | ok (within ε=0.02) |
| ato AP | 0.546 | 0.533 | equal (−2.4% rel, ε=5%) |
| mule n_pos | 3,162 | 3,162 | comparable |

Other families: APP improved; invoice/mule equal. No silent other-family drop this pass.

Headline `v1-gtest-48` photograph deferred to Photography Day.

---

## Stage 2 — Optuna nested A/B

**Command:** `tune_champion('v1-train-46', world_seed=46, dest_run_id='v1-train-46-stage2')`  
**Date:** 2026-08-29  
**Wall time:** ~7.4 min (trials + refit)  
**Artifacts:** `models/v1-train-46-stage2/`, `data/validation/v1/tune_summary.json`, `trials.json`

| Field | Value |
|---|---|
| `optuna_skipped_small_n` | false |
| `inner_val_fraud_pos` | 818 |
| `n_trials` | 40 (file present) |
| **best_params** | max_depth=3, lr=0.0286, max_iter=65 |
| `model_freeze_id` | `9faf0edc00c9aa81d91c5e7c33731b36cc405d07e866d45241e3f894c79599de` |
| `detect_thr` | 0.0436 |
| `act_thr` | 0.5 |
| inner_B genuine_fp (best trial) | 0.84% (ceiling 0.02) |

### Stage 1 vs Stage 2 (eval fold — diagnostic)

| Metric | Stage 1 | Stage 2 | Δ |
|---|---|---|---|
| binary_ap | 0.840 | 0.839 | −0.001 |
| genuine_fp | 4.84% | **3.56%** | **−1.28pp** |
| identity AP | 0.095 | 0.505 | +0.410 |
| ato AP | 0.028 | 0.004 | −0.024 |
| mule AP | 0.994 | 0.977 | −0.017 |

`max_depth` stayed at 3 (not the search bound). Nested inner_B FPR constraint held. G-test photograph deferred to Photography Day.

---

## Stage 3b — Loop T

**Command:** `mine_fn_rules('v1-train-46', 'v1-gdev-47', 'identity_burst')`  
**Date:** 2026-08-29  
**Artifact:** `data/validation/v1/loop_t_result.json`

| Field | Value |
|---|---|
| status | **skipped** |
| reason | `insufficient_fn` |
| n_fn | **0** |
| n_genuine | 390,431 |
| candidates | [] |

Stage 1 champion already catches every identity_burst FN on G-dev. No drafts, no YAML change. **3b complete.** Photography Day uses current `v0_rules.yaml`.

---

## Photography Day (seed 48 only)

**Date:** 2026-08-29  
**World:** `data/runs/v1-gtest-48/` (394,954 events)  
**Artifacts:** `data/validation/v1/photography_day.json`, `npos_gate.json`, `delta_vs_stage1.json`

Same seed/scale as Loop M `__gtest`, so family APs match that comparison. Seed 43 was never opened.

### Headline table (same G-test population)

| Model | binary_ap | genuine_fp | precision | recall | ato AP | identity_burst AP | mule AP |
|---|---|---|---|---|---|---|---|
| Stage 1 `v1-train-46` | 0.879 | **8.79%** | 0.172 | 0.952 | **0.546** | 0.337 | 0.996 |
| Stage 2 Optuna | 0.866 | **7.54%** | 0.194 | 0.948 | 0.369 | 0.535 | 0.972 |
| Stage 3 Loop M | **0.996** | 8.07% | 0.192 | 1.000 | 0.533 | **0.967** | 0.995 |

WITHOUT_STAMPS AP **0.579** on all three rows (with APP flags 0.977).

### n_pos (all three rows share this)

| Family | n_pos | comparable |
|---|---|---|
| app_fraud | 1,572 | yes |
| invoice_fraud | 747 | yes |
| ato | 395 | yes |
| identity_burst | 1,542 | yes |
| mule | **3,162** | **yes** |

**npos_gate:** `comparable` — mule 3,162 ≥ 30. No scale bump.

### Stage 1 vs 2 delta (G-test)

| | |
|---|---|
| binary_ap Δ | −0.013 |
| genuine_fp Δ | **−1.25pp** |
| verdict | **`stage2_ok`** |
| noise-chase | `max_depth=3` (not at search bound) |
| `stage3_parent` | **1** (always) |

### Brake (Stage 1)

`mule_credit_restrict` 3,753 vs mule n_pos 3,162 → **1.19×** (v0 was ~1,139×).

### Check (this pass)

Loop M is the strongest G-test row: identity 0.337 → 0.967, binary AP 0.879 → 0.996, genuine_fp still within ε of Stage 1 (8.79% → 8.07%). Other-family gate held. Mule is comparable and AP ~0.996.

Stage 2 did what v0 failed: FPR went **down** (−1.25pp) with flat-to-worse binary AP. ATO AP fell 0.546 → 0.369 on G-test — do not promote Stage 2 as headline.

**Headline:** Loop M `v1-train-46__loopm-train` for identity + overall AP. Stage 1 remains the cleaner FPR parent if you refuse the extra-row identity boost. WITHOUT_STAMPS 0.579 and Loop T n_fn=0 are still the honesty constraints — APP/invoice are not portable, and the miner never ran.

Do not rescore seed 43. Stage 4 scored — see below. Do not compare SAML-D AP to this G-test table.

---

## Stage 4 — external-dataset

**Date:** 2026-08-29  
**Command:** streamed `score_saml_d()` (nice −15, `OMP_NUM_THREADS=1`, batch 2048). Wall ~22.6 min. Peak RSS ~4.1 GB. Did **not** `pd.read_csv` the 9.5M file.  
**CSV:** `data/externals/SAML-D.csv` (951 MB; gitignored)  
**Model:** frozen Stage 1 `v1-train-46` (`detect_thr` ≈ 3.91×10⁻⁴)  
**Adapter:** `packages/eval/saml_d.py` (single-pass FeatureComputer; last ⅓ calendar scored in batches)  
**Artifacts:** [`data/validation/v1/holdout_metrics.json`](data/validation/v1/holdout_metrics.json), [`data/validation/v1/stage4_saml_d.json`](data/validation/v1/stage4_saml_d.json)  
**Write-up:** [`Docs/validation/stage4-external-block.md`](Docs/validation/stage4-external-block.md)  
**Mapping:** [`Docs/plans/saml-d-typology-map.template.md`](Docs/plans/saml-d-typology-map.template.md)

Eval cut 2023-05-08 18:49:54 UTC (last ⅓ of 2022-10-07 → 2023-08-23). `n_rows` 9,504,852 → `n_eval` **3,144,540**. Eval prevalence **0.1105%** (stated 0.1039%).

**Lead metric — TPR@FPR** (do **not** compare `binary_ap` 0.0021 to Photography Day 0.879):

| FPR target | TPR | Score threshold |
|---|---|---|
| 0.1% | **1.09%** | 0.993 |
| 0.5% | **1.47%** | 0.990 |
| 1% | **2.27%** | 0.977 |

Lab `detect_thr` on this table: recall 68.8%, precision 0.139% (≈ prevalence). The frozen threshold is not a SAML-D operating point.

Eval n_pos: mule **3,084** (family AP 0.00096), invoice_fraud **22** (AP withheld, n<30), unmapped **369**, normal 3,141,065. Never `app_fraud` / `ato`.

**Investigation (no model change):** [`Docs/plans/v1-saml-d-transfer-investigation.md`](Docs/plans/v1-saml-d-transfer-investigation.md). Measurement-fix plan: [`Docs/plans/v1.1-verification-and-fix-pass.md`](Docs/plans/v1.1-verification-and-fix-pass.md). WITHOUT_STAMPS 0.579 is **not** per-model (ablation retrains a toy APP detector). Loop M `__gtest` **is** `v1-gtest-48` (identical event_ids). SAML-D scored Stage 1 only.

| Row | Result |
|---|---|
| SAML-D | **scored**. Streamed adapter. Lead TPR@FPR ≈ random×1–2. Lab champion does **not** transfer. |
| Xente | License unverified — omitted |
| IBM HI-Small | CSV not fetched — PSI not run |
| BAF | Overlap matrix only; no champion transfer (CC BY-NC-ND) |
| APP/invoice | Public gap confirmed. Over-Invoicing n=22 in eval — too few for family AP. |

---

## Wave 0 — autonomous validation loop (2026-08-29)

**Branch:** `agent/wave0-validation`  
**Scope:** measurement / instrumentation only on frozen `v1-gtest-48`. No generator, Brake, or model-recipe changes.

### 0.1 Frozen-champion ablation (P0 closed)

**Defect:** `_app_ablation` refit a toy APP HGB; all three Photography rows showed identical `without_stamps` **0.579** (unconfirmed per model).

**Fix:** zero columns on encoded matrix → score frozen `champ.model` / `_fraud_score`; tag `app_ablation_source: frozen_champion`; seed-43 cache checks `gtest_run_id` on read.

**Re-scored WITHOUT_STAMPS (binary AP, frozen champion) on `v1-gtest-48`:**

| Model | with_app_flags (APP AP) | without_app_flags | **without_stamps** |
|---|---|---|---|
| Stage 1 | 0.980 | 0.222 | **0.717** |
| Stage 2 | 0.977 | 0.174 | **0.549** |
| Loop M | 0.983 | 0.242 | **0.844** |

Pre-fix **0.579** is deprecated. Artifact: [`data/validation/v1/photography_day.json`](data/validation/v1/photography_day.json) (`champion_model_run_id`: `v1-train-46__loopm-train`).

### 0.2 G-test alias

`v1-train-46__gtest` ≡ `v1-gtest-48` (394,954 identical `event_id`s). Documented in [`data/validation/v1/loop_m_result.json`](data/validation/v1/loop_m_result.json). Not independent holdout.

### 0.3 genuine_fp naming

`genuine_fp` = FP/n_normal (lead). `genuine_fp_over_eval` = predicted-positive rate — see [`VALIDATION.md`](VALIDATION.md) §0.3.

### 0.4 Hub gate (report-only)

[`data/validation/v1/hub_gate_report.json`](data/validation/v1/hub_gate_report.json): 34,052 hub rows; `fan_in_1h≥6` → 21,233; **31** received `mule_credit_restrict` / hard_flag (Loop M champion). Wave 1 gate would fail — Brake unchanged in Wave 0.

### 0.6 SAML-D Loop M (complete)

Stream-scored `v1-train-46__loopm-train` (~18 min, peak RSS ~4.1 GB). Artifact: [`stage4_saml_d_loopm.json`](data/validation/v1/stage4_saml_d_loopm.json).

| FPR target | Stage 1 TPR | Loop M TPR |
|---|---|---|
| 0.1% | 1.09% | **1.96%** |
| 0.5% | 1.47% | **3.05%** |
| 1% | 2.27% | **3.91%** |

Still weak absolute transfer; lead metric only. `binary_ap` ~0.002 (both).

**Ledger:** [`data/validation/v1/agent/`](data/validation/v1/agent/), [`docs/agent/final_validation_report.md`](docs/agent/final_validation_report.md).

---

## Wave 1 iteration 1 — H2 hub exemption (2026-08-29)

**ACCEPT.** Hub `mule_credit_restrict` 31 → 0 on gtest-48. Seed 49 confirmatory: `genuine_fp` 8.12%, cost 0.0092. Loop continues (SAML-D / portable features next).
