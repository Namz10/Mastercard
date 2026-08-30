# Defense diagram prompts

Shared visual system for all four. Paste the **Style block** at the top of every prompt.

Do not use project slang (no “Loop M”, Wave, H5, gtest nicknames). Use the labels in each prompt.

---

## Style block (prepend to every prompt)

```
Visual system: McKinsey-style enterprise architecture slide, light mode.
Background: pure white #FFFFFF with a very faint cool-gray content well #F7F8FA.
Palette only: navy #0B1F33 for titles and primary boxes; steel #4A5A6A for secondary labels;
light fill #EEF2F5 for boxes; one accent only — McKinsey blue #0070AD for the critical path
and selected operating point. No gold, no neon, no gradients, no shadows, no 3D, no icons
that look like clip-art, no isometric, no glassmorphism, no dark mode.
Typography: clean grotesque sans (like Helvetica Neue / Inter). Title 18–22pt navy, all
sentence case. Body 9–11pt steel. No decorative bold except the one metric callout.
Layout: generous whitespace, aligned to a 12-column grid, hairline 1px navy-at-20% strokes,
rounded corners 2px only. Left-to-right then top-to-bottom. Numbered stages 01 02 03.
Every box has a short noun-phrase title and one 6–10 word subtitle. No arrows thicker than 1px.
No watermarks, no logos, no fake UI chrome. Photorealism forbidden — flat vector diagram only.
Text must be spelled correctly, English, fully readable. 16:9 landscape, print-ready.
```

---

## 1. Training pipeline

```
[PASTE STYLE BLOCK]

Title, top left: “Model training pipeline”
Subtitle: “Nested validation · hyperparameter search · family-targeted refit”

Draw a single horizontal swimlane diagram with five numbered stages, equal width, connected by thin rightward arrows.

01  Data generation
    Synthetic payment event stream
    Time-ordered events · five fraud families + genuine
    Output: labeled event table

02  Feature construction
    Causal features at event time t only
    Groups: velocity, inter-event timing, payee/graph, amount, session flags
    No future information · no technique-id leakage into X

03  Nested splits (critical — draw as a nested box, not a pie)
    Outer: train calendar vs held-out test world (never used here)
    Inside train calendar only:
      inner_fit  →  trees are grown
      inner_val   →  hyperparameter objective and threshold selection
    Caption under this stage: “Test world is not in the search”

04  HistGradientBoostingClassifier + Optuna
    Estimator: sklearn HistGradientBoostingClassifier (multiclass)
    Classes: genuine, app fraud, ATO, identity burst, invoice fraud, mule
    Optuna TPE on inner_fit / inner_val only
    Search: learning rate, boosting iterations, leaf size, L2, max bins,
            either max depth or max leaf nodes
    Inner_val further split A/B: fit probability calibrators on A, score on B
    Objective: recall at a genuine false-positive ceiling — not average precision alone
    Output: candidate fitted model + calibrated P(family)

05  Evaluation-gated refit (optional path, dashed border)
    Score development world → identify weakest fraud family by average precision
    Generate extra events of that family only · append to train (capped fraction)
    Refit the same estimator class
    Promote only if family AP, genuine FPR, and cost do not regress
    Reject path shown below stage 05 as a small steel box: “Candidate discarded”

Footer, small steel text:
“Champion is selected by gates, not by the newest trial.”

Do not write Loop M, Optuna as a trophy, or “AI.” Show Optuna as a search box inside stage 04.
```

---

## 2. Inference (scoring + action)

```
[PASTE STYLE BLOCK]

Title: “Inference path”
Subtitle: “Event → representation → score → operating point → action”

One left-to-right pipeline, seven boxes, single critical path in #0070AD. No branches except the final action enum.

01  Payment event
    Amount, parties, timestamp, rail

02  Feature vector at time t
    Same causal construction as training
    Velocity · timing · graph-lite · amounts · session flags (if present)

03  Multiclass classifier
    HistGradientBoostingClassifier (frozen weights)
    Output: P(genuine), P(app), P(ATO), P(identity burst), P(invoice), P(mule)

04  Fraud score
    score = 1 − P(genuine)
    After per-class isotonic calibration

05  Operating point
    Compare score to detect_threshold
    detect_threshold selected to maximize recall subject to genuine FPR ≤ 0.1%
    Selected on training inner_val only · not on the test world
    Callout in accent: “detect_thr = 0.915”

06  Family + rules
    Predicted family = argmax P(family)
    Rule hits evaluated on the live event (fan-in burst, session, invoice, …)
    Hub merchants exempt from the mule fan-in rule

07  Action policy
    Deterministic table, not a second model
    Six outcomes in a compact vertical stack to the right of 07:
      allow
      notify
      step-up authentication
      hold
      decline
      mule credit restrict
    Caption: “App fraud never silent-declines · mule restricts the payee”

Small footnote: “This is not transaction → binary yes/no.”
```

