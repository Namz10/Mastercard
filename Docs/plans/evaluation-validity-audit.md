# Evaluation-Validity Audit (Pre-Final Validation)

**Date:** 2026-08-29  
**Scope:** Identify → Generate → Defend — will reported metrics be honest, reproducible, and defensible?  
**Source of truth read (in order):** `defend-execution-ssot.md` §13, `architecture-defense-doc.md`, `VALIDATION.md`, `models/features.json`, `packages/config/scale.py`

---

## Summary

The core evaluation spine is **largely implemented correctly**: time+entity splits, inner-val thresholding, G-test seed discipline in fit/tune/Loop T, stamp gating for APP flags, vectorized rule-bit parity tests, and `gtest_opened_at` logging. **Three issues can invalidate or undermine headline numbers if you run validation today without fixing them:** (1) `recipe_hash` ignores Optuna `best_params.json`, so G-test can be rescored after hyperparameter drift without moving to seed 45; (2) binary fraud PR-AUC / precision / recall / confusion matrix are absent from persisted metrics; (3) several doc-locked constants (`isolation_forest.enabled_default`, PSI fail thresholds) disagree with code.

---

## Findings Table

| Check # | File(s) inspected | Finding | Severity | Fix needed |
|--------:|-------------------|---------|----------|------------|
| **1** | `packages/sim/runner.py`, `Makefile`, `packages/config/scale.py`, `tests/test_validation_protocol.py` | Seeds 42/43/44 are generated via independent `run_population()` calls with distinct `world_seed`; not derived from one another. Parquet bytes differ across seeds (tested). | — | None (pass) |
| **1** | `packages/sim/ledger.py`, `tests/test_validation_protocol.py` | `event_id` format is `evt-{seq:010d}` starting at 1 in every world — **IDs overlap across seeds** (same string, different parquets). No cross-world `event_id` disjoint assertion exists (only Loop M `evt-lm-*` ∩ G-test). | RISK | Do not claim global disjoint `event_id` space; or namespace IDs with `world_seed` prefix. |
| **1** | `packages/eval/fit.py`, `packages/eval/loop_m.py`, `Makefile`, `packages/eval/loop_t.py`, `tests/test_eval_phase3.py`, `tests/test_eval_phase6.py` | Seed 43 is read only for `score_run(all_rows=True)` and Loop M before/after in production paths. `fit_champion`, `tune_champion` (guard), Loop T, orchestrator all refuse or never open seed-43 paths. | — | None (pass) |
| **1** | `packages/eval/fit.py` (`_record_gtest_opened`, `gtest_protocol.json`) | `gtest_opened_at` **is implemented** and tested; written on first `score_run(all_rows=True)` when sidecar `world_seed==43`. | — | None (pass) |
| **1** | `packages/eval/fit.py` (`load_champion`, `_record_gtest_opened`) | **No enforcement** that seed 43 is one-shot per *model recipe*: `recipe_hash` is SHA-256 of `models/features.json` only — **not** `best_params.json` or `champion.joblib` hyperparameters. After Optuna/tune, same `recipe_hash` allows rescoring 43; `gtest_opened_at` is reused, not blocked. Violates SSOT §2 “do not change features/params and rescore 43”. | **BLOCKER** | Extend frozen hash to include `best_params` + `op_threshold`; refuse `score_run(all_rows=True)` on 43 if model artifact changed after first `gtest_opened_at`, or mandate seed 45. |
| **1** | `packages/eval/loop_m.py` | Loop M scores the same `gtest_id` twice (before/after) — **allowed** by design for comparison; not a protocol violation. | — | None (pass) |
| **1** | `packages/eval/loop_m.py` | `family_chosen_from_slice` rejects `gtest`/`43`; only `inner_val \| diagnostic \| gdev44`. No `gtest` reads in family-pick logic. | — | None (pass) |
| **2** | `packages/eval/split.py`, tests | `assign_folds` uses calendar 2/3 + entity holdout; no `train_test_split(shuffle=True)` in active fit path (grep + source inspection). | — | None (pass) |
| **2** | `packages/eval/split.py` (`inner_folds_from_train`) | Inner-val is last 20% of **outer train** calendar (`t1 - (t1-t0)*fraction`); not random. Tested in `test_eval_phase3.py`. | — | None (pass) |
| **2** | `packages/eval/split.py`, `tests/test_eval_split.py` | Entity holdout marks held mule/customer rows as `eval`; `build_matrix(fold="train")` excludes them. **No explicit set-intersection assertion** that eval entity IDs are absent from train fold (logic implies it; not CI-guarded). | RISK | Add test: `set(train_split[payer,payee]) ∩ set(eval_split[payer,payee]) == ∅` for held entities. |
| **2** | `packages/sim/features.py` | Causal `G(t−)`: prune → snapshot → append; single forward pass; no PageRank/full-graph features. | — | None (pass) |
| **2** | `packages/sim/export.py`, `packages/eval/split.py`, `tests/test_sim_export.py`, `tests/test_phase7_nonfunctional.py` | `TRAIN_DENYLIST` enforced via `assert_train_schema`, `assert_no_x_leak`, CI tests; denylist columns absent from train parquet. | — | None (pass) |
| **2** | `packages/eval/split.py`, `packages/sim/ledger.py` | `label_family` ∉ `TECHNIQUE_IDS` asserted in `build_matrix` and `make_event`. | — | None (pass) |
| **3** | `packages/sim/export.py`, `packages/sim/features.py`, `tests/test_sim_export.py`, `tests/test_sim_inject.py` | APP flags forced False/0 on non-`app_fraud` rows in `train_rows()` and `replay_features()`. CI asserts. | — | None (pass) |
| **3** | `packages/sim/export.py`, `tests/test_sim_inject.py` (`test_genuine_invoice_flags_false_after_replay`) | Invoice flags default False on genuine replay; invoice inject rows True. Parquet-level assertion on **all non-invoice rows** not in export tests (only event-level fixture). | RISK | Add parquet test: `~(label_family=='invoice_fraud')` → all three invoice flags False. |
| **3** | `packages/eval/iso_check.py`, `models/features.json`, `tests/test_eval_phase6.py` | IF input excludes APP, invoice, `rule__*` columns. Stamp-free list tested. | — | None (pass) |
| **3** | `packages/eval/iso_check.py`, `packages/eval/fit.py` | IF trains on `inner_fit` rows with `label_family==normal` — **post-mix** ledger normals, not pre-inject quiet-world only (SSOT Ticket 8 wording). | RISK | Document honestly; or add quiet-world normal subsample for IF train. |
| **3** | `packages/eval/iso_check.py` vs SSOT §1 | `contamination=0.05` hardcoded; SSOT locks `0.01`. Changes genuine-notify gate behavior. | RISK | Set `contamination=0.01` from `features.json`. |
| **3** | `models/features.json` vs SSOT §1 / §13 | `isolation_forest.enabled_default: true` in repo; SSOT locks `false`. IF may activate on validation laptop if notify rate ≤5%. | RISK | Set `enabled_default: false` unless T8 gate explicitly passed on Plan 08 scale. |
| **3** | `packages/eval/fit.py` (`_app_ablation`) | Two **separate** binary HGB fits (with flags vs zeroed flags) — not inference-time zeroing on one model. “Without” zeros columns rather than dropping them (minor semantic difference). | — | Acceptable; note in write-up. |
| **4** | `packages/eval/fit.py` (`score_run`, `fit_champion`, `_metrics_pass`) | `ap_by_family` and `n_pos` co-located in same metrics dict; `not_comparable` present. | — | None (pass) |
| **4** | `packages/eval/fit.py` | **No explicit fields** for binary fraud PR-AUC, precision, recall, or confusion matrix at `op_threshold` in `metrics.json` / `score_run` output. Only `f1_at_op`, `tpr_at_fpr`, `genuine_fp`. VALIDATION.md §3 lists binary PR-AUC as primary. | RISK | Add `binary_ap`, `precision_at_op`, `recall_at_op`, `confusion_matrix` on G-test score JSON. |
| **4** | `packages/eval/fit.py` (`genuine_fp` computation) | `genuine_fp` = mean(`score >= thr` on `label_family=="normal"`) — correct subset, not `1-precision`. | — | None (pass) |
| **4** | `packages/eval/fit.py` §13.4, `tests/test_eval_fit.py` | G-test `app_ablation` **copied** from champion `metrics.json` (`app_ablation_source: champion_fit`) — keys present on G-test JSON but values are from **seed-42 diagnostic eval**, not G-test rows. By SSOT, but misleading if slides say “G-test ablation”. | RISK | Label clearly in JSON/slides; or run ablation on G-test features (still no refit on 43). |
| **4** | `packages/eval/fit.py` (`score_run`) | `action_histogram` in **score response body**, not inside `metrics` dict; **not persisted** to disk by `fit_champion` or `score_run`. Makefile `defend-gtest` only prints AP — histogram discarded. | RISK | Persist `action_histogram` + `cost_sketch` to `models/{run_id}/gtest_score.json` or metrics. |
| **4** | `packages/eval/split.py`, `packages/eval/fit.py` | `protocol: time_cut_2_3_plus_entity_holdout` on diagnostic; `g_test_full_population` on G-test `all_rows` — matches code. | — | None (pass) |
| **5** | `packages/policy/rules.py`, `tests/test_loop_t.py` | `FORBIDDEN_RULE_FIELDS` rejects `technique_id`, `injector_id`, `world_seed`, etc.; `parse_predicate("technique_id == T13")` raises. | — | None (pass) |
| **5** | `packages/policy/rules.py`, `packages/eval/fit.py`, `tests/test_eval_vectorized_rules.py` | Champion `rule__*` bits from `vectorized_rule_bits`; brake hist uses same bits via `_rule_hit_masks`. Parity tests vs row-loop `evaluate_rules`. | — | None (pass) |
| **5** | `packages/eval/brake.py`, `packages/eval/fit.py` (`_vectorized_brake_actions`) | Priority matches doc: mule → calm → APP → invoice → ATO → identity_burst → score notify → allow; APP+decline→hold override; IF allow→notify only. Tested in `test_eval_vectorized_rules.py`. | — | None (pass) |
| **5** | `packages/eval/brake.py` | APP never hard-declined: clamp at lines 100–102 (and vectorized equivalent). | — | None (pass) |
| **6** | `packages/eval/loop_m.py` | Extra rows use `train_seed + 10007`; `extra_ids ∩ gtest_event_ids` asserted. | — | None (pass) |
| **6** | `packages/eval/loop_m.py` | `catalog_solved: False` hardcoded. | — | None (pass) |
| **6** | `packages/eval/loop_m.py`, `packages/eval/fit.py` | Augmented refit uses same `world_seed`, recipe, `force_train_event_ids` only delta; same `fit_champion` path. | — | None (pass) |
| **6** | `packages/eval/loop_m.py` (`_write_augmented`) | 15% cap enforced by truncation (`cap = max(1, int(len(train_df)*cap_frac))`), not a hard `assert n_extra <= cap` after filter. Behavior correct; weak guard if logic regresses. | COSMETIC | Add `assert len(extra_tr) <= cap` after truncation. |
| **7** | `packages/sim/fidelity.py`, `packages/sim/runner.py`, `Makefile` | PSI gates **run** and set `fidelity.pass`; Makefile asserts pass on `generate-scale`. Thresholds are **0.25 / 0.35**, not VALIDATION.md’s 0.2 fail line. | RISK | Align thresholds with VALIDATION.md or update VALIDATION.md to match frozen fixture constants. |
| **7** | `packages/sim/fidelity.py`, `tests/test_sim_inject.py`, `tests/test_sim_fidelity.py` | Anti-stub: `fan_in_1h` recomputed independently; variance test on mule rows; not copied from YAML knob. | — | None (pass) |
| **7** | `packages/sim/features.py` | Feature computation is O(n) single pass (`FeatureComputer.updates`); no nested full-ledger scan in snapshot path. | — | None (pass) |
| **8** | `packages/eval/fit.py` (`_recipe_hash`) | `recipe_hash` = SHA-256 of `models/features.json` bytes; changes when JSON changes; tested. | — | None (pass) |
| **8** | `packages/eval/fit.py` | Fit writes `models/{run_id}/features.json` (run copy), **does not mutate** repo `models/features.json`. `AEGIS_PERM_REPEATS` env override avoids touching recipe. | — | None (pass) |
| **8** | `packages/eval/fit.py` (`tune_champion`) | Optuna objective uses inner-val only; refuses `sidecar world_seed==43`; no gtest path in objective. | — | None (pass) |
| **8** | `packages/eval/fit.py` | **Gap:** tuned hyperparameters not in `recipe_hash` (see Check 1 BLOCKER). | **BLOCKER** | Same fix as Check 1. |
| **9** | Repo-wide grep | No SAML-D / external holdout adapter implemented. | — | N/A — not built; do not quote external AP. |

