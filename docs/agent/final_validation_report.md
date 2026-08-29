# Final validation report — Wave 0 (v1 Defend)

**Date:** 2026-08-29  
**Branch:** `agent/wave0-validation`  
**Photograph:** `v1-gtest-48` (seed 48, re-scored only — not regenerated)

## Defects found and disposition

| ID | Defect | Status |
|----|--------|--------|
| B1/P0 | Identical `without_stamps` 0.579 on all models | **Fixed** (0.1) |
| B2/P0 | `_app_ablation` toy retrain | **Fixed** |
| B3/P0 | Seed-43 cache ignored `gtest_run_id` | **Fixed** |
| B4 | `__gtest` alias to `v1-gtest-48` | **Documented** (0.2) |
| B5 | `genuine_fp_over_eval` naming | **Documented** (0.3) |
| B10 | Hub fan-in rule on hubs | **Measured** (0.4); 31 hub restricts |

## Accepted fixes

### Wave 0.1 — frozen-champion ablation

**Critic (10/10 PASS):**

1. Defect: ablation ignored champion → identical misleading WITHOUT_STAMPS.
2. Evidence: photography_day.json triple equality; `fit.py` `_app_ablation` refit path.
3. Label leak: no — zeros columns at score time only.
4. Less realistic sim: no generator change.
5. Overfit 48: no training; rescore frozen models on frozen world.
6. AP vs FP: exposes lower portable AP; does not inflate headlines.
7. SAML-D: instrumentation only; should not worsen external (no model change).
8. Improve: per-model `without_stamps` truthfulness.
9. Regress: headline binary AP unchanged (0.879 / 0.866 / 0.996).
10. Falsify: two champions on same world → ablations differ (`test_frozen_champion_ablation_differs_per_model`).

**Judge:** ACCEPT — instrumentation fix; headline APs stable; ablations now differ (0.717 / 0.549 / 0.844).

## Scorecard (G-test 48, post–Wave 0)

| Model | binary_ap | genuine_fp | cost_sketch | without_stamps |
|-------|-----------|------------|-------------|----------------|
| Stage 1 | 0.879 | 8.79% | 0.486 | 0.717 |
| Stage 2 | 0.866 | 7.54% | 0.553 | 0.549 |
| Loop M | **0.996** | 8.07% | **0.011** | **0.844** |

**Champion:** `v1-train-46__loopm-train`  
**Rule:** fpr_constrained_recall → mule_ranking → without_stamps_frozen_champion

## SAML-D TPR@FPR (external)

| Model | 0.1% FPR | 0.5% FPR | 1% FPR |
|-------|----------|----------|--------|
| Stage 1 (`holdout_metrics.json`) | 1.09% | 1.47% | 2.27% |
| Loop M (`stage4_saml_d_loopm.json`) | **1.96%** | **3.05%** | **3.91%** |

Loop M improves TPR@FPR vs Stage 1 on the same SAML-D eval slice but remains far from lab transfer. `binary_ap` ~0.0021 (both models). Do **not** compare to lab 0.879.

## Remaining limitations

- Transfer to SAML-D remains weak (combination H: stamps + shift + ontology).
- Hub gate: 31 legitimate hub rows restricted at `fan_in_1h≥6` — Wave 1 Brake work on seed **49** only.
- Loop T miner skipped (`n_fn=0` on G-dev).
- APP/invoice families have no honest external analog.
- Pre–Wave 0 WITHOUT_STAMPS **0.579** must not be cited.

## Claims the Defend pipeline may vs must not make

**May:**

- Loop M improves identity_burst and binary AP on seed-48 photograph with cost sketch 0.011 vs 0.486.
- Mule n_pos 3,162 on G-test is comparable; entity recall metrics are meaningful at v1 scale.
- SAML-D TPR@FPR is the honest external headline (Stage 1 and Loop M sidecars).
- WITHOUT_STAMPS frozen-champion AP differs by model (portable-column stress test).

**Must not:**

- Claim WITHOUT_STAMPS 0.579 or identical ablation across models.
- Claim `v1-train-46__gtest` is independent confirmation of G-test.
- Claim lab AP 0.879 transfers to SAML-D.
- Claim hub high-volume merchants are exempt from mule rules (unmeasured until Wave 1).
- Lead with accuracy or “lab rate = India.”

