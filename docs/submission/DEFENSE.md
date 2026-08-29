# Technical Defense — Fraud Detection System

**Champion:** `v1-train-46__loopm-train` (sklearn `HistGradientBoostingClassifier`, evaluation-gated family-targeted retraining)  
**Evaluation:** Internal G-test `v1-gtest-48` (seed 48) unless labelled otherwise  
**This is a technical defense, not a research paper.**

> **One-line:** We built an evaluation-gated fraud detection pipeline that achieves ~98.7% recall at a 0.1% genuine false-positive rate on our internal test world, while explicitly testing and rejecting improvements that trade away fraud-family performance or operational cost.

---

## 1. Executive summary

The system scores payment events for fraud and then **acts**: allow, notify, step-up, hold, decline, or restrict credit on a mule payee. Detection without an action layer is not an operational detector.

It combines:

* causal event-time features (velocity, timing, payee/graph, amounts, session stamps);
* a multiclass `HistGradientBoostingClassifier` producing a fraud score;
* an **FPR-constrained operating threshold** (not the default low threshold);
* a rule/policy layer (`brake`) that maps family + score + rule hits → action;
* an evaluation-gated improvement loop that only keeps a candidate if family AP, genuine FPR, and cost do not collapse.

**Provisional champion:** Loop M (`v1-train-46__loopm-train`).

### Headlines — Internal G-test only

> **98.7% fraud recall at 0.1% genuine false-positive rate**

> **99.8% fraud recall at 1% genuine false-positive rate**

These are **internal G-test** numbers on frozen seed 48. They are **not** production, **not** real-world, and **not** SAML-D.

A second, stricter claim: the 0.1% FPR **threshold was selected on training `inner_val` only**, then evaluated once on the G-test eval fold: **98.52% recall at 0.032% genuine FPR**. See §5.

---

## 2. System architecture

```text
Transaction stream (simulator or SAML-D adapter)
        ↓
Feature construction (causal at event time t)
        ↓
Behavioral / temporal / graph / amount / session signals
        ↓
HistGradientBoostingClassifier (multiclass family probabilities)
        ↓
Fraud score  (1 − P(normal), calibrated)
        ↓
FPR-constrained operating threshold  (detect_thr)
        ↓
Predicted family + rule hits
        ↓
Action policy (brake)
        ↓
Allow / Notify / Step-up / Hold / Decline / Mule credit-restrict
```

The system is not `transaction → binary classifier`. It is:

> transaction → behavioral representation → fraud score → operating-point decision → risk-aware action

---

## 3. Fraud families (internal evaluation)

Full-world `v1-gtest-48` photography. AP is a ranking metric (independent of `detect_thr`).

| Fraud family | Evaluation positives | AP |
|--------------|--------------------:|---:|
| App fraud | 1,572 | 0.983 |
| ATO | 395 | 0.533 |
| Identity burst | 1,542 | 0.967 |
| Invoice fraud | 747 | 1.000 |
| Mule | 3,162 | 0.995 |

Source: [`photography_day.json`](../../data/validation/v1/photography_day.json) Loop M block.

ATO is the weakest family (ranking). It is still caught at high recall under the FPR-constrained threshold (eval-fold recall 88.7% at the frozen 0.1% op; full-world Pareto identity/mule remain >98% at 0.1% FPR).

---

## 4. Model evolution

| Model | `model_run_id` | Binary AP | Genuine FPR (default thr) | Cost sketch |
|-------|----------------|----------:|--------------------------:|------------:|
| Stage 1 | `v1-train-46` | 0.879 | 8.79% | 0.486 |
| Stage 2 | `v1-train-46-stage2` | 0.866 | 7.54% | 0.553 |
| **Loop M** | **`v1-train-46__loopm-train`** | **0.996** | 8.07%* | **0.011** |

\*Default `detect_thr` (~8% genuine FPR) is **not** the headline operating result. It is the training-time detection threshold. The system is evaluated at an **FPR-constrained** threshold (§5).

Stage 2 (AP-oriented Optuna) did not beat Stage 1 on AP or cost. Loop M did — mainly by lifting identity-burst ranking and collapsing operational cost.

