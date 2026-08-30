# v1 Loop M — Final Model Scorecard

**Submission pack (use this champion only):** [`docs/submission/DEFENSE.md`](../submission/DEFENSE.md) · [`FROZEN-MODEL.md`](../submission/FROZEN-MODEL.md) · [`HANDOFF.md`](../submission/HANDOFF.md)

**Champion:** `v1-train-46__loopm-train`  
**Status:** Provisional champion (v1, post–autonomous validation loop)  
**Generated:** 2026-08-29  
**Primary artifact:** [`data/validation/v1/internal_01pct_fpr_freeze.json`](../data/validation/v1/internal_01pct_fpr_freeze.json)

> **Scope disclaimer:** All metrics in Sections 1–6 are **internal simulator performance** on frozen seeds 46/47/48. They are **not** SAML-D or other external transfer results. External numbers are isolated in Section 7.

---

## 1. Champion identity

| Field | Value |
|-------|-------|
| `model_run_id` | `v1-train-46__loopm-train` |
| Train world | `v1-train-46` + Loop M hard-positive / hard-negative rounds |
| Promote gate | Family AP + FPR ε on `v1-gdev-47` |
| Confirmatory holdout | `v1-gtest-49` (one shot after loop) |
| Photography holdout | `v1-gtest-48` (frozen; not used for promote/tune) |
| `model_freeze_id` | `e2f6cf866ddc8f053218e2d9bd460431c69a1d7e140effb1f88ddcd6dd55d009` |
| Feature count | 37 raw columns |
| Registry | [`docs/agent/champions.md`](champions.md), [`data/validation/v1/champion_registry.json`](../data/validation/v1/champion_registry.json) |

**Rejected successors (do not deploy):**

| Version | `model_run_id` | Reject reason |
|---------|----------------|---------------|
| v2 FPR-tuned | `v1-train-46__fpr-v2` | identity_burst AP −8%, cost ~300× worse |
| v2 HN | `v1-train-46__hn-train` | H6 generic hard negatives — family/cost collapse |

---

## 2. Frozen operating point @ 0.1% genuine FPR (deployment reference)

Threshold selected on **`inner_val` of `v1-train-46` only** (42,399 rows). Evaluated **once** on the **`eval` fold** of `v1-gtest-48` (time-cut protocol). No test-set threshold tuning.

| Metric | Value |
|--------|-------|
| **Selected `detect_thr`** | **0.9152** |
| Threshold selection split | `inner_val` on `v1-train-46` |
| Inner-val recall @ cap | 100.0% |
| Inner-val genuine FPR @ cap | 0.0072% |
| Legacy default `detect_thr` | 0.000546 |

### G-test eval-fold results (`v1-gtest-48`, eval fold only)

| Metric | Frozen @ 0.1% FPR | Legacy default op |
|--------|-------------------|-------------------|
| **Genuine FPR** | **0.032%** (57 / 179,049 normals) | 4.00% |
| **Recall @ op** | **98.52%** (3,917 / 3,976 fraud) | 99.97% |
| **Precision @ op** | **98.57%** | 35.69% |
| **Binary AP** | 0.9985 | 0.9985 |

**Acceptance gates:** genuine FPR ≤ 0.1% ✓ · no test threshold selection ✓ · no retrain ✓

Reference (post-hoc Pareto on **full** gtest-48, not used for selection): **98.67% recall @ 0.1% FPR**.

### Family AP @ frozen op (eval fold)

| Family | n | AP | Recall @ op |
|--------|---|-----|-------------|
| app_fraud | 726 | 0.990 | 98.48% |
| ato | 150 | 0.056 | 88.67% |
| identity_burst | 1,018 | **0.984** | **98.53%** |
| invoice_fraud | 326 | 1.000 | 100.0% |
| mule | 1,756 | **0.994** | **99.09%** |

### Confusion matrix @ frozen op

| | Predicted neg | Predicted pos |
|--|---------------|---------------|
| Actual normal | 178,992 | 57 |
| Actual fraud | 59 | 3,917 |

