# Agent knowledge base (append-only)

User-supplied priorities, context, and decisions. The autonomous validation loop **reads this file at the start of every cycle** (with `prompt.md`). Append new sections at the bottom — do not delete prior entries without noting why.

---

## 2026-08-29 — SAML-D transfer & improvement priorities

**Context:** Chase SAML-D transfer and lab FPR jointly. Optimize the operating problem, not AP alone.

### 1. FPR-constrained training/thresholding — #1 priority

Don't optimize AP alone. Optimize:

> maximize recall subject to genuine FPR ≤ X%

Run a **Pareto curve** at multiple FPR operating points, e.g.:

- 5% FPR
- 2%
- 1%
- 0.5%
- 0.1%

Then check whether Loop M **dominates** Stage 1 across the full curve. Very high recall at ~1% FPR would be a major upgrade.

### 2. Make Loop M recursive

Current: weakest family → add examples → retrain → evaluate.

Target loop:

> detect weakness → generate targeted hard negatives/positives → retrain → evaluate → find next weakness → repeat

Strict **max rounds** and an **untouched final test set**. Automated adversarial validation/improvement loop.

### 3. Hard-negative mining

High value for FPR. Find legitimate transactions scored highly:

> normal transaction + high fraud score = hard negative

Add to training. Teaches: *"This looks suspicious, but is actually legitimate."* More aligned with current weakness than generating more fraud.

### 4. Cross-world robustness

Avoid seed-48 specialist. Train/improve on one world; evaluate across 46 → 47 → 48 → 49 with different behavioral distributions.

Ideal protocol:

> train 46 → validate 47 → untouched test 48/49

Repeat with another seed. Strong cross-world performance makes headline metrics more convincing.

### 5. Feature ablation + leakage audit

Systematically ablate: stamps, app flags, velocity, merchant, temporal, customer history, graph, every suspiciously powerful feature.

Question: *Does the model still work when individual shortcuts disappear?*

### 6. Improve the simulator (long-term)

Simulator should deliberately produce:

- legitimate high-volume hubs
- legitimate burst behavior
- fraud that looks normal
- normal behavior that looks fraudulent
- overlapping fraud/normal distributions
- temporal drift
- unseen fraud patterns
- noisy/missing features
- changing fraud prevalence

> Make the simulator actively try to fool the classifier.

Yeah — these are the right kinds of improvements, but they are not all equally valuable.

The biggest ones I'd prioritize from this document are:

Hard-negative mining (H6) — probably the most direct way to reduce your current ~8% genuine FPR. Find legitimate transactions the model is incorrectly scoring highly, then train against those.
Payee-side / graph-lite features — especially important for mule detection: unique senders, money-in → money-out speed, payee age, payer/payee role stability. These attack the actual mule behavior rather than simulator-specific stamps.
Calibration + cost-based thresholding — this is huge for your current situation. Your model can have excellent recall but still produce too many false positives. Calibration makes the score meaningful, while cost-based threshold selection lets you explicitly trade missed fraud against false actions.
Temporal/behavioral features — particularly for ATO/identity and APP. Things like inter-event gaps, acceleration of activity, time since device/payee changes, etc. should make the classifier less dependent on static simulator artifacts.
Cross-world robustness — retrain on multiple seeds and measure variance. This tells you whether the impressive Loop M result is genuinely robust or partly a lucky world.

More valuable than easier fraud.