---

## 5. Main result — FPR / recall Pareto

**Internal G-test `v1-gtest-48`.** Artifact: [`pareto_gtest48.json`](../../data/validation/v1/pareto_gtest48.json).

| Genuine FPR cap | Stage 1 recall | Loop M recall |
|----------------:|--------------:|--------------:|
| 5% | 96.3% | **99.9%** |
| 2% | 94.8% | **99.9%** |
| 1% | 87.9% | **99.8%** |
| 0.5% | 84.7% | **99.7%** |
| 0.1% | 83.1% | **98.7%** |

```text
Recall
100% ┤                    ● Loop M
 99% ┤              ●─────
 95% ┤
 90% ┤
 85% ┤ ● Stage 1
 80% ┤
     └──────────────────────────────
       0.1   0.5    1     2     5
                 Genuine FPR %
```

**Loop M dominates Stage 1 across the evaluated FPR range on the internal G-test.**

The operating point to highlight:

> **98.7% recall while constraining genuine false positives to ≤ 0.1%.**

A detector that flags almost every transaction can “catch everything” and is operationally useless. This curve shows high recall **under a tight FPR cap**.

### Protocol freeze (threshold not chosen on G-test)

| Step | Detail |
|------|--------|
| Select | `inner_val` of `v1-train-46` only (42,399 rows) |
| Rule | max recall subject to genuine FPR ≤ 0.1% |
| Selected `detect_thr` | **0.9152** |
| Evaluate once | time-cut **eval fold** of `v1-gtest-48` |
| Result | **98.52% recall @ 0.032% genuine FPR**, precision 98.57% |

Artifact: [`internal_01pct_fpr_freeze.json`](../../data/validation/v1/internal_01pct_fpr_freeze.json).

Later confirmatory sweep (`pareto_genuine_fpr.json`) on **full** gtest-48: 99.57% / 99.47% / **98.67%** recall at 1% / 0.5% / 0.1% FPR. Same dominance; slightly more conservative at 1% than the 5-point curve above.

---

## 6. Identity-burst

**Identity-burst AP = 0.967** on full `v1-gtest-48`.

In the simulator this family is **fan-in / burst** shaped (many inbound payments in a short window), not APP session-stamp shaped. Ablation shows **temporal** and **graph** groups drop binary AP by ~0.31 when zeroed at score time. That is why behavioral/temporal features matter: identity-burst is a timing-and-graph problem, not a GSTIN checksum problem.

At the 1% FPR envelope, identity-burst **recall** is **99.8%**.

---

## 7. Mule detection

**Mule AP = 0.995** (n = 3,162 on G-test — comparable; earlier museum v0 had n=29, not comparable).

Mule is not only a score. Predicted mule (or mule rule hit) maps to **`mule_credit_restrict`**: restrict credit on the payee rather than silently declining the payer’s app session.

**Hub investigation (high volume ≠ mule):**

* Legitimate high-volume hubs (`VID-SIM-HUB-*`) exist in the v1 worlds.
* Wave 0: 31 hub rows received mule restriction / hard-flag at `fan_in_1h ≥ 6`.
* Hub exemption: `mule-fan-in-burst` does not fire on hub payees.
* After exemption: hub `mule_credit_restrict` = **0** on gtest-48 and gtest-49.
* Loop M **model scores unchanged** (Brake-only change).

This does **not** mean all hub behavior is solved. It shows the action layer can exempt expected merchant fan-in without retraining.

---

## 8. Cost sketch

| Model | Cost sketch |
|-------|------------:|
| Stage 1 | 0.486 |
| Stage 2 | 0.553 |
| **Loop M** | **0.011** |

Weights: missed fraud = 10; FP notify = 1; FP hold = 3; FP decline = 8.

This is a **simulation cost sketch / relative operational cost**, **not** Indian banking monetary loss.

Loop M reduces simulated operational cost by ~44× vs Stage 1 while keeping very high fraud recall. At the **tight 0.1% FPR freeze**, cost rises to **0.149** (more misses, fewer FPs) — the expected recall/FPR trade.

---

## 9. Action distribution

