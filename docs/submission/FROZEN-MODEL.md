# Peak frozen model — Loop M

**Use this model only.** Do not mix Stage 1, Stage 2, rejected v2, or museum seed-43 numbers into claims about the champion.

| Field | Value |
|-------|-------|
| Champion | `v1-train-46__loopm-train` |
| Status | Provisional champion (v1) |
| `model_freeze_id` | `e2f6cf866ddc8f053218e2d9bd460431c69a1d7e140effb1f88ddcd6dd55d009` |
| Train world | `v1-train-46` + Loop M family extras |
| Photography G-test | `v1-gtest-48` (seed 48, frozen) |
| Promote gate | `v1-gdev-47` |
| Confirmatory | `v1-gtest-49` (one shot) |
| Frozen 0.1% FPR threshold | **0.9151932016993464** (selected on `inner_val` of `v1-train-46` only) |

**Rejected — do not deploy or headline:**

| `model_run_id` | Why rejected |
|----------------|--------------|
| `v1-train-46__hn-train` | Hard-negative mining: identity_burst AP collapsed, cost exploded |
| `v1-train-46__fpr-v2` | FPR-only Optuna: identity_burst AP −8%, cost ~300× |

---

## Two numbers, two protocols (do not mix)

| Protocol | Split used to pick threshold | Evaluation | Genuine FPR | Recall | Use for |
|----------|-----------------------------|------------|-------------|--------|---------|
| **Protocol freeze** | `inner_val` on train-46 (never G-test) | **Eval fold** of gtest-48, once | **0.032%** | **98.52%** | Honest operating-point claim |
| **Pareto envelope** | Score sweep on G-test scores (diagnostic) | Full gtest-48 | 0.098–0.100% | **98.67%** | Frontier / slide headline |

The **98.7% @ 0.1% FPR** slide number is the Pareto envelope on full `v1-gtest-48` (`pareto_genuine_fpr.json` / `pareto_gtest48.json`). It is **internal G-test**, not production, not SAML-D.

The **protocol freeze** is the number you can defend as “threshold was not chosen on the test set.”

Artifact: [`data/validation/v1/internal_01pct_fpr_freeze.json`](../../data/validation/v1/internal_01pct_fpr_freeze.json)

---

## Protocol freeze @ genuine FPR ≤ 0.1%

Threshold: max recall on **inner_val** (42,399 rows; 818 fraud) subject to genuine FPR ≤ 0.1%. Then scored **once** on the time-cut **eval fold** of `v1-gtest-48`.

| Metric | Frozen op | Legacy default `detect_thr` |
|--------|-----------|------------------------------|
| `detect_thr` | **0.9152** | 0.000546 |
| Genuine FPR | **0.0318%** (57 / 179,049) | 4.00% |
| Recall | **98.52%** (3,917 / 3,976) | 99.97% |
| Precision | **98.57%** | 35.69% |
| Binary AP | 0.9985 | 0.9985 |

Confusion: TN 178,992 · FP 57 · FN 59 · TP 3,917.

### Family recall @ frozen op (eval fold)

| Family | n | AP | Recall @ 0.9152 |
|--------|--:|---:|----------------:|
| app_fraud | 726 | 0.990 | 98.48% |
| ato | 150 | 0.056 | 88.67% |
| identity_burst | 1,018 | 0.984 | 98.53% |
| invoice_fraud | 326 | 1.000 | 100.0% |
| mule | 1,756 | 0.994 | 99.09% |

**ATO AP 0.056 on the eval fold is a ranking metric on a 150-positive slice; do not confuse with 88.7% recall at the frozen threshold.** Full-world photography ATO AP is 0.533 (see below).

### Actions @ frozen op (eval fold)

| Action | Count |
|--------|------:|
| allow | 177,906 |
| notify | 1,782 |
| mule_credit_restrict | 2,505 |
| hold | 761 |
| step_up | 64 |
| decline | 7 |

Cost sketch (simulation / relative, not Indian rupees): **0.149** at this tight FPR (FN rate 1.48%).

---

## Full-world photography (`v1-gtest-48`, all rows)

Source: [`photography_day.json`](../../data/validation/v1/photography_day.json). **Default op uses legacy `detect_thr` (~8% genuine FPR). Do not headline that FPR.** Ranking metrics (AP) do not depend on the operating threshold.

| Metric | Loop M |
|--------|--------|
| Binary AP | **0.9956** (report **0.996**) |
| identity_burst AP | **0.9667** (report **0.967**) |
| mule AP | **0.9946** (report **0.995**) |
| invoice_fraud AP | 0.9999 |
| app_fraud AP | 0.983 |
| ato AP | 0.533 |
| Genuine FPR @ default op | 8.07% |
| Recall @ default op | 99.99% |
| Cost sketch @ default op | **0.011** |
| Without stamps AP | **0.844** |
| Without app flags AP | 0.242 |

### Full-world positives

| Family | n |
|--------|--:|
| app_fraud | 1,572 |
| ato | 395 |
| identity_burst | 1,542 |
| invoice_fraud | 747 |
| mule | 3,162 |
| normal | 387,536 |

### Full-world action histogram (default op)

| Action | Count |
|--------|------:|
| allow | 383,922 |
| mule_credit_restrict | 4,468 |
| notify | 4,104 |
| hold | 1,980 |
| decline | 381 |
| step_up | 99 |

---

## Pareto envelope (full gtest-48)

**H5 5-point curve** — [`pareto_gtest48.json`](../../data/validation/v1/pareto_gtest48.json)

| Genuine FPR cap | Stage 1 recall | **Loop M recall** | Loop M genuine FPR |
|----------------:|---------------:|------------------:|--------------------:|
| 5% | 96.25% | **99.95%** | 4.99% |
| 2% | 94.77% | **99.89%** | 1.99% |
| 1% | 87.95% | **99.81%** | 0.99% |
| 0.5% | 84.69% | **99.66%** | 0.49% |
| 0.1% | 83.15% | **98.68%** | 0.100% |

**H5b confirmatory sweep** (later, `max_recall_at_genuine_fpr`) — [`pareto_genuine_fpr.json`](../../data/validation/v1/pareto_genuine_fpr.json)

| Cap | Loop M recall | identity_burst recall | mule recall |
|----:|--------------:|----------------------:|------------:|
| 1% | 99.57% | 99.81% | 99.62% |
| 0.5% | 99.47% | 99.81% | 99.46% |
| 0.1% | **98.67%** | 98.90% | 99.11% |

Slide headline uses **98.7% @ 0.1%** and **99.8% @ 1%** from the H5 5-point curve. H5b is the tighter later measurement at 1% (**99.57%**). Both dominate Stage 1.

---

## What this model is not

- Not production-ready, not real-world India, not SAML-D.
- SAML-D TPR @ 0.1% FPR is **1.96%** (feature starvation / domain shift — see handoff).
- Default `detect_thr` 0.000546 is **not** the frozen operating point.
- Stage 1 / Stage 2 / v2 numbers are baselines or rejects, not this champion.
