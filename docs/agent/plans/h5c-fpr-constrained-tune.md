# H5c — FPR-constrained hyperparameter tuning (champion v2)

## Hypothesis

Loop M signal is strong but default `detect_thr` (~8% `genuine_fp`) undersells the Pareto frontier. **Optuna on inner-fit/inner-val only** with expanded HGB search + **max recall @ genuine FPR ≤ 1%** objective yields a champion that improves operational recall at fixed FPR without family collapse.

## One change

1. `fit_champion`: `detect_thr` from `max_recall_at_genuine_fpr` (normal-mask denominator).
2. `tune_champion`: same threshold rule; expanded search (`max_iter`, `learning_rate`, `max_leaf_nodes` **or** `max_depth`, `min_samples_leaf`, `l2_regularization`, `max_bins`).
3. Objective: maximize inner-A recall @ `operating_point_fpr` (1%) subject to inner-B `genuine_fp` ≤ ceiling; log 0.5%/0.1% in trial attrs.
4. Train `v1-train-46` → `v1-train-46__fpr-v2` (**champion v2**).
5. **Promote/reject on `v1-gdev-47` only** (scratch paper, repeatable).
6. **One-shot** confirmatory score on `v1-gtest-49` if gdev Pareto improves vs `v1-train-46__loopm-train` (v1 Loop M).

## Split discipline (anti-rig)

| Split | Role |
|-------|------|
| inner_fit / inner_val | Optuna + `detect_thr` only |
| `v1-gdev-47` | Per-round promote/reject (H5c) |
| `v1-gtest-48` | Frozen photograph — **no tune, no promote loop** |
| `v1-gtest-49` | Confirmatory — **touched once** after gdev accept |
| SAML-D | Stream-score only; never threshold-tune |

Never train/tune on gtest-48/49 labels. Never bump `n_customers`.

## sklearn params (pinned `scikit-learn>=1.4`)

`max_leaf_nodes`, `min_samples_leaf`, `l2_regularization`, `max_bins` — verified HGB params. No `max_features` (not in HGB). `max_depth` and `max_leaf_nodes` mutually exclusive per trial.

## Success (Pareto, not AP)

- v2 recall @ 1% FPR on gdev-47 ≥ v1 Loop M − 2pp **and** `identity_burst` recall @ 1% not −5pp
- Default-op `genuine_fp` on gdev not worse than v1 + 1pp ε
- gtest-49 confirmatory: same Pareto dominance or within ε; no family gate fail

## Critic (10/10 PASS)

1. **Defect:** default op ~8% FPR despite 1% inner target; AP-tuned Stage 2 irrelevant.
2. **Evidence:** `pareto_genuine_fpr.json` LoopM 99.6% @ 1% vs 8.07% default op.
3. **Leakage:** Optuna inner only; gdev promote; gtest-49 once.
4. **Easier sim:** no generator change.
5. **Overfit 48:** no gtest-48 in tune or promote loop.
6. **AP gaming:** objective is recall@FPR, not AP.
7. **SAML-D:** no external labels in objective.
8. **Improve:** operational Pareto + recorded champion v2.
9. **Regress:** reject if identity/mule/cost gates fail on gdev.
10. **Falsify:** v2 Pareto ≤ LoopM on gdev → REJECT, keep v1 champion.

## Out of scope

- Recursive Loop M (H7 — separate; max **3** rounds, gdev-only promote)
- Hard-negative mining (H6b)
- Simulator / new estimators
