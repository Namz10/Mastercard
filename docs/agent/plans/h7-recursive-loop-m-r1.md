# H7 round 1 — Recursive Loop M diagnostic (G-dev only)

**Status:** CRITIC PASS — round 1 read-only diagnostic  
**Hypothesis:** H7 — targeted weakness → correction loop beats one-shot Loop M when mistakes are family-shaped (H6-D lesson)  
**Champion:** `v1-train-46__loopm-train` · **G-dev:** `v1-gdev-47`

## Observation

Loop M fixed `identity_burst` once (Stage 1 pick AP 0.32 → champion ~0.99 on gtest). H6 generic top-500 HN **REJECT**: FPR win but identity AP collapse — mined rows 91% `is_new_payee`, wrong shape vs fan_in-shaped identity fraud. H5c FPR-only tune also **REJECT**. Before any retrain, round 1 must quantify **where** the provisional champion still fails on G-dev.

## One change (round 1 only)

Add `packages/eval/recursive_loop_m.py`:

1. **`diagnose_weakness(run_id='v1-gdev-47', model_run_id='v1-train-46__loopm-train')`**
   - Score full G-dev population with frozen champion (`all_rows=True`).
   - Pick **weakest fraud family** = lowest `ap_by_family` among families with `n_pos >= 30`.
   - Bucket mistakes at `detect_thr`:
     - **FP normals** — all vs H6-D pool (`is_new_payee=1` excluded from HN count).
     - **FN by family** — fraud rows below threshold.
     - **Borderline** — scores within ±20% of `detect_thr` (all + per family).
   - Persist `data/validation/v1/h7_round1_diagnosis.json`.
   - **No** `fit_champion`, **no** blind top-k HN mining, **no** gtest scoring.

Round 2+ (not this iteration): targeted Loop M extras + filtered HN → retrain → promote/reject on gdev only.

## Protocol (locked)

| Split | Role |
|-------|------|
| `v1-gdev-47` | Round 1 diagnostic + per-round promote/reject (rounds 2–3) |
| `v1-gtest-48` | Frozen photograph — **never** promote/tune |
| `v1-gtest-49` | Confirmatory — **once** after loop ends |
| MAX_ROUNDS | **3** |

`OMP_NUM_THREADS=1` for eval runs. No seed-43 museum.

## Success (round 1)

- Artifact names weakest family with FN/FP/borderline counts under H6-D filters.
- Recommended intervention is family-targeted (Loop M positives + filtered HN), not generic top-k.
- Enables round 2 plan without touching gtest.

## RED tests

1. `test_diagnose_weakness_source_gdev_only` — no gtest promote, no `fit_champion`, no top-k mine.
2. `test_diagnose_weakness_h6_d_filter` — `HN_EXCLUDE_NEW_PAYEE` and separate FP buckets in source.
3. `test_pick_weakest_respects_n_pos_floor` — unit test on synthetic AP/n_pos.

## Critic (10/10 PASS)

1. **Defect:** H6/H5c showed blind FPR/HN moves hurt identity; need mistake forensics before retrain.
2. **Evidence:** `h6_diagnosis.json` — 91% new-payee mined vs fan_in identity shape.
3. **Leakage:** read-only gdev score; no label use on gtest-48/49 for this round.
4. **Easier sim:** no generator change.
5. **Overfit 48:** gtest-48 absent from diagnostic and promote gate.
6. **AP gaming:** diagnostic only; round 2+ uses Pareto + family gates on gdev.
7. **SAML-D:** not in round 1 scope.
8. **Improve:** structured buckets enable targeted Loop M instead of H6 repeat.
9. **Regress:** round 1 cannot regress champion (no train).
10. **Falsify:** if weakest family is not identity_burst and FN pool is tiny → skip Loop M round 2, try alternate family intervention.

## Out of scope (round 1)

- `fit_champion` / augment train
- gtest-48/49 scoring
- Optuna / threshold retune
- Generic hard-negative mining
