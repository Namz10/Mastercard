# Plan: H4-E2 preflight + next iteration (H6)

**Status:** Path A IMPLEMENTED (critic PASS 2026-08-29) — H6 next with full gate  
**Date:** 2026-08-29  
**Violation:** Prior session ran `fit_champion('v1-train-50')` without critic/judge; wasted ~200s PI then failed `inner_val.ato=0<15`.

## Root cause (FACT)

| Run | inner_fit ATO | inner_val ATO | eval ATO |
|-----|---------------|---------------|----------|
| v1-train-46 (seed 46) | 206 | **39** | 151 |
| v1-train-50 (seed 50) | 250 | **0** | 153 |

`inner_folds_from_train` uses last 20% of train calendar for `inner_val`. On seed 50, **all ATO events fall in the first 80%** of train span → E2 floor fails after expensive fit stages.

Terminal spam in `terminals/15.txt` is a **bad wait-loop** re-tailing one traceback, not 25 separate fits.

## Proposed changes (pick one path — critic must choose)

### Path A — Pre-flight gate only (minimal, recommended first)

1. Add `preflight_fold_floors(run_id, world_seed)` called at **start** of `fit_champion` (before HGB/PI).
2. Raises same `ValueError` as `assert_fold_n_pos` but **before** heavy work.
3. RED test: toy world with known inner_val desert → preflight fails in <1s.
4. **H4:** document blocked; do not retry fit on seed 50 without Path B/C.

**Risk:** Low. No fold logic change.  
**Does not fix:** seed 50 still unfittable.

### Path B — Family-stratified inner_val backfill (E2 fix)

1. After calendar cut, if any fraud family `< fold_floor_min` in `inner_val`, move oldest events of that family from `inner_fit` → `inner_val` until floor met (train fold only; no eval touch).
2. RED: seed-50-like synthetic calendar → inner_val.ato ≥ 15.
3. Re-run H4 fit on v1-train-50 only after pytest + critic PASS.

**Risk:** Medium — changes threshold calibration distribution; must prove no label leak and document in VALIDATION.md.

### Path C — Abandon H4 on seed 50; proceed H6

1. Leave H4 `rejected` in ledger.
2. **H6 hard-negative mining** on frozen `v1-gdev-47` / eval `v1-gtest-48` (no new worlds).
3. No split.py change.

**Risk:** Low. H4 mechanism untested until Path B or new seed.

## Critic checklist (10 questions)

1. Defect: E2 fold floor fails late / H4 executed without gate.
2. Evidence: fold counts above; `/tmp/h4_fit_score.log` traceback.
3. Label leak: Path B must not move eval rows.
4. Realism: Path B may alter inner_val calendar semantics.
5. Overfit 48: H6 uses inner_fit extras only; 48 frozen.
6. AP vs FP: H6 targets genuine_fp directly.
7. SAML-D: no train on external.
8. Improve: preflight saves time; H6 targets KB §3.
9. Regress: Path B could shift detect_thr.
10. Falsify: preflight fails fast on seed 50; H6 genuine_fp down on 49.

## Execution order (after CRITIC PASS)

1. RED tests (subagent or parent)
2. Implement **one** path only
3. `pytest` gate
4. Eval per SOP (H6: mine on 47, score 48/49)
5. JUDGE subagent → ledger → commit

## Explicitly forbidden

- Running `fit_champion` on new seeds without preflight
- Lowering `fold_floor_min` in production recipe
- Retuning on gtest-48 labels for H6
