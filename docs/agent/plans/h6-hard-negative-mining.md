# Plan: H6 — Hard-negative mining (KB §3)

**Status:** CRITIC PASS — implementing; v1 eval running  
**Hypothesis:** H6 — high-scoring normals from G-dev lower genuine FPR on frozen G-test vs more fraud positives  
**Branch:** `agent/H6-hard-negatives`

## Observation

Loop M champion: **8.07%** `genuine_fp` on gtest-48; **8.12%** on gtest-49. KB prioritizes teaching the model that suspicious-looking normals are still normal.

## Proposed change (one module)

Add `packages/eval/hard_negatives.py`:

1. **`mine_hard_negatives(gdev_run_id, model_run_id, *, top_k, min_score)`**  
   - Score all rows on **v1-gdev-47** with **frozen** `v1-train-46__loopm-train` (no retrain on gdev).  
   - Keep `label_family == normal` only.  
   - Rank by `_fraud_score`; take top `k` (default 500, cap `extra_row_cap_frac=0.15` of train-46 length).  
   - Return event_ids + scores manifest (no gtest-48/49 rows).

2. **`augment_train_with_hard_negatives(train_run_id, gdev_run_id, mined_ids)`**  
   - Copy feature rows from gdev train parquet for mined ids.  
   - Append to train-46 copy `v1-train-46__hn-train` with new ids `evt-hn-*`, timestamps shifted into train-46 calendar (same pattern as Loop M `_write_augmented`).  
   - Labels stay **`normal`**.  
   - `force_train_event_ids` = hn ids → **inner_fit only** (existing split guard).

3. **`run_hard_negative_loop(...)`**  
   - Mine → augment → `fit_champion(aug_id, world_seed=46, force_train_event_ids=hn_ids, dest_run_id=v1-train-46__hn-train)`  
   - Score **gtest-48** (instrumentation) and **gtest-49** (confirmatory) with `all_rows=True`.  
   - Persist `data/validation/v1/h6_hard_negatives.json`.

## Pre-registered gates (G6, locked before numbers)

| Gate | Criterion |
|------|-----------|
| Primary | `genuine_fp` ↓ on gtest-49 vs Loop M baseline 8.12% |
| FPR slack | ≤ +2pp vs baseline on 49 (same as `genuine_fpr_eps`) |
| Recall | `recall_at_op` not down >5% relative on 49 |
| Families | No comparable family AP drop >5% relative on 48 |
| SAML-D | Optional sidecar; must not regress TPR@0.1% FPR if run |

## Anti-rig

- Mine/score selection uses **gdev-47 only** — never gtest-48/49 labels for mining.  
- Base model frozen for mining scores.  
- No threshold retune on gtest.  
- No relabeling fraud as normal.

## RED tests (before implementation)

1. `test_mine_hard_negatives_only_normals` — mined ids all `label_family==normal` on fixture/toy.  
2. `test_hn_extra_ids_disjoint_from_gtest49` — hn ids not in gtest-49 split.  
3. `test_hn_force_train_stays_inner_fit` — augmented ids ∈ inner_fit slice.

## Critic falsification

H6 rejected if: retrain completes but `genuine_fp` on gtest-49 unchanged or worse beyond ε, while recall collapses.

## Execution order

PLAN → **CRITIC** → RED → implement → pytest → fit+score → **JUDGE** → ledger → commit