---

## Doc ↔ Code Disagreements (defensibility risk even if code is “fine”)

| Topic | Doc says | Code does |
|-------|----------|-----------|
| G-test one-shot | SSOT §2: after `gtest_opened_at`, do not change params and rescore 43; use seed 45 if peeked | Logs timestamp only; `recipe_hash` excludes Optuna params; rescoring allowed |
| IF default | SSOT §1: `enabled_default: false` | `models/features.json`: `enabled_default: true` |
| IF contamination | SSOT §1: `0.01` | `iso_check.py`: hardcoded `0.05` |
| PSI fail gate | VALIDATION.md §2.2.1: PSI ≥ 0.2 → fail | `fidelity.py`: `PSI_AMOUNT_MAX=0.25`, `PSI_HOUR_MAX=0.35` |
| APP ablation on G-test | Architecture §6 lists `app_ablation` on headline blob | Values copied from seed-42 fit diagnostic eval (`app_ablation_source: champion_fit`) |
| Binary fraud metrics | VALIDATION.md §3 primary metrics | Not in persisted `metrics.json` |
| Cross-world IDs | Audit prompt / informal “disjoint event_id space” | Same `evt-0000000001`… namespace in every seed (separate parquets) |
| `action_histogram` | Architecture §6 + SSOT cost sketch | Present in `score_run` **response** only; not saved in Makefile flow |
| Generate fidelity | VALIDATION implies hard gate | `run_population` returns `pass: false` but **does not raise**; API returns 200 with failed fidelity |

