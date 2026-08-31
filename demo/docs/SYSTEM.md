# System architecture (booth narrative)

Technical SSOT for judges. In-app copy lives in `src/content/system-story.ts`.

## Closed loop

1. **Identify** — Allowlisted OSINT → extract → ground to T01–T24 atlas → HITL approve.
2. **Generate** — Quiet UPI-like world → typed injectors → fidelity (PSI, fraud-rate band) → parquet.
3. **Defend** — Causal features + rule bits → HistGBM champion → recall @ genuine FPR OP → Brake policy.
4. **Loop M** — Miss family from diagnostic slice → extra train mix → grade new gtest → highlight Identify.

## HistGBM nested fit

| Stage | What we do | Why |
|-------|------------|-----|
| Load + rule bits | Train allowlist columns; rules as features | No label leakage |
| Assign folds | Time cut + entity holdout | G2 protocol |
| Inner HGB | HGB on inner_fit | Threshold model |
| Inner-val OP | Isotonic cal; pick OP at target FPR | Never tune on eval |
| Isolation forest | Unsupervised anomaly | Kill-switch if too noisy |
| Outer HGB | Refit on full train | Shipped champion |
| Permutation | Feature importance on inner-val | Explainability |
| Bootstrap CI | Cluster resamples per family | Stability bands |
| Brake histogram | Policy at OP | What bank would do |

## Champion protocol

- Worlds: `v1-train-46` (train), `v1-gtest-48` (reported transfer).
- Model: `v1-train-46__loopm-train` after Loop M.
- Threshold: inner_val at 0.1% FPR cap → **98.52% recall @ 0.032% genuine FPR** on gtest-48.

## Seven gates (G1–G7)

Documented in VALIDATION.md — causal features, temporal split, ablation, delayed labels, baseline, rollback, coverage. Prototype replays recorded artifacts.

See also: `docs/METRICS.md`
