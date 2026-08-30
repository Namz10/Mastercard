# v1 → SAML-D transfer-failure investigation

**Date:** 2026-08-29  
**Status:** evidence audit. **No model change.** Frozen [`results.md`](../../results.md) untouched.  
**SOP log:** [`results-2.md`](../../results-2.md)  
**SAML-D metrics:** [`data/validation/v1/holdout_metrics.json`](../../data/validation/v1/holdout_metrics.json)  
**Photography:** [`data/validation/v1/photography_day.json`](../../data/validation/v1/photography_day.json)

This document answers: what is actually broken vs evaluation mismatch vs simulator leakage, and what we may claim.

SAML-D was scored with **Stage 1 only** (`v1-train-46`). Loop M was **not** sent through the adapter. External numbers below are not a Loop M result.

---

## Headline

The lab champion does not rank SAML-D laundering. That is not “the threshold is wrong.” Internal `detect_thr` flags ~55% of SAML-D eval rows (precision ≈ prevalence). TPR@FPR, which is threshold-free ranking, is ~2–11× a random ranker and ~70× worse than the same model’s train-eval TPR@0.1% FPR (72% → 1.1%).

The combination that explains the gap:

| Code | Verdict | Weight |
|---|---|---|
| A simulator leakage / stamps | **Primary on lab APP/invoice AP** | High |
| B feature distribution shift | **Primary on transfer** | High |
| C label/family mapping | **Material, not the whole gap** | Medium |
| D threshold/calibration | **Real at internal op; does not explain TPR@FPR** | Medium |
| E temporal construction | Same `FeatureComputer`; **entity age/KYC is not the same** | Medium |
| F SAML-D patterns absent in sim | **Primary on mule family AP** | High |
| G prevalence / methodology | **AP is not comparable** | High (for claims) |
| H combination | **Yes. A+B+F+G, with D at the frozen cut** | — |

---

## A. What is actually broken

1. **Ranking on SAML-D is near-chance in the bulk of the score range.**  
   TPR@FPR 0.1% / 0.5% / 1% = 1.09% / 1.47% / 2.27%. Train-eval (seed 46 eval fold) TPR@0.1% FPR was **72.3%** (`models/v1-train-46/metrics.json`).

2. **Mule-vs-rest AP on SAML-D is 0.00096** with mule prevalence 3084/3,144,540 = 0.000981. That is **no ranking** of mapped mule rows. Graph features exist on both sides; the lab mule signature (fan-in knob 18, 3-day mule accounts, smurf cap) is not SAML-D’s mix (structuring, smurfing, layered fan, cash withdrawal, cycles, …).

3. **Permutation importance on Stage 1 inner_val is stamp-heavy:** `urgency_pressure`, `gstin_checksum_ok`, `beneficiary_changed` are in the top 7. SAML-D replay **hard-zeros** all APP/invoice stamps. The model’s highest-importance directions are structurally off.

4. **WITHOUT_STAMPS 0.579 on Photography Day is not a champion metric.** All three models (Stage 1, Stage 2, Loop M) store the **identical** `without_stamps` / `with_app_flags` / `without_app_flags` floats. `_app_ablation` **retrains a fresh binary APP HGB** on the scored world’s matrices; it does not zero columns on the frozen champion. On `all_rows=True` G-test, `x_tr == x_ev` (the G-test world). Treat 0.579 as **unconfirmed for Wave 6**. Fit-time ablation on seed-46 eval (still a retrain, not the champion) is 0.993 → 0.601 / 0.595.

5. **8% genuine FP is a real product failure on the lab operating point**, independent of SAML-D. Loop M recall 99.99% at 8.07% genuine FP / 19% precision. Cost sketch is the honest lab headline (Loop M expected_cost 0.011 vs Stage 1 0.486), not AP.

---

## B. What is merely evaluation mismatch

1. **Prevalence.** Lab G-test fraud rate ≈ 7418/394954 = **1.88%**. SAML-D eval **0.1105%**. Binary AP 0.879 vs 0.0021 is not a transfer coefficient.

2. **Label ontology.** Lab y ∈ {app_fraud, ato, identity_burst, invoice_fraud, mule, normal}. SAML-D mapped y ∈ {mule, invoice_fraud, unmapped, normal}. **Zero** APP/ATO/identity rows. Families that dominate lab AP (APP 0.98, invoice 1.00) are **absent** from the external table.