---

## Prioritized Punch-List

### Fix TODAY before any validation run (BLOCKERs only)

1. **Freeze model identity for G-test, not just `features.json`.** Include `best_params.json` digest (or champion hyperparameter tuple + `op_threshold`) in `recipe_hash` / `gtest_protocol.json`. On `score_run(all_rows=True)` with `world_seed==43`, if champion artifact changed after first `gtest_opened_at`, **refuse** or require explicit `make-gconfirm` seed 45 run_id.
2. **Workflow:** If you already ran `defend-gtest` during development, treat that headline number as **exploratory** until the fix lands and you photograph on a fresh 43 (or 45).

### Can wait (RISK — weaken claims but don’t auto-invalidate if labeled honestly)

1. Add binary fraud `binary_ap`, `precision_at_op`, `recall_at_op`, `confusion_matrix` to G-test score artifact.
2. Persist `action_histogram` and full G-test metrics JSON from Makefile (`defend-gtest` → write `data/runs/make-gtest/score.json` or similar).
3. Set `isolation_forest.enabled_default: false` until Plan 08 IF abort gate is run and logged.
4. Align PSI thresholds with VALIDATION.md or update VALIDATION.md to match `fidelity.py` constants.
5. Add entity holdout disjoint-ID CI test; add parquet-level invoice-flag isolation test.
6. Clarify in slides that G-test `app_ablation` is champion-fit diagnostic, not recomputed on seed-43 rows.
7. Fix IF `contamination` to 0.01 per SSOT.
8. Hard-fail `run_population` (or API 422) when `fidelity.pass` is false outside test fixtures.

