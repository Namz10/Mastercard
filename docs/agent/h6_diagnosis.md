# H6 failure diagnosis

**Date:** 2026-08-29 · **Status:** complete (read-only forensics)

## What happened

Generic top-500 hard-negative mining on `v1-gdev-47` lowered confirmatory `genuine_fp` (8.12% → 6.74% on gtest-49) but collapsed `identity_burst` AP (0.958 → 0.364) and exploded `cost_sketch` (~40×). **Do not promote** `v1-train-46__hn-train`.

## Root cause (feature forensics)

| Cohort | `is_new_payee` mean | `fan_in_1h` mean | APP stamp active |
|--------|---------------------|------------------|------------------|
| Mined HN (n=500) | **0.906** | 1.25 | 0.4% |
| All normals | 0.049 | 1.54 | 0.4% |
| `identity_burst` fraud | 0.003 | **57.5** | 0% |

Mined rows are **new-payee-shaped legitimate traffic** scoring 0.91–1.0 — not stamp-heavy APP profiles. `identity_burst` fraud is **fan-in / burst** shaped. Generic mining teaches the model to suppress the wrong shortcut (new payee) and shifts the global threshold/ranking, hurting identity recall despite FPR gains.

## Recommended next mining design

1. **Filter mining pool:** drop `is_new_payee=1` normals (or cap `top_k` ≤ 50).
2. **Portable-only negatives:** mine normals that false-positive on fan_in/burst/velocity — not APP/new-payee proxies.
3. **Family gate:** only add HN when `identity_burst` is the weakest family on gdev; otherwise skip.

Artifact: [`data/validation/v1/h6_diagnosis.json`](../../data/validation/v1/h6_diagnosis.json)