3. **SAML-D `binary_ap` is 1−P(normal), family AP uses per-class `pmap`.** Internal family AP uses `_ap_by_family` on the family’s probability column. SAML-D mule AP used the **binary fraud score** against a mule indicator. Not the same estimator. Do not call 0.00096 a clean family comparison.

4. **`genuine_fp` vs `genuine_fp_over_eval`.**  
   - `genuine_fp` = FP / n_normal (canonical). Photography Stage 1: 34076/387536 = 8.79%.  
   - `genuine_fp_over_eval` = **(TP+FP)/n_eval** (predicted-positive rate), 41138/394954 = 10.42%. Name is M4-class misleading.  
   Fit-time Stage 1 `genuine_fp` 4.84% is the **seed-46 eval fold**, not gtest-48. Same formula, different population. Expected to differ.

5. **Loop M `__gtest` is not a second photograph.** `v1-train-46__gtest` and `v1-gtest-48` are seed 48, 2400×120×90, **394954 rows, event_id sets identical, positional match.** Two directories, one population. Loop M “internal G-test” agreeing with Photography Day is **the same table**, not stability across worlds.

6. **Invoice family AP on SAML-D is null** (n=22 < 30). Cannot claim invoice transfer.

---

## C. What is simulator leakage

Not target columns in X (`assert_no_x_leak` holds; denylist is real). Leakage is **generator → feature determinism**.

Stage 1 inner_val permutation importance (neg log-loss):

| Rank | Feature | Importance | SAML-D analogue |
|---|---|---|---|
| 1 | `urgency_pressure` | 0.039 | Always 0 |
| 2 | `account_age_days` | 0.025 | First-seen in CSV, not KYC age |
| 3 | `gstin_checksum_ok` | 0.017 | Always false |
| 4 | `payee_history_count` | 0.014 | Causal, yes |
| 5 | `fan_in_24h` | 0.012 | Causal, yes |
| 6 | `hours_since_payee` | 0.009 | Causal, yes |
| 7 | `beneficiary_changed` | 0.008 | Always false |

APP injector (`packages/sim/inject/app_session.py`, mix knobs): fraud paths set `call_active_flag=True`, `urgency_pressure≈0.8`. Invoice `doc_beneficiary.py` sets GST flags by scenario. Those columns are not y, but they are **near-sufficient statistics of the family generator**.

Rule bits (`rule__*`) are mostly 0.0 PI on inner_val — the HGB already has the raw stamps. On SAML-D, stamp-triggered rules do not fire; graph rules may still fire on FeatureComputer counts.

`burst_velocity` is documented as a clone of `fan_out_1h` in older architecture notes; PI is ~0.

---

## D. What transfers (narrow)

What **can** be claimed as portable machinery, not performance:

- Causal `FeatureComputer` (1h/24h/7d/30d deques, G(t−)) ran on 9.5M SAML-D rows without loading the CSV.
- Graph/velocity columns are defined the same way. They did **not** produce mule ranking (family AP ≈ prevalence).
- Adapter never maps to `app_fraud` / `ato`.
- Restrict ratio on lab mule is 1.19× (v0 was ~1139×) — a lab Brake claim, not an external one.

What **does not** transfer: APP/invoice stamps, lab `detect_thr`, binary AP, APP/ATO/identity family AP, invoice family AP.

---

## E. Highest-value fixes (do not retrain yet)

Ordered by “fixes a lie or unblocks a real experiment,” not AP.

1. **Ablation instrumentation (Phase 1.1).** Score the **frozen champion** with stamp columns zeroed. Key results by `(model_freeze_id, run_id)`. Add a test: two toy models on one world → ablations **must differ**. Recompute Photography Day WITHOUT_STAMPS for all three models from existing `v1-gtest-48` parquet (measurement only).

2. **Rename Loop M G-test honestly.** `v1-train-46__gtest` ≡ `v1-gtest-48`. Log it as the same seed-48 photograph.

3. **Document `genuine_fp` vs `genuine_fp_over_eval` in VALIDATION.md.** Do not “reconcile” 4.84% vs 8.79% — different rows.

