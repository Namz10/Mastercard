# Child 3 — n_pos scale gate (after Stage 1 G-test only)

**Parent:** [Master validation protocol](../../.cursor/plans/external_holdout_validation_64f9d54e.plan.md)  
**When:** After Stage 1 G-test photograph on seed 43, **before** Stage 2 Optuna.  
**Short checklist (same rules):** [`15-npos-scale-gate-after-stage1.md`](15-npos-scale-gate-after-stage1.md)  
**Prerequisite:** [`eval-child-preval-blockers.md`](eval-child-preval-blockers.md) so the photograph is freeze-valid.

**Do not** raise `n_customers` / `n_merchants` preemptively in Stage 0. Frozen Plan 08 scale stays **2400 × 120 × 90** until this gate says otherwise — and even then, **customers stay 2400**.

---

## Floor

`n_pos_not_comparable_below = 30` ([`models/features.json`](../../models/features.json), SSOT §1).

Quote family AP only when `not_comparable` is false. Otherwise print `n_pos` and the flag. Do not claim a mule win or loss on `n_pos < 30`.

---

## Which slice is the photograph

**G-test `all_rows` (`score_run(..., all_rows=True)`, protocol `g_test_full_population`).**

The diagnostic eval fold (outer last 1/3 + entity holdout on seed 42, or eval fold on 43 if you ever score `all_rows=False`) **can zero** `ato` / identity. That is **not** the n_pos gate and **not** the family-AP quote for the write-up.

Existing **fullmix seed 42** (operator knowledge, pre-43):

| Family | `all_rows` n_pos (seed 42) | Gate |
|---|---|---|
| mule | ~28 | **below 30** → `not_comparable` |
| ato | healthy | comparable |
| invoice_fraud | healthy | comparable |
| app_fraud | healthy | comparable |

Seed 43 will differ. **Do not assume** mule stays 28. Read the Stage 1 G-test JSON.

---

## Procedure

1. Freeze sidecar scale at 2400×120×90. Do **not** raise `n_customers` as the default fix for thin mule support. Constants: [`packages/config/scale.py`](../../packages/config/scale.py).
2. Keep the existing seed-42 fullmix world for Stage 1. Mule `n_pos` ≈ 28 on 42 `all_rows` is expected. Do **not** regenerate a larger population **before** Stage 1.
3. Photograph Stage 1 G-test (`make-gtest`, seed 43) at that frozen sidecar scale.
4. Read G-test `metrics.n_pos` / `not_comparable` **per family on all_rows**.
5. If mule (or any family you will quote as a headline AP) still has `n_pos < 30`:
   - Keep `n_customers=2400`, `n_merchants=120`.
   - Cheapest levers: raise mule mix share [`DEFAULT_SHARES["mule"]`](../../packages/sim/inject/mix.py) (currently **0.40**) and/or `sim_days` (currently **90**).
   - Do **not** add customers to “buy” more mule rows. That changes graph density and is a different experiment.
6. After a mix or `sim_days` bump:
   - Regenerate train 42 and G-test 43 (and G-dev 44) at the **same** n_customers / n_merchants.
   - Refit Stage 1 (new `model_freeze_id`).
   - Re-photograph Stage 1. Prior seed-43 numbers are **exploratory**.
   - Re-lock Loop M family from the **new** G-dev 44.
7. If after one bump mule is still `< 30`: record `not_comparable`, quote `n_pos`, proceed to Stage 2 **without** claiming mule AP. A second bump is a judgment call; still never the customer-count lever for this gate.

---

## What this is not

- Not a license to change Plan 08 as the **default** Makefile scale before seeing seed-43 `n_pos`.
- Not Loop G. Not a new injector.
- Not an excuse to skip Stage 2 / 3b because mule is thin. Other families can still carry the table.

---

## Write-up line (required)

One sentence: G-test mule `n_pos` = N; comparable or not; if bumped, record old `sim_days` / mule share vs new, and that 43 was re-photographed after Child 1 freeze rules.
