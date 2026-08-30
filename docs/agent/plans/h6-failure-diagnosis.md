# H6-D — Diagnose generic hard-negative mining failure

## Observation

H6 JUDGE REJECT: gtest-49 `genuine_fp` 8.12%→6.74% but `identity_burst` AP 0.958→0.364 and `cost_sketch` ~40×. Do **not** retry generic top-500 mining.

## Hypothesis

Mined normals are **near-saturated fraud scores** (~0.99+) with **APP/stamp-shaped feature profiles** overlapping `identity_burst`. Retrain pushes the model to suppress those directions, collapsing identity recall.

## Change (one)

- Add `packages/eval/h6_diagnosis.py`: feature means + APP-flag overlap for mined vs normals vs identity fraud on `v1-gdev-47`
- Persist `data/validation/v1/h6_diagnosis.json` + `docs/agent/h6_diagnosis.md`

## Anti-rig

- Read-only forensics on existing H6 artifact and gdev parquet
- No retrain, no new mining

## Success

- Quantified feature/stamp overlap explaining identity collapse
- Actionable constraints for next mining attempt (cap k, exclude stamp-active normals, family-aware)

## Next (not this iteration)

- H6b family-aware/capped mining with critic gate