### COSMETIC

1. Loop M explicit `assert len(extra_tr) <= cap` after truncation.
2. Harmonize `tune_champion` docstring (claims frozen threshold; `fit_champion` recomputes from inner-val — acceptable but confusing).

---

## What Looks Solid (no action required)

- Nested split protocol (outer time+entity, inner calendar 20%).
- G-test excluded from fit, tune, Loop T mine, permutation importance paths.
- APP session stamp isolation in export/replay.
- Rule forbidden-field enforcement and vectorized/loop rule-bit parity tests.
- Brake priority order and APP-no-decline clamp.
- Loop M: `catalog_solved: false`, extra seed offset, G-test disjointness for `evt-lm-*`.
- `gtest_opened_at` logging (implementation exists — not policy-only).
- Causal feature computer; anti-stub `fan_in_1h` tests.
- `recipe_hash` mismatch blocks scoring when `features.json` changes after freeze.

---

## Recommended Validation Order After BLOCKER Fix

```
make generate-scale          # seed 42
make defend-fit              # freeze champion + manifest
make defend-gdev             # seed 44 — Loop T / ECE only
# Loop T mine/approve if needed
make defend-gtest            # seed 43 — ONE headline photograph; persist full JSON
```

Do **not** run `defend-tune` or change `best_params.json` between `defend-fit` and `defend-gtest` until the recipe-hash BLOCKER is fixed.
