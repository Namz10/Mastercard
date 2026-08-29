# n_pos scale gate (after Stage 1 G-test)

Full SOP: [`eval-child-npos-scale.md`](eval-child-npos-scale.md). Parent: [Master validation protocol](../../.cursor/plans/external_holdout_validation_64f9d54e.plan.md).

Floor: `n_pos_not_comparable_below = 30`. Seed-42 `make-scale-fullmix` `all_rows` mule `n_pos` ≈ 28 today (already `not_comparable`).

1. Freeze Plan 08 sidecar scale at 2400×120×90; do not raise `n_customers` as the default fix for thin mule support.
2. Keep the existing seed-42 fullmix world; mule `n_pos` ≈ 28 on `all_rows` is expected — do not regenerate a larger population before Stage 1.
3. Photograph Stage 1 G-test first (`make-gtest`, seed 43, `score_run(all_rows=True)`) at that frozen sidecar scale; do not pre-scale.
4. After Stage 1, read G-test `n_pos` / `not_comparable` per family on **all_rows** (not the diagnostic eval fold).
5. If mule (or any family you will quote) still has `n_pos` < 30, keep `n_customers=2400` and `n_merchants=120`.
6. Cheapest levers: raise mule mix share (`DEFAULT_SHARES["mule"]`, currently 0.40) and/or `sim_days` (currently 90) — not customer count.
7. After a mix or `sim_days` bump: regenerate train 42 and G-test 43 at the same sidecar n_customers/n_merchants, refit, re-photograph Stage 1; prior seed-43 numbers are exploratory.
8. Quote family AP only when `not_comparable` is false; otherwise print `n_pos` and the `not_comparable` flag — do not claim a mule win or loss.
