# Peak handoff — entire process

**Audience:** someone picking up the repo for defense, scoring, or a next experiment.  
**Champion to use:** `v1-train-46__loopm-train` only. See [`FROZEN-MODEL.md`](FROZEN-MODEL.md).  
**Submission defense:** [`DEFENSE.md`](DEFENSE.md).  
**Full metric dump:** [`../agent/final-v1-metrics.md`](../agent/final-v1-metrics.md).

All headline numbers below are **internal simulator G-test** unless a section says SAML-D.

---

## 0. What to say in one minute

We detect five fraud families on a causal event-time feature vector with sklearn `HistGradientBoostingClassifier`, then map score + predicted family + rules into an action (`allow` / `notify` / `step_up` / `hold` / `decline` / `mule_credit_restrict`). We improved the model by adding **targeted extra training events for the weakest family** and **refusing** later candidates that cut genuine FPR but destroyed identity-burst ranking or cost. On frozen seed 48 the champion reaches **~98.7% recall at ≤0.1% genuine FPR**. External SAML-D transfer is **~2% TPR at 0.1% FPR** because session/device/stamp features the model uses internally do not exist there.

---

## 1. Worlds, seeds, and what is frozen

| Run ID | Seed | Role |
|--------|------|------|
| `v1-train-46` | 46 | Train world (2400 customers × 120 merchants × 90 days) |
| `v1-gdev-47` | 47 | Development / promote-reject gate |
| `v1-gtest-48` | 48 | Frozen photography holdout — **never used to promote** |
| `v1-gtest-49` | 49 | One-shot confirmatory after a loop ends |
| Museum `results.md` | 43 | **Do not touch / do not mix** |

Scale is frozen at **2400 × 120 × 90** until mule cardinality is proven. `v1-train-46__gtest` is **byte-identical** to `v1-gtest-48` — not an independent holdout.

**Do not regenerate seed 48.** Rescore frozen models only.

---

## 2. Pipeline (code map)

| Stage | Code | What it is |
|-------|------|-----------|
| Simulate population | `packages/sim/` | Event stream + `label_family` |
| Feature export | `packages/sim/export.py` | Train allowlist; no technique IDs in X |
| Rule bits | `packages/policy/rules.py` | Rule hits attached as features |
| Fit | `packages/eval/fit.py` | `HistGradientBoostingClassifier`, folds, Optuna, metrics |
| Family-targeted extras | `packages/eval/loop_m.py` | Append extras for weakest family; refit |
| Actions | `packages/eval/brake.py` | Policy enum from family + score + hits |
| FPR envelope | `packages/eval/fpr_pareto.py` | Max recall s.t. genuine FPR ≤ cap |
| 0.1% freeze | `packages/eval/internal_fpr_freeze.py` | inner_val thr → one G-test eval |
| SAML-D | `packages/eval/saml_d.py` | Stream replay + family map |
| SAML-D forensics | `packages/eval/saml_d_forensics.py` | B1–B7 audits |

Estimator: **`sklearn.ensemble.HistGradientBoostingClassifier`**. Multiclass over `{normal, app_fraud, ato, identity_burst, invoice_fraud, mule}`. Fraud score = `1 − P(normal)` after optional per-class isotonic calibration on an inner split.

---

## 3. Technical highlights (no project slang)

### 3.1 Histogram gradient boosting

`HistGradientBoostingClassifier` bins each continuous feature (up to `max_bins`) and grows trees on those bins. That is why it is the estimator: it handles mixed numeric/categorical (after encoding), is fast on ~2e5 train rows, and does not require a GPU.

Parameters that actually get searched or set:

| Parameter | Role |
|-----------|------|
| `max_iter` | Number of boosting iterations |
| `learning_rate` | Shrinkage per tree |
| `max_depth` **or** `max_leaf_nodes` | Tree complexity (mutually exclusive in our kwargs builder) |
| `min_samples_leaf` | Leaf size; controls variance on rare families |
| `l2_regularization` | Shrinks leaf values |
| `max_bins` | 64 / 128 / 255 |

Default recipe-ish baseline (Stage 1): shallow trees (`max_depth≈3`), `max_iter≈80`, `learning_rate≈0.08`. Isolation Forest can be enabled as an auxiliary signal (`isolation_forest_enabled`).

### 3.2 Nested inner split + Optuna

Training rows are split **inner_fit / inner_val**. Optuna’s objective **only** uses those. G-dev and G-test are never in the trial loop. Inner_val is further split A/B so calibrators fit on A and scores evaluate on B.