Loop M on full `v1-gtest-48` (default op; 394,954 events):

| Action | Count |
|--------|------:|
| allow | 383,922 |
| mule_credit_restrict | 4,468 |
| notify | 4,104 |
| hold | 1,980 |
| decline | 381 |
| step_up | 99 |

The pipeline does not end at `P(fraud) = X`. `brake` maps predicted family + score + rule hits to an action enum. APP never silent-declines. ATO may decline. Mule → credit restrict.

---

## 10. Ablation / robustness

Frozen-champion ablation: **zero the named columns at scoring time** on the **same** fitted model. Do **not** refit a toy model.

| Model | Without stamps AP |
|-------|------------------:|
| Stage 1 | **0.717** |
| Stage 2 | **0.549** |
| Loop M | **0.844** |

The old **0.579 identical-across-models** result is **obsolete** and must not appear. It was a measurement defect (toy retrain / shared path).

H9 group ablation on Loop M (gtest-48, Δ binary AP vs 0.996 baseline):

| Group zeroed | Δ AP |
|--------------|-----:|
| temporal | −0.313 |
| graph | −0.308 |
| app/session flags | −0.117 |
| velocity | −0.068 |
| merchant/amount | −0.060 |
| stamps | −0.040 |

---

## 11. Validation / defect-defense

The evaluation pipeline was audited, not only the model.

| Defect | Resolution |
|--------|------------|
| Frozen-champion ablation incorrectly refit a toy model (identical 0.579) | Fixed — per-model 0.717 / 0.549 / 0.844 |
| Seed-43 cache could ignore G-test run ID | Fixed |
| Loop M `__gtest` alias is byte-identical to gtest-48 | Documented — not an independent holdout |
| `genuine_fp_over_eval` vs `genuine_fp` naming | Documented |
| Hub fan-in rule on legitimate hubs | Measured (31) then exempted (0) |
| E2 fold-floor failure (seed 50 `inner_val.ato=0`) | Preflight guard before fit |

---

## 12. Loop M — what it actually does

Not a marketing name. It is **class-conditional training-set augmentation** with a **hard promote/reject gate**.

```text
Fit baseline HistGradientBoostingClassifier
     ↓
Score G-dev; identify weakest fraud family (by AP, n_pos ≥ floor)
     ↓
Simulate extra events of that family only (same engine scale)
     ↓
Append extras to train (capped fraction; new event IDs; timestamps jittered into train calendar)
     ↓
Refit the same estimator class
     ↓
Evaluate on G-dev vs previous champion
     ↓
Accept only if family AP, genuine FPR, and cost gates pass
```

Improvement is **not** accepted merely because binary AP increased. Gates include recall, genuine FPR, family AP (especially identity-burst and mule), cost sketch, and ablation.

Recursive protocol (H7): max 3 rounds; promote/reject **each round on `v1-gdev-47`**; `v1-gtest-49` confirmatory **once** after the loop. Frozen `v1-gtest-48` is never used to promote.

---

## 13. Hyperparameter optimization (Optuna)

Optuna (TPE sampler) searches `HistGradientBoostingClassifier` hyperparameters on **inner_fit / inner_val only**. It never sees G-dev, G-test, or SAML-D labels.

Search space includes: `learning_rate`, `max_iter`, `min_samples_leaf`, `l2_regularization`, `max_bins`, and either `max_leaf_nodes` or `max_depth`.

**Optuna does not guarantee the best model.** It produces candidates. Independent evaluation gates decide whether a candidate is acceptable. Stage 2 (AP-oriented) and H5c (FPR-constrained Optuna → `v1-train-46__fpr-v2`) both lost to Loop M on those gates.

---

## 14. What failed

### Hard-negative mining (`v1-train-46__hn-train`) — REJECTED

| Metric | Before | After (gtest-49) |
|--------|--------|-------------------|
| Genuine FPR | 8.12% | **6.74%** |
| identity_burst AP | 0.958 | **0.364** |
| Cost sketch | 0.009 | **0.368** (~40×) |

Mined “hard” normals were 91% `is_new_payee`. Identity-burst fraud is fan-in/burst shaped (`fan_in_1h` ≈ 58). The retrain suppressed the wrong pattern.

