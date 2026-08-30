# Champion registry (versioned)

**Naming:** **v0** = pre–autonomous-loop baselines (Stage 1 `v1-train-46`, Stage 2 Optuna). **v1** = **provisional champion after Wave 0 + Loop M** (`v1-train-46__loopm-train`) — this is the skill-era winner, not museum v0. **v2+** = subsequent experiments (FPR-tune, HN, etc.).

Canonical record of promoted models. **v1 photograph seeds 46/47/48 stay frozen** — new versions get new `model_run_id` suffixes; headline seed-48 numbers are not retroactively rewritten.

| Version | `model_run_id` | Train world | Promote gate | Confirmatory | Status |
|---------|----------------|-------------|--------------|--------------|--------|
| **v0** Stage 1 | `v1-train-46` | `v1-train-46` | — | `v1-gtest-48` | baseline |
| **v0** Stage 2 | `v1-train-46-stage2` | `v1-train-46` | AP Optuna (legacy) | `v1-gtest-48` | not champion |
| **v1** Loop M | `v1-train-46__loopm-train` | `v1-train-46` + Loop M extras | family AP + FPR ε on gdev | `v1-gtest-48` | **provisional champion** |
| **v2** FPR-tuned | `v1-train-46__fpr-v2` | `v1-train-46` + FPR Optuna | Pareto @ 1% on **gdev-47** | `v1-gtest-49` once | **REJECT** (identity/cost) |
| **v2-reject** HN | `v1-train-46__hn-train` | H6 generic mining | — | gtest-49 | **REJECT** |

## v1 Loop M — provisional champion (`v1-gtest-48` photograph)

| Metric | Value |
|--------|-------|
| `binary_ap` | 0.996 |
| `genuine_fp` (default op) | 8.07% |
| `recall_at_op` | 99.99% |
| `identity_burst` AP | 0.967 |
| `cost_sketch` | 0.011 |
| Pareto recall @ **1% FPR** (g48) | **99.6%** |

Artifacts: [`pareto_genuine_fpr.json`](../data/validation/v1/pareto_genuine_fpr.json), [`photography_day.json`](../data/validation/v1/photography_day.json).

**Operational note:** Default `detect_thr` undersells the Pareto frontier (~99.6% recall @ 1% FPR without retrain). Deployment should use FPR-constrained thresholding on calibrated scores, not the low default threshold alone.

**H5d operational report:** [`pareto_operational_v1.json`](../data/validation/v1/pareto_operational_v1.json) — on gtest-48 @1% FPR: recall **99.57%**, `genuine_fp` **0.99%**, identity_burst recall **99.8%** (vs default op 8.07% FPR).

## v2 FPR-tuned — H5c REJECT (`v1-train-46__fpr-v2`)

Optuna 25 trials, inner_val FPR objective, expanded HGB search. Artifact: [`h5c_fpr_v2_eval.json`](../data/validation/v1/h5c_fpr_v2_eval.json).

### gdev-47 (promote gate)

| Metric | v1 Loop M | v2 FPR | Verdict |
|--------|-----------|--------|---------|
| Pareto recall @ 1% FPR | **99.59%** | 99.38% | v2 slightly worse |
| Pareto recall @ 0.1% FPR | **98.43%** | 96.19% | v2 −2.2pp |
| `identity_burst` AP | **0.988** | 0.908 | **FAIL** (−8%) |
| `cost_sketch` | **0.002** | 0.663 | **FAIL** (~300×) |
| `genuine_fp` (default op) | 3.81% | 0.03% | misleading win |

### gtest-49 (confirmatory, one shot)

Same pattern: identity AP ~0.91 vs 0.99, cost ~0.69 vs 0.002. **Do not promote.**

**Lesson:** FPR-only inner objective + higher `detect_thr` repeats H6 failure mode — lower FPR without Pareto improvement and with family/cost collapse. Keep v1; next iteration: tune for **Pareto @ 1% on gdev** with cost + identity gates in objective, or deploy Pareto threshold on frozen v1 without retrain.

## Recursive Loop M (H7)

Promote/reject **each round on `v1-gdev-47`**. **`v1-gtest-49` once** after loop ends. **Max 3 rounds.** Round-1 diagnostic: [`h7_round1_diagnosis.json`](../data/validation/v1/h7_round1_diagnosis.json) — weakest family **ato** (AP 0.54 on gdev).

## Machine-readable

[`data/validation/v1/champion_registry.json`](../data/validation/v1/champion_registry.json)