TPE sampler, typical 25 trials (H5c). Objective variants we actually ran:

1. **Stage 2:** AP-oriented inner objective → `v1-train-46-stage2` (worse AP and cost than Stage 1 on G-test).
2. **H5c:** maximize recall at a genuine-FPR ceiling on inner_val, with expanded HGB search → `v1-train-46__fpr-v2` → **rejected** on gdev (identity AP and cost).

**Optuna is a candidate generator, not a champion selector.**

### 3.3 Evaluation-gated family-targeted retraining (“Loop M”)

Mechanism, not a brand:

1. Score the current champion on G-dev.
2. Pick the weakest fraud family with enough positives.
3. Run the **same simulator** to generate extra events of that family only.
4. Append them to the original train parquet (capped as a fraction of train size; timestamps jittered into the train calendar; new `evt-lm-*` IDs).
5. Refit the **same** HGB class.
6. Compare to previous champion on G-dev using family AP, genuine FPR, and cost — not AP alone.

That is **targeted class-conditional data augmentation + a regression gate**, not generic oversampling and not GAN synthesis.

Recursive version (H7): max 3 rounds; each round judged on `v1-gdev-47`; `v1-gtest-49` once at the end. Round-1 diagnostic: weakest family is **ATO** (gdev AP 0.54). Round 2 was **not** run before freeze; do not start it against gtest-48.

### 3.4 FPR-constrained operating point

Two different procedures:

| Procedure | Threshold from | Eval | Purpose |
|----------|----------------|------|---------|
| Pareto envelope | Sweep scores **on the eval world** | Same world | Diagnostic frontier |
| **Protocol freeze** | `inner_val` of **train-46** | G-test **once** | Defensible operating point |

Genuine FPR = FP among rows labelled `normal` (not “all negatives including other fraud”). Frozen thr **0.9152** → eval-fold **98.52% recall @ 0.032% gfp**.

Default stored `detect_thr` (~5e-4) yields ~8% genuine FPR and ~100% recall. **Do not headline the default FPR.**

### 3.5 Action policy (`brake`)

Inputs: predicted family, fraud score, rule hits, payee id.

| Condition | Action |
|----------|--------|
| Mule pred or mule rule | `mule_credit_restrict` |
| Calm-down rule, no hard flag | `allow` |
| App fraud | `hold` or `notify` (never silent decline) |
| Invoice | `hold` or `case` |
| ATO | `decline` or `step_up` |
| Identity burst | `step_up` or `notify` |
| Else high score | `notify` |
| Else | `allow` |

Hub payees `VID-SIM-HUB-*` skip rule `mule-fan-in-burst` so legitimate high fan-in is not treated as mule.

### 3.6 Frozen-champion ablation

Zero feature groups **at score time** on the fitted champion. Do not refit. That is how WITHOUT_STAMPS became 0.717 / 0.549 / 0.844 instead of a fake identical 0.579.

---

## 4. Chronology (what actually happened)

| Wave / ID | What | Verdict |
|-----------|------|---------|
| Stage 0 | Generate train-46 | Done |
| Stage 1 | Base HGB fit | Baseline AP 0.879 on gtest-48 |
| Stage 2 | Optuna AP tune | Not champion (AP 0.866, cost 0.553) |
| Loop M | Family extras + refit | **Champion** AP 0.996, cost 0.011 |
| Wave 0.1 | Fix ablation toy-retrain | ACCEPT |
| H2 | Hub payee exemption | ACCEPT (31 → 0 restricts) |
| H4 | Stamp noise on normals | REJECT (E2 fold floor; no retrain) |
| H4-E2 | Preflight fold floors | ACCEPT |
| H5 | 5-point FPR/TPR curve | ACCEPT (measurement) |
| H6 | Generic hard-negative mining | **REJECT** |
| H6-D | Forensics on mined rows | ACCEPT (91% new-payee) |
| H5b | Tight Pareto 1/0.5/0.1% | ACCEPT |
| H5c | FPR-constrained Optuna v2 | **REJECT** |
| H5d | Operational Pareto on frozen v1 | ACCEPT (no retrain) |
| H7-R1 | Weakest-family diagnostic | ACCEPT (ATO) |
| H9 | Group ablation | ACCEPT |
| Phase A | Freeze 0.1% FPR thr from inner_val | ACCEPT |
| Phase B | SAML-D forensics | Complete; **stop** on retrain |

