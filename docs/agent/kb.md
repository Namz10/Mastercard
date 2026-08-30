# Big-Win Improvement Priorities

**Goal:** Improve classifier potency without chasing cosmetic metrics or burning time on low-impact experiments.

## Priority 1 — FPR-Constrained Optimization + Hyperparameter Tuning

**Objective:** Keep fraud recall extremely high while materially reducing genuine false positives.

Optimize:

> maximize recall subject to genuine FPR ≤ target

Evaluate at:

* 5%
* 2%
* **1%**
* 0.5%
* 0.1%

### Hyperparameter search

Run nested/controlled Optuna tuning against the operating objective, not AP alone.

Tune the HGB classifier's meaningful parameters, including:

* learning rate
* max leaf nodes / tree complexity
* max iterations
* minimum samples per leaf
* L2 regularization
* `max_bins` (sklearn HGB; no `max_features` on HGB — verify pinned sklearn)

Optuna runs on **inner_fit / inner_val only** — never G-dev, never G-test, never SAML-D labels.

Primary objective:

> maximize recall at the chosen FPR constraint

Secondary checks:

* binary AP
* identity_burst AP
* mule AP
* cost sketch
* WITHOUT_STAMPS performance

**Acceptance rule:** A candidate is only promoted if it improves the operating objective without causing a major regression in important fraud families.

---

## Priority 2 — Recursive Targeted Loop M

Turn Loop M from a one-shot correction into an **automated weakness → correction → validation loop**.

### Loop

1. Identify the weakest important fraud family.
2. Inspect its false negatives and confusing legitimate examples.
3. Generate targeted additional positives and/or behavioral variants.
4. Generate realistic hard negatives where appropriate.
5. Retrain.
6. **Evaluate on G-dev (`v1-gdev-47`)** — promote/reject this round against prior champion.
7. Compare Pareto (recall @ fixed FPR) on G-dev only.
8. Promote only if operating objective improves without family/cost regressions.
9. Repeat for **max 3 rounds** (hard cap).

**After loop terminates:** one-shot confirmatory score on **`v1-gtest-49` only**. Frozen **`v1-gtest-48` photograph is never used for promote/reject decisions** (instrumentation compare OK, not tuning).

### Guardrails

* Never modify the frozen final test set.
* Never train on test examples.
* Never tune directly on the final test set.
* No seed-43 museum contamination.
* No estimator swapping during this improvement pass.
* No metric cherry-picking.
* No promotion based on AP alone.
* Reject any candidate with severe regression in another important fraud family.
* Reject candidates that improve FPR only by destroying recall.
* Every round must produce a reproducible artifact and comparison against the previous champion.

### Promotion objective

Prefer:

> **lower genuine FPR + very high recall + lower operational cost**

rather than:

> maximum AP.

---

## Priority 3 — Targeted Behavioral Features

Only investigate features that attack genuine weaknesses in the fraud behavior.

Highest-value areas:

* transaction velocity
* inter-event timing
* acceleration/burstiness
* customer behavioral history
* payee history
* money-in → money-out timing
* sender/payee relationship stability
* graph-lite transaction behavior
* account/device/payee changes

Do not add features merely because they increase lab AP.

---

## Priority 4 — Systematic Ablation / Leakage Audit

Verify that performance is not coming from simulator shortcuts.

Ablate:

* stamps
* app flags
* velocity
* merchant features
* temporal features
* customer history
* graph features
* suspiciously powerful individual features

A feature is considered valuable only if its contribution is defensible and performance does not collapse when obvious shortcuts disappear.

---

# Execution Order

### FIRST

**Optuna + FPR-constrained optimization**

### SECOND

**Recursive targeted Loop M**

### THIRD

**Behavioral/graph-lite feature improvements**

Everything else is lower priority unless these experiments expose a specific defect.

## Final promotion rule

A new champion must demonstrate:

**Higher recall at the same FPR OR lower FPR at the same recall**

while maintaining acceptable:

* fraud-family AP
* cost sketch
* ablation robustness
* no leakage
* no test contamination

If an experiment produces a prettier single metric but violates these conditions, **reject it.**


I'm sure about the strategic conclusion, but not about saying there are zero huge wins left.

Based strictly on everything you've shown me:

Loop M is genuinely strong internally.
The 0.1% FPR / 98.7% recall result is very promising.
The failed H6 and H5c experiments show that blindly optimizing FPR can damage the classifier.
SAML-D transfer is still the major weakness.
So I would not risk the current champion with random new training changes right before submission.

The one thing I would absolutely finish is:

Select the 0.1% FPR threshold on inner validation → freeze it → evaluate once on untouched test.

If that holds near 98%+ recall, that's a substantially cleaner headline than the current default 8.07% FPR.

After that: stop unless you have time for one targeted experiment. You already have enough strong evidence for a hackathon submission.

One correction to my earlier wording: 98.7% @ 0.1% FPR is not yet a guaranteed production operating point because your current Pareto number was measured from the evaluation curve. The threshold-selection protocol is what makes that claim defensible.