**Lesson:** lowering FPR in isolation is not sufficient.

### FPR-only retraining (`v1-train-46__fpr-v2`) — REJECTED

Optuna 25 trials, inner_val FPR objective, expanded HGB search.

| Gate (gdev-47) | Loop M | FPR-v2 |
|----------------|--------|--------|
| Pareto recall @ 1% | **99.59%** | 99.38% |
| Pareto recall @ 0.1% | **98.43%** | 96.19% |
| identity_burst AP | **0.988** | 0.908 |
| Cost sketch | **0.002** | 0.663 |

Confirmatory gtest-49: same pattern. **Do not promote.** Loop M was selected by a **multi-metric gate**, not by being the newest model.

---

## 15. Champion selection

> **Champion: `v1-train-46__loopm-train`**

Rule: FPR-constrained recall → mule ranking → frozen-champion ablation → operational cost → regression gates.

This is the **current validated / provisional champion**. It is not claimed to be globally optimal.

Frozen operating threshold for ≤0.1% genuine FPR: **`detect_thr = 0.9152`**.

---

## 16. Main results slide

### LOOP M — INTERNAL G-TEST (`v1-gtest-48`)

| | |
|--:|:--|
| **98.7%** | Recall @ 0.1% genuine FPR |
| **99.8%** | Recall @ 1% genuine FPR |
| **0.996** | Binary AP |
| **0.995** | Mule AP |
| **0.967** | Identity-burst AP |
| **0.011** | Simulation cost sketch |

Protocol freeze (inner_val → eval fold once): **98.52% recall @ 0.032% genuine FPR**.

---

## 17. Claims we can make

* Loop M achieved ~98.7% recall at ≤0.1% genuine FPR on the internal G-test.
* Loop M dominates Stage 1 across the measured internal FPR Pareto curve.
* Loop M achieved ~0.996 binary AP on the internal G-test.
* Mule and identity-burst detection are strong on that world.
* The system produces risk-based actions, not just scores.
* The evaluation pipeline has explicit regression and rejection gates.
* Failed improvements were rejected when they caused collateral regressions.
* Frozen-champion ablation is a more honest robustness measurement than the obsolete 0.579 figure.

---

## 18. Claims we must not make

* “98.7% recall in the real world.”
* “Production-ready.”
* “Guaranteed fraud detection.”
* “Zero false positives.”
* “99.8% accuracy.” (recall-at-FPR is not accuracy)
* “The model is perfect.”
* “Optuna found the optimal model.”
* “SAML-D validates the internal 98.7% result.”
* “The simulator perfectly represents India.”
* “High-volume merchants can never be fraudulent.”
* “Loop M is universally optimal.”

---

## 19. Limitations

* Results are from the internal G-test simulation (seeds 46/47/48).
* Simulator behavior may not capture all real-world fraud.
* Some families (app, ATO, identity-burst) have no honest SAML-D analogue.
* SAML-D transfer is a **separate** generalization problem: ~1.96% TPR @ 0.1% FPR. Diagnosis: app/device/stamps unavailable; 98% of SAML-D positives score below the internal 0.1% threshold. **Do not treat SAML-D as confirmation of 98.7%.**
* Champion is a strong **prototype**, not a production deployment.
* Cost sketch is simulated/relative, not actual financial loss.

---

## 20. Final takeaway

The key achievement is not a high AP number. The system shows very high fraud recall under a strict false-positive constraint, combining model scoring, behavioral detection, mule reasoning, action policies, and evaluation-gated iterative improvement.

> **Current champion: Loop M — 98.7% recall @ 0.1% genuine FPR on the internal G-test.**

**Use only** `v1-train-46__loopm-train` with frozen `detect_thr = 0.9152` for the 0.1% FPR operating point.

Canonical artifacts: [`FROZEN-MODEL.md`](FROZEN-MODEL.md) · [`internal_01pct_fpr_freeze.json`](../../data/validation/v1/internal_01pct_fpr_freeze.json) · [`photography_day.json`](../../data/validation/v1/photography_day.json)