Ledger: [`results-2.md`](../../results-2.md), [`../agent/final_validation_report.md`](../agent/final_validation_report.md), [`../agent/kb.md`](../agent/kb.md).

---

## 5. Rejected experiments (keep in the ledger)

**Hypothesis → intervention → result → rejection reason**

| ID | Intervention | Result | Why rejected |
|----|--------------|--------|----------------|
| H6 | Top-500 high-score normals from gdev → retrain | FPR 8.12% → 6.74% on gtest-49 | identity_burst AP 0.958 → 0.364; cost ~40× |
| H5c | Optuna HGB + FPR thr on inner_val | Default FPR tiny | Pareto @1% worse; identity −8%; cost ~300× |
| H4 | 2% APP-shaped stamp noise on normals | Could not fit seed 50 | `inner_val.ato=0`; preflight now blocks this |

Do not re-run H6-style generic mining. If mining again: drop `is_new_payee=1` from the pool; mine fan-in/burst FPs.

---

## 6. SAML-D (external) — do not mix with 98.7%

Full eval (~3.14M last-third calendar), frozen Loop M:

| FPR | TPR |
|-----|----:|
| 0.1% | 1.96% |
| 0.5% | 3.05% |
| 1.0% | 3.91% |

Diagnosis (Phase B): **Case A** — 98.2% of SAML-D positives score below internal `detect_thr` 0.915. App/device/stamp features are stubbed false. `app_fraud` / `ato` / `identity_burst` are never mapped. Rail is a constant `upi_like`. **Not a threshold bug.** Do not tune on SAML-D labels. Phase D: **stop** unless a translation defect is proven with a regression test.

---

## 7. Defects that were real (evaluation honesty)

| ID | Defect | Status |
|----|--------|--------|
| B1 | Identical WITHOUT_STAMPS 0.579 | Fixed |
| B2 | `_app_ablation` toy retrain | Fixed |
| B3 | Seed-43 cache ignored `gtest_run_id` | Fixed |
| B4 | `__gtest` alias | Documented |
| B5 | `genuine_fp` vs `genuine_fp_over_eval` | Documented |
| B10 | Hub fan-in | Measured then exempted |
| E2 | Fold floor | Preflight |

**Never cite 0.579.** Never call `v1-train-46__gtest` independent confirmation.

---

## 8. How to reproduce the frozen 0.1% point

```bash
PYTHONPATH=. .venv/bin/python -c \
  "from packages.eval.internal_fpr_freeze import freeze_internal_01pct_fpr; freeze_internal_01pct_fpr()"
```

Writes `data/validation/v1/internal_01pct_fpr_freeze.json`. Does not retrain. Does not touch G-test labels for threshold selection.

Score the champion: `load_champion("v1-train-46__loopm-train")`. `model_freeze_id` must remain `e2f6cf866ddc8f053218e2d9bd460431c69a1d7e140effb1f88ddcd6dd55d009`.

---

## 9. What not to do next

* Do not retrain against `v1-gtest-48`.
* Do not pick thresholds on G-test or SAML-D.
* Do not promote a model that wins FPR but loses identity-burst or cost.
* Do not claim internal recall as SAML-D or India.
* Do not swap the estimator class in a last-minute pass.
* If you change the adapter, add a regression test, re-score the **frozen** champion, then compare internal 0.1% recall + family AP **before** any retrain.

---

## 10. Document index

| Doc | Role |
|-----|------|
| [`FROZEN-MODEL.md`](FROZEN-MODEL.md) | **Only** the frozen champion’s numbers |
| [`DEFENSE.md`](DEFENSE.md) | Official technical defense |
| [`../agent/final-v1-metrics.md`](../agent/final-v1-metrics.md) | Exhaustive scorecard + SAML-D |
| [`../agent/champions.md`](../agent/champions.md) | Version table |
| [`../agent/final_validation_report.md`](../agent/final_validation_report.md) | Wave 0–1 iteration log |
| [`../agent/kb.md`](../agent/kb.md) | Priority order (FPR → recursive family loop → features) |

Machine artifacts under `data/validation/v1/`: `internal_01pct_fpr_freeze.json`, `photography_day.json`, `pareto_gtest48.json`, `pareto_genuine_fpr.json`, `pareto_operational_v1.json`, `h9_ablation_audit.json`, `h6_diagnosis.json`, `h5c_fpr_v2_eval.json`, `saml_d_forensics.json`, `stage4_saml_d_loopm.json`, `champion_registry.json`.