### Action histogram @ frozen op

| Action | Count |
|--------|------:|
| allow | 177,906 |
| notify | 1,782 |
| hold | 761 |
| mule_credit_restrict | 2,505 |
| step_up | 64 |
| decline | 7 |

### Cost sketch @ frozen op

| Field | Value |
|-------|-------|
| Unit | lab_not_india |
| Miss weight | 10.0 |
| FP notify / hold / decline weights | 1.0 / 3.0 / 8.0 |
| FN rate | 1.48% |
| **Expected cost** | **0.149** |
| FP action hist | allow 3 · hold 41 · mule_credit_restrict 12 · step_up 1 |

---

## 3. Full-world internal metrics (`v1-gtest-48`, all rows)

From frozen photography day — headline numbers for stakeholder comparison. **Default op** uses legacy `detect_thr`; use Section 2 for FPR-constrained deployment.

| Metric | Loop M (`v1-train-46__loopm-train`) | Stage 1 baseline (`v1-train-46`) |
|--------|-------------------------------------|-----------------------------------|
| Binary AP | **0.996** | 0.879 |
| Genuine FPR (default op) | 8.07% | 8.79% |
| Recall @ default op | 99.99% | 95.20% |
| identity_burst AP | **0.967** | 0.337 |
| mule AP | **0.995** | 0.996 |
| invoice_fraud AP | 1.000 | 1.000 |
| ato AP | 0.533 | 0.546 |
| Cost sketch (default op) | **0.011** | 0.486 |

Artifact: [`data/validation/v1/photography_day.json`](../data/validation/v1/photography_day.json)

### Post-hoc Pareto envelope (full gtest-48, diagnostic only)

Thresholds chosen **after** seeing test scores — **not** the protocol freeze. Useful for understanding the score frontier.

| FPR target | Threshold | Genuine FPR | Recall | identity_burst recall | mule recall |
|------------|-----------|-------------|--------|----------------------|-------------|
| 1.0% | 0.0227 | 0.93% | **99.57%** | 99.80% | 99.62% |
| 0.5% | 0.3022 | 0.43% | 99.47% | 99.81% | 99.46% |
| **0.1%** | 0.9214 | 0.098% | **98.67%** | 98.90% | 99.11% |

Artifacts: [`pareto_operational_v1.json`](../data/validation/v1/pareto_operational_v1.json), [`pareto_genuine_fpr.json`](../data/validation/v1/pareto_genuine_fpr.json)

---

## 4. Development world (`v1-gdev-47`)

| Metric | Default op | Pareto @ 1% FPR | Pareto @ 0.1% FPR |
|--------|------------|-----------------|-------------------|
| Genuine FPR | 7.87% | 0.99% | 0.099% |
| Recall | 100.0% | 99.59% | 98.43% |
| identity_burst recall | — | 99.81% | 98.64% |
| mule recall | — | 99.53% | 98.65% |
| Cost sketch proxy | 0.077 | 0.051 | 0.158 |

### H7 round-1 weakness diagnostic

| Family | gdev AP | Notes |
|--------|---------|-------|
| ato | **0.537** | Weakest family (n=398) |
| identity_burst | 0.939 | |
| mule | 0.992 | |
| app_fraud | 0.985 | |
| invoice_fraud | 1.000 | |

91% of mined hard negatives are `is_new_payee`-driven (H6-D). Artifact: [`h7_round1_diagnosis.json`](../data/validation/v1/h7_round1_diagnosis.json)

---

## 5. Feature ablation (frozen champion, no retrain)

Internal diagnostic on `v1-gtest-48`. Largest AP drops when zeroing groups:

| Group zeroed | Δ binary AP (gtest-48) | Interpretation |
|--------------|--------------------------|----------------|
| **temporal** | **−0.313** | hours_since_*, account_age |
| **graph** | **−0.308** | fan-in/out asymmetry, payee graph |
| app_flags | −0.117 | call/paste/pause/urgency |
| velocity | −0.068 | burst, fan in/out windows |
| stamps | −0.040 | beneficiary/GSTIN/lookalike rules |
| merchant | −0.060 | amount_vs_p30/7d |