---

## 3. Validation pipeline

```
[PASTE STYLE BLOCK]

Title: “Validation and promotion”
Subtitle: “Separate worlds · one-way information flow · explicit reject”

Draw THREE vertical columns of equal height, labeled as worlds, with a one-way arrow left → right. Nothing flows backward.

Column A — Train world (seed 46)
  Fit HistGradientBoostingClassifier
  Optuna + threshold selection on inner_val only
  Optional family-targeted extra events
  Output: candidate model artifact (frozen weights + detect_threshold)

Column B — Development world (seed 47)
  Title: “Promote / reject gate”
  Score the candidate once per experiment
  Gates listed as a checklist (unchecked boxes, not green ticks except one):
    · Recall at genuine FPR ≤ 1% and 0.1%
    · Identity-burst average precision
    · Mule average precision
    · Simulation cost sketch
    · Frozen-champion ablation (zero feature groups at score time)
  Two exits at the bottom of column B:
    Accent path rightward: “Promote”
    Steel dashed path downward: “Reject — keep prior champion”
  Tiny examples under Reject (steel, 8pt):
    “Hard-negative mining: FPR down, identity-burst AP 0.96 → 0.36”
    “FPR-only retrain: cost sketch ×300, identity-burst AP −8%”

Column C — Test worlds (read-only)
  Top: Photograph / holdout (seed 48) — frozen, never used to choose the model
       Report: family AP, Pareto recall@FPR, actions, cost
  Bottom: Confirmatory world (seed 49) — touched once after a loop ends
  Red-line (navy, not red) across the column: “No threshold search · no retraining”

Bottom full-width bar:
“Genuine FPR = false positives / genuine transactions, not accuracy.
Average precision and recall-at-FPR are reported separately.”

Do not show a circular MLOps infinity loop. This is a ladder with a reject chute.
```

---

## 4. Pareto chart (in depth)

```
[PASTE STYLE BLOCK]

Title: “Recall under a genuine false-positive cap”
Subtitle: “Internal holdout world · not production · not external transfer”

This is a 2D line chart, not a dashboard. One chart, large, top 70% of the frame.

X-axis: Genuine false-positive rate (%), linear, ticks at 0.1, 0.5, 1, 2, 5. Label: “Genuine FPR (%)”
Y-axis: Fraud recall (%), from 80 to 100. Ticks at 80, 85, 90, 95, 100. Label: “Fraud recall (%)”
No 3D, no area fill under the champion except a 4% opacity #0070AD wash.

Two series only:
  Steel solid line + small open circles: “Stage 1 baseline”
  Navy + accent line, slightly thicker (1.5px), filled circles: “Champion (family-targeted refit)”

Exact points (place labels as small navy callouts, offset so they do not collide):

Stage 1:
  5.0% FPR → 96.3% recall
  2.0% → 94.8%
  1.0% → 87.9%
  0.5% → 84.7%
  0.1% → 83.1%

Champion:
  5.0% → 99.9%
  2.0% → 99.9%
  1.0% → 99.8%
  0.5% → 99.7%
  0.1% → 98.7%

Highlight the 0.1% operating point with a vertical hairline at x=0.1 and a square callout:
  “Selected operating region
   98.7% recall
   genuine FPR ≤ 0.1%”

Second smaller callout at x=1.0:
  “99.8% recall @ 1% genuine FPR”

Legend top-right, two lines only, no box border.

Bottom 30%: three equal annotation cards, hairline, no icons:

Card 1  Why this chart
  “A detector that flags almost every genuine payment can show high recall.
   The curve asks: how much fraud remains caught when genuine FPR is capped.”

Card 2  How the threshold is chosen
  “The 0.1% cap threshold is selected on training inner_val.
   The holdout world is scored once. Thresholds are not searched on the test labels.”

Card 3  Protocol freeze (separate from the curve)
  “inner_val threshold 0.915 → holdout eval fold
   98.5% recall at 0.032% genuine FPR
   (stricter than reading 98.7% off this envelope)”

Footnote 8pt: “Internal simulator holdout. Do not label as accuracy or real-world performance.”

Do not add a third series. Do not add SAML-D on this chart.
```

---

## How to generate

- Aspect: **16:9** for all four.
- Generate as a **set** with the same style block so slides match.
- If the model misspells labels, regenerate with “fix spelling, keep layout.”
- If it invents extra boxes, add: “Do not add boxes that are not listed.”