## Wave 1 iteration 1 — H2 hub payee exemption (ACCEPT)

**Change:** `mule-fan-in-burst` does not trigger `mule_credit_restrict` for `VID-SIM-HUB-*` payees (`brake.py`, vectorized hist in `fit.py`).

| Check | Before | After |
|---|---|---|
| Hub `mule_credit_restrict` (gtest-48) | 31 | **0** |
| `hub_fan_in_ge6_with_restrict` | 31 | **0** |
| Loop M `genuine_fp` gtest-48 | 8.07% | 8.07% (unchanged) |
| Loop M `genuine_fp` gtest-49 | — | 8.12% |
| Cost sketch gtest-49 | — | 0.0092 |

Confirmatory world: `data/runs/v1-gtest-49/` (seed 49, 396,655 events). Model scores unchanged; Brake-only.

## Wave 1 entry criteria

P0 closed. Hub gate measured (fail documented). Proceed with hypotheses on seed **49** for behavior changes only.

## User KB + prompt intake

- **KB:** `docs/agent/kb.md` (append-only priorities; seeded 2026-08-29 with FPR Pareto, recursive Loop M, hard negatives, cross-world, ablation, adversarial sim)
- **Prompt:** `docs/agent/prompt.md` (session overrides; read each cycle)

## Wave 1 iteration 2 — H5 FPR Pareto baseline (measurement)

**Artifact:** `data/validation/v1/pareto_gtest48.json` on frozen `v1-gtest-48`.

| FPR target | Stage 1 TPR | Loop M TPR | Loop M dominates? |
|------------|-------------|------------|-------------------|
| 5% | 96.3% | **99.9%** | yes |
| 2% | 94.8% | **99.9%** | yes |
| 1% | 87.9% | **99.8%** | yes |
| 0.5% | 84.7% | **99.7%** | yes |
| 0.1% | 83.1% | **98.7%** | yes |

Loop M dominates Stage 1 at every operating point on seed 48. Next: FPR-**constrained training** (not just threshold sweep) per KB §1.

## Wave 1 iteration 3 — H4 genuine stamp noise (REJECT)

**Worlds:** train `v1-train-50` (seed 50), test `v1-gtest-52` (seed 52). Generator change landed (2% low APP-shaped stamp noise on normals).

**Fit blocked:** `inner_val.ato=0<15` on `v1-train-50` (E2 fold floor). Cannot retrain until inner calendar has ≥15 ATO in inner_val.

**Partial read (frozen Loop M, no retrain):** `genuine_fp` on gtest-52 **10.03%** vs gtest-48 **8.07%** — seed + generator confound; does not validate H4 mechanism without successful fit.

## Wave 1 iteration 4 — H4-E2 preflight (ACCEPT)

`preflight_fold_floors()` at start of `fit_champion` — fail fast before PI when E2 fold floors fail (e.g. seed-50 `inner_val.ato=0`).

## Wave 1 iteration 5 — H6 hard-negative mining (REJECT)

**Plan:** [h6-hard-negative-mining.md](plans/h6-hard-negative-mining.md) · **Critic PASS** · **Judge REJECT**

Mined top-500 high-scoring normals from `v1-gdev-47` (frozen Loop M scorer) → `v1-train-46__hn-train` (500 extras, `evt-hn-*`, inner_fit).

| Metric | gtest-48 | gtest-49 (confirmatory) |
|--------|----------|-------------------------|
| `genuine_fp` | 8.07% → **6.70%** | 8.12% → **6.74%** |
| `recall_at_op` | 99.99% → 94.30% | 100% → 96.4% |
| `identity_burst` AP | 0.967 → **0.333** | 0.958 → **0.364** |
| `cost_sketch` | 0.011 → **0.575** | 0.009 → **0.368** |

FPR win is real on seed 49, but **identity_burst collapse** and **cost explosion** fail G6. Do **not** promote `v1-train-46__hn-train`. Artifact: `data/validation/v1/h6_hard_negatives.json`. Next: smaller `top_k`, family-aware mining, or payee/graph features per KB.