Without stamps baseline AP: 0.844. Without app flags: 0.878.  
Artifact: [`h9_ablation_audit.json`](../data/validation/v1/h9_ablation_audit.json)

**SAML-D implication:** device/app flags and stamps are **unavailable** on external data (forced false). Internal ablation predicts a large transfer gap from these groups alone.

---

## 6. App / stamp sensitivity (photography)

| Ablation | identity_burst proxy (app flags AP) |
|----------|-------------------------------------|
| with_app_flags | 0.983 |
| without_app_flags | 0.242 |
| without_stamps (full model) | 0.844 |

Loop M's identity_burst lift is heavily app-session dependent internally.

---

## 7. SAML-D external transfer (separate evaluation)

> **Not internal performance.** Scored with frozen champion; eval slice = last 1/3 calendar (~3.14M rows). Do not compare `binary_ap` to internal G-test AP.

### Headline TPR @ FPR (from full 3.14M eval pass)

| FPR target | TPR | Threshold (SAML-D negatives) |
|------------|-----|------------------------------|
| **0.1%** | **1.96%** | 0.974 |
| 0.5% | 3.05% | 0.947 |
| 1.0% | 3.91% | 0.909 |

Default op on SAML-D (legacy thr 0.000546): recall 41.0%, binary AP 0.002 — misleading; scores are miscalibrated externally.

Artifact: [`stage4_saml_d_loopm.json`](../data/validation/v1/stage4_saml_d_loopm.json)

### Label mapping on SAML-D eval slice

| Mapped family | n positives |
|---------------|------------:|
| mule | 3,084 |
| unmapped | 369 |
| invoice_fraud | 22 |
| normal | 3,141,065 |

Families **never mapped:** `app_fraud`, `ato`, `identity_burst` (forbidden by protocol).

### Score distribution diagnosis (500k eval sample)

| Cohort | p50 | p90 | p99 |
|--------|-----|-----|-----|
| SAML-D positives | 0.00042 | 0.011 | 0.967 |
| SAML-D negatives | 0.00040 | 0.505 | 0.912 |

| Diagnostic | Value |
|------------|-------|
| Fraction positives below internal 0.1% thr (0.915) | **98.2%** |
| Fraction negatives above internal 0.1% thr | 0.93% |
| **Classification** | **Case A — fraud receives near-zero scores** |

### Feature coverage on SAML-D

| Group | Internal | SAML-D | Comparable? |
|-------|----------|--------|-------------|
| velocity | ✓ | ✓ replay | Yes |
| temporal | ✓ | ✓ replay | Yes |
| customer_history | ✓ | ✓ replay | Yes |
| merchant_payee | ✓ | ✓ replay | Yes |
| graph | ✓ | ✓ replay | Yes |
| amount | ✓ | ✓ replay | Yes |
| behavioral | ✓ | ✓ replay | Yes |
| account_level | ✓ | ✓ replay | Yes |
| transaction_level | ✓ | ✓ (rail=`upi_like` constant) | Partial |
| **device_app** | ✓ | **✗ stubbed** | **No** |
| **stamps** | ✓ | **✗ stubbed** | **No** |

Full forensics: [`saml_d_forensics.json`](../data/validation/v1/saml_d_forensics.json)

---

## 8. Root-cause classification (Phase C gate)

| Rank | Suspected cause | Evidence |
|------|-----------------|----------|
| **Confirmed** | APP/device/session stamps unavailable | Forced false in SAML-D adapter; −0.12 AP internally when zeroed |
| **Confirmed** | identity_burst / app_fraud / ato unmapped | No SAML-D laundering type maps to these families |
| **Strongly supported** | Score distribution / feature starvation (Case A) | 98.2% SAML-D positives score below internal 0.1% thr; median pos score ≈ 0.0004 |
| **Strongly supported** | Rail ontology analogue | All payments mapped to `upi_like` constant |
| **Plausible** | Unmapped laundering types (369 eval positives) | Behavioural_Change_*, Single_large, etc. |
| **Plausible** | Genuine domain shift | Real bank transactions vs synthetic sim |
| **Unsupported** | Threshold retuning on SAML-D alone fixes transfer | Case A dominates; calibration shift is secondary |