4. **Hub gate report-only** on existing gtest parquet (Phase 2.1). If it requires Brake/rule edits, that leaks seed 48 → confirm on **49**, do not iterate 48.

5. **Name champion (Phase 2.2).** Wave 6: FPR-constrained recall, then mule ranking, then WITHOUT_STAMPS (post-1.1). **Provisional champion: `v1-train-46__loopm-train`.** Cost 0.011 vs 0.486 is the verified differentiator. WITHOUT_STAMPS currently tied because it is invalid.

6. **Next SAML-D pass (optional, not a model change):** stream-score **Loop M** too; persist score histograms (normal vs mapped-fraud) and TPR at more FPR points. Do not `pd.read_csv` the full file.

7. **Simulator (only after 1.1, new seed 49 if behavior changes):** stamp noise on genuine; hard-negative hubs already exist but unmeasured; ATO diversity (hardest family 0.53); **do not** make ATO easier. Goal: genuine FP **down**, not AP up.

8. **Do not** spend remaining time on Optuna or swapping HGB for XGBoost. Internal AP is already saturated on stamps.

---

## F. Ablation matrix (reproducible; not executed)

Every candidate later must be scored on seed 46 train / 47 G-dev / 48 G-test (frozen) / SAML-D last-⅓. **Primary objective: external TPR@FPR and lab genuine FP.** Secondary: family coverage, calibration. **Not** max synthetic AP.

| ID | Change | Internal 48 | SAML-D | Allowed now? |
|---|---|---|---|---|
| M0 | Stage 1 as photographed | done | scored | freeze |
| M1 | Loop M as photographed | done | **not scored** | score only |
| M2 | Champion × zero stamps (no retrain) | re-score 48 | re-score adapter | measurement |
| M3 | Champion × zero APP flags only | re-score 48 | ≈ M2 (already zero) | measurement |
| M4 | Champion × portable columns only (iso stamp-free list + graph) | re-score 48 | re-score adapter | measurement |
| S1 | Hard negatives (travel, legit burst, new-device genuine) | **seed 49** | after | blocked until 1.1 |
| S2 | Stamp noise / non-deterministic APP | seed 49 | after | blocked |
| T1 | Recalibrated op on SAML-D (report only) | n/a | report TPR@FPR (already) | report |

Do not cherry-pick M2 if M0/M1/M3/M4 are missing.

---

## G. Recommended final model

**Do not replace HGB.** Do not ensemble-search.

- **Named lab champion (provisional):** `v1-train-46__loopm-train` — recall/cost, mule comparable, identity fixed, ATO still weak (0.53).  
- **External baseline:** `v1-train-46` until Loop M is streamed on SAML-D.  
- **Operating-point target (next system change, seed 49):** recall ≥ 98% **subject to** genuine FP substantially below 8%, not AP 0.998.

---

## H. Claims we can safely make

- Lab Photography Day (seed 48, 394,954 events): Stage 1 AP 0.879 / genuine FP 8.79%; Loop M AP 0.996 / genuine FP 8.07% / identity 0.337 → 0.967; mule n_pos 3,162 comparable; restrict 1.19×.  
- Loop M expected_cost 0.011 vs Stage 1 0.486 (lab units, not India).  
- SAML-D last-⅓, Stage 1, streamed FeatureComputer: TPR@FPR 1.09% / 1.47% / 2.27%. Prevalence 0.1105%. Mapping never APP/ATO.  
- APP flags are synthetic and not an SDK; fit-time APP AP collapses ~0.99 → ~0.60 when a **retrain** zeros them (still not champion-on-ablated-X).  
- Authors of SAML-D: synthetic table will not fully capture real-world unpredictability.

---

## I. Claims we absolutely should NOT make

- “0.996 AP on G-test therefore the detector works on AML data.”  
- “WITHOUT_STAMPS 0.579 proves stamps are only part of the story” **per model** — the three models share one number because ablation ignores the champion.  
- “Loop M was validated on an independent G-test from Photography Day.” Same 394,954 event_ids.  
- “SAML-D mule AP 0.00096 is a family transfer number comparable to lab mule 0.996.” Different score, different ontology, AP ≈ prevalence.  
- “Invoice/APP/ATO transfer.” Invoice n=22; APP/ATO not in SAML-D.  
- “Internal `detect_thr` is the SAML-D operating point.” It flags ~1.72M / 3.14M rows.  
- Hub-FPR / “high volume ≠ mule” until Phase 2.1 is measured on the photograph.  
- Any Xente/IBM/BAF transfer.

