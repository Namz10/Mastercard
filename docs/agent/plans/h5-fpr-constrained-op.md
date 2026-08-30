# H5b — FPR-constrained operating envelope (instrumentation)

## Hypothesis

Explicit **max recall @ genuine FPR ≤ {1%, 0.5%, 0.1%}** on frozen Loop M vs Stage 1 quantifies the operational Pareto frontier on **gtest-48 and gtest-49**, including per-family recall at each cap. This does not retrain; it makes the optimization objective auditable before any threshold/training change.

## Change (one)

- Add `packages/eval/fpr_pareto.py`: `max_recall_at_genuine_fpr`, `pareto_envelope`, `write_pareto_report`
- Persist `data/validation/v1/pareto_genuine_fpr.json`
- RED tests in `tests/test_fpr_pareto.py`

## Anti-rig

- No label/world edits; frozen champions only
- Thresholds are **post-hoc** on eval rows — not used to pick ops on gtest-48/49 for champion promotion
- Does not subsample or retune on SAML-D

## Success

- Loop M envelope dominates Stage 1 at 1/0.5/0.1% on gtest-48 **and** gtest-49
- Family recall table shows which families pay the FPR cost at each cap
- Artifact committed for Wave 1 ledger

## Out of scope (next iteration)

- Wire `max_recall_at_genuine_fpr` into `fit_champion` inner_val `detect_thr` (if materially different from `_tpr_at_fpr`)
- Retrain with FPR-constrained Optuna objective