**Verdict:** Transfer weakness is primarily **feature mismatch + starvation** (missing app/stamp signal the model relies on for identity_burst), not a fixable threshold bug. **Do not retrain** until translation defects are addressed or domain-shift intervention is narrowly scoped.

**Phase D status:** STOP — no high-confidence translation fix identified beyond documenting unavailable features. Next evidence-backed step: targeted adapter work for causal replay validation + regression tests, then re-score frozen champion.

---

## 9. Evaluation protocol summary

| Rule | Status |
|------|--------|
| Threshold from train/val only | ✓ `inner_val` on seed-46 train world |
| Single untouched G-test eval for freeze | ✓ eval fold of gtest-48 |
| No SAML-D label tuning | ✓ forensics diagnostic only |
| No retrain for freeze | ✓ frozen champion weights |
| Seeds 46/47/48 frozen | ✓ |
| gtest-48 not used in promote loop | ✓ |
| Rejected experiments retained | ✓ H5c, H6 in ledger |

---

## 10. Artifact index

| Artifact | Purpose |
|----------|---------|
| [`internal_01pct_fpr_freeze.json`](../data/validation/v1/internal_01pct_fpr_freeze.json) | **Canonical 0.1% FPR operating point** |
| [`photography_day.json`](../data/validation/v1/photography_day.json) | Full-world seed-48 headlines |
| [`pareto_operational_v1.json`](../data/validation/v1/pareto_operational_v1.json) | Operational Pareto (gdev/g48/g49) |
| [`pareto_genuine_fpr.json`](../data/validation/v1/pareto_genuine_fpr.json) | FPR envelope vs Stage 1 |
| [`saml_d_forensics.json`](../data/validation/v1/saml_d_forensics.json) | SAML-D transfer audit B1–B7 |
| [`stage4_saml_d_loopm.json`](../data/validation/v1/stage4_saml_d_loopm.json) | Full SAML-D scored eval |
| [`h9_ablation_audit.json`](../data/validation/v1/h9_ablation_audit.json) | Feature group ablation |
| [`h7_round1_diagnosis.json`](../data/validation/v1/h7_round1_diagnosis.json) | Loop M weakness (ato) |
| [`h6_diagnosis.json`](../data/validation/v1/h6_diagnosis.json) | Hard-negative mining diagnosis |
| [`h5c_fpr_v2_eval.json`](../data/validation/v1/h5c_fpr_v2_eval.json) | v2 FPR reject evidence |
| [`champion_registry.json`](../data/validation/v1/champion_registry.json) | Machine-readable champion record |

---

## 11. How to reproduce

```bash
# Phase A — freeze internal 0.1% FPR operating point
PYTHONPATH=. .venv/bin/python -c \
  "from packages.eval.internal_fpr_freeze import freeze_internal_01pct_fpr; freeze_internal_01pct_fpr()"

# Phase B — SAML-D forensics (requires data/externals/SAML-D.csv)
PYTHONPATH=. .venv/bin/python -c \
  "from packages.eval.saml_d_forensics import run_saml_d_forensics; \
   run_saml_d_forensics(frozen_thr=0.9151932016993464)"
```

---

## 12. Deployment recommendation

1. **Use `detect_thr = 0.9152`** (from inner_val @ FPR ≤ 0.1%) for production FPR-constrained operation — not the legacy 0.000546 default.
2. Expect **~98.5% recall @ ~0.03% genuine FPR** on internal eval fold; **~98.7% @ ~0.1% FPR** on full gtest-48 post-hoc reference.
3. Monitor **ato** family (weakest AP) and **identity_burst** cost at tight FPR.
4. Treat SAML-D **~2% TPR @ 0.1% FPR** as expected given missing app/stamp features until adapter fixes are validated — do not claim internal recall as external performance.
