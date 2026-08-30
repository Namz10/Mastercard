# Defend v1 system map (Wave 0)

## Seeds and worlds

| Role | run_id | world_seed |
|------|--------|------------|
| Train | `v1-train-46` | 46 |
| G-dev | `v1-gdev-47` | 47 |
| G-test photograph | `v1-gtest-48` | 48 |
| Loop M duplicate | `v1-train-46__gtest` | 48 (alias) |

Scale: 2400 × 120 × 90. Museum seed 43 is frozen in `results.md`.

## Models

| model_run_id | Stage | Notes |
|--------------|-------|-------|
| `v1-train-46` | Stage 1 | Base HGB champion |
| `v1-train-46-stage2` | Optuna | Lower FPR, weaker ATO on gtest |
| `v1-train-46__loopm-train` | Loop M | Provisional champion (cost + recall) |

## Lead metrics

- Lab: family AP, `genuine_fp` = FP/n_normal, TPR@FPR at inner-val `detect_thr`, cost sketch
- External: SAML-D TPR@FPR only (never compare binary AP to lab 0.879)
- Wave 6 tie-break: `without_stamps` frozen-champion binary AP on gtest-48

## Wave 0 closures

| ID | Fix |
|----|-----|
| 0.1 | `_app_ablation` scores frozen champion |
| 0.2 | `loop_m_result.json` gtest alias documented |
| 0.3 | `VALIDATION.md` genuine_fp vs over_eval |
| 0.4 | `hub_gate_report.json` report-only |
| 0.5 | `photography_day.json` champion fields |
| 0.6 | SAML-D Loop M sidecar |