---

## Phase 1–2 measurement bugs (confirmed)

### 1.1 Stamp ablation (blocks Wave 1 “stamps partially killed”)

Not a JSON cache keyed by `run_id` for seed 48 (`_gtest_cached_score_if_opened` only returns cache when `world_seed == 43`). The identical Photography Day ablation triple is because `_app_ablation` **does not use `champ.model`**. Fix: zero columns on encoded X, run **frozen** `_fraud_score`. Test: 1-tree vs champion on same gtest → ablations differ.

### 1.2 Loop M aliasing

`gtest_run_id` `v1-train-46__gtest` is a second `run_population(world_seed=48, …)` write. Event IDs match `v1-gtest-48` exactly. Document as alias of the same photograph.

### 1.3 genuine_fp denominator

Two formulas, both implemented on purpose. Fit-time vs gtest differ because populations differ. Standardize **reporting**: lead `genuine_fp` (FP/n_normal). Relabel or deprecate `genuine_fp_over_eval`.

### 2.1 Hubs

Generator plants 3 `kind=hub` merchants (`packages/sim/world.py`). Tests only check they are labeled `normal`. Photography `action_histogram` does not split hubs. **Unmeasured.** Report-only first.

### 2.2 Champion field

`photography_day.json` has no `champion_model_run_id`. Add after 1.1: `v1-train-46__loopm-train`.

---

## Score distributions (without another 9.5M pass)

Per-row SAML-D scores were discarded (RAM-safe stream). Reconstruct from aggregates:

- Internal op 3.91×10⁻⁴: recall 68.8%, precision 0.139% ⇒ **TP+FP ≈ 1.72M** of 3.14M (≈55% of eval above thr). Scores are **not** collapsed to zero; the cut is far too low.  
- TPR@0.1% FPR needs threshold **0.993**. Mass sits in (0.0004, 0.993) for both classes — **poor separation**, not a calibration-only story.

PR/ROC plots require a future streamed dump of `(score, y)` (~3.1M float32 + int8 ≈ 16 MB), not a full feature matrix.

---

## Feature compatibility (champion X vs SAML-D)

Allowlist + `rule__*` from `models/v1-train-46/metrics.json` `feature_columns`.

**True analogue, same computer:** fan_in/out 1h/24h, unique payers, burst_velocity, txn_velocity_24h, hours_since_*, amount_vs_*, unique_payees_7d, payee_fan_out_1h, in_out_asymmetry_24h, is_new_payee, payee_history_count.

**Same name, different meaning:** `account_age_days` (lab KYC created_ts vs first ledger touch); `is_new_device` (always 0 on SAML-D); `kyc_tier` (always tier2); `rail` (always `upi_like`).

**Simulator-only (always false/0 on SAML-D):** APP×4, invoice×3.

**Rule bits:** stamp rules dead; graph rules may fire if thresholds met.

Amounts: SAML-D `Amount` × 100 → `amount_minor`. Currency mix (UK pounds, etc.) vs lab UPI priors — unquantified shift (no PSI this pass).

---

## Family mapping (eval slice)

Positives 3475 = mule 3084 + invoice 22 + unmapped 369. **10.6% of positives excluded from family AP.** Unmapped: Behavioural_Change_*, Single_large. Mule bucket mixes 13 graph/placement types. Over-Invoicing is a weak GST analog and under-powered.

---

## Red-team (hackathon judge)

- Ablation number reused across models.  
- Two G-test run_ids, one population.  
- External scored Stage 1 only.  
- Lead lab AP 0.996 at 8% genuine FP.  
- SAML-D AP quoted next to lab AP.  
- Hub gate claimed but not in sidecar.  
- “Portable graph features” while mule AP ≈ prevalence.  
- Iso/ECE on lab not shown as transfer evidence.

---

## Execution order (v1.1, half-day to one day)

See [`v1.1-verification-and-fix-pass.md`](v1.1-verification-and-fix-pass.md). Measurement on frozen 48 first. No second casual G-test. Seed **49** only if Brake/rules/generator change.
