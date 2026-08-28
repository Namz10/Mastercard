# AegisLoop Defend — QA / validation tracker

**Implements:** code from [`defend-execution-ssot.md`](defend-execution-ssot.md) (§13). Agent index: Cursor Defend Peak plan + [`README-defend.md`](README-defend.md).  
**Architecture claims:** [`defense-architecture.md`](defense-architecture.md), [`architecture-defense-doc.md`](architecture-defense-doc.md).  
**Do not implement product code from this file.** Write the **named test first**, confirm it is **RED on current `HEAD`**, then implement the ticket until it is GREEN. A ticket is not done if the only passing tests are the old suite.

---

## 0. QA rules (non-negotiable)

1. **RED first.** For every `ADD` row, `pytest <node>` on current code must fail for the **stated reason** (ImportError, AssertionError, missing key). If it already passes, the test is too weak — rewrite the oracle.
2. **No skip-as-pass.** `pytest.skip`, `xfail` without a ticket, empty `candidates: []` counted as success, or `n_pos` missing treated as `0` are forbidden.
3. **No tautology.** Do not assert `"ap_by_family" in metrics` only. After T2 also assert `set(metrics["n_pos"]) >= LABEL_FAMILIES` and `not_comparable` dtype/bool per family.
4. **Oracles are literals.** Expected numbers, seeds, path substrings, HTTP JSON keys are written below. Do not invent softer checks at runtime.
5. **Fixtures are small and deterministic.** Unit RED tests use hand-built events / tmp `runs_dir`, not Plan 08. HTTP E2E uses `n_customers=20` unless marked `slow`.
6. **Cursor plan vs SSOT.** Tests follow **SSOT §13**, not `defend_peak_implementation_d6545d76.plan.md` where they conflict (table below).

| Cursor plan (stale) | SSOT §13 (test this) |
|---------------------|----------------------|
| Loop T `fold="inner_val"` | G-dev world 44; `gdev_mine` 70% / `gdev_gate` 30% by `event_ts` |
| 7 HTTP routes including edit/fp-propose | Four routes: mine, drafts, approve, reject |
| YAML `_meta.version` | List-root YAML; `versions.json` + `data/rules/backups/v0_rules.v{n}.yaml` |
| Loop M run_id `{train}-lm` | Keep `{run_id}__extra-{family}`, `{run_id}__gtest`, `{run_id}__loopm-train` |
| Burst “or drop column” | Redefine `burst_velocity`; keep `seasoning-burst` |
| Optuna hard prune | Soft penalty `binary_AP - 10*max(0, fp-0.01)` |
| T5 before T7 | Sequence T4 → T6 → T7, then T5 |

---

## 1. Always-green regression (must stay green while adding RED tests)

```bash
pytest tests/test_sim_export.py tests/test_sim_inject.py tests/test_sim_world.py \
  tests/test_sim_fidelity.py tests/test_eval_fit.py tests/test_eval_split.py \
  tests/test_eval_loop_m.py tests/test_eval_rules_brake.py \
  tests/test_defend_handoff.py tests/test_defend_api.py -q --tb=short
```

**Do not delete** existing functions listed in §11.

---

## 2. Traceability: architecture claim → test id

| Architecture / SSOT claim | Test IDs |
|---------------------------|----------|
| Invoice flags lost on `replay_features` | 1A.1–1A.6 |
| `burst_velocity == float(fan_out_1h)` | 1B.1–1B.3 |
| `G(t−)` prune then snapshot then append | 1B.4, `test_causal_payee_history_ignores_future` EXISTS |
| `n_pos` beside every family AP | 2.1–2.5, MET.1 |
| `op_threshold` on outer eval today | 3.2 RED until T3 |
| G-test `score_run(all_rows=True)` | 2.4, GD.3, E.2b |
| APP flags genuine-zero | `test_app_flags_only_on_app_rows` EXISTS + 1A.7 |
| APP ablation | `test_app_ablation_reported` EXISTS; ML.2 direction |
| Brake mule / APP no decline / ATO decline | `test_brake_app_not_decline_ato_may_decline_mule_payee_restricts` EXISTS + 8.2 |
| Invoice rule no `gstin` string | `test_invoice_rule_uses_payload_booleans_not_gstin_string` EXISTS |
| 24 coverage cells; T07 named_gap | `test_coverage_map_has_24_techniques`, `test_named_gap_for_t07` EXISTS + C.2 |
| Loop M extras ∉ G-test; `catalog_solved False` | 6.1 EXISTS |
| Loop T never opens seed 43 | 7.6 |
| Loop T YAML list-root | 7.9 |
| LLM cannot change `when` | 7.7 |
| IF stamp-free; notify-only | 8.1–8.5 |
| Named gaps T06/T07/T20–T23 | C.2 |
| Denylist never in X or HTTP blob | 1A.5, E.2 EXISTS |
| Split not shuffle | `test_reported_split_is_not_shuffle`, `test_time_cut_uses_event_ts_not_shuffle` EXISTS |
| Entity holdout | `test_entity_holdout_mule_payee_goes_to_eval_even_if_early` EXISTS |
| `y` is family not Txx | `test_fit_y_is_family_enum_not_technique` EXISTS |

---

## 3. Ticket tests — RED oracle, fixture, exact asserts

Legend: **RED today** = what `HEAD` does before the ticket.

### Ticket 1A — Invoice booleans

**RED today:** `TRAIN_ALLOWLIST` has no `beneficiary_changed`. `replay_features` overwrites `features_auth` without payload copy. `train_rows()` omits the three keys.

| ID | Function | File | Fixture | Exact asserts | RED today |
|----|----------|------|---------|---------------|-----------|
| 1A.1 | `test_replay_copies_invoice_payload_booleans` | `tests/test_sim_inject.py` | One `doc_beneficiary` event with `payload={beneficiary_changed: True, gstin_checksum_ok: True, lookalike_domain_flag: True}` then `replay_features` | `ev["features_auth"]["beneficiary_changed"] is True`; same for other two | False / KeyError |
| 1A.2 | `test_genuine_invoice_flags_false_after_replay` | same | Quiet/genuine event, empty payload | all three `is False` | KeyError or missing |
| 1A.3 | `test_train_parquet_has_invoice_cols_not_gstin` | `tests/test_sim_export.py` | `run_population(..., n_customers=16, pin=True)` full mix | `{"beneficiary_changed","gstin_checksum_ok","lookalike_domain_flag"} ⊆ train.columns`; `"gstin" not in train.columns`; `"payload" not in train.columns` | columns missing |
| 1A.4 | `test_allowlist_includes_invoice_booleans` | `tests/test_sim_export.py` | import `TRAIN_ALLOWLIST` | three names in tuple | fail |
| 1A.5 | `test_fit_feature_columns_exclude_gstin_payload` | `tests/test_eval_fit.py` | existing `pop` fixture | `"gstin" not in cols` and `"payload" not in cols`; after T1A `"beneficiary_changed" in cols` | last assert RED |
| 1A.6 | `test_invoice_rule_bit_can_fire_on_parquet_row` | `tests/test_eval_rules_brake.py` | flatten a train row with flags True | `invoice-beneficiary-swap` in hits | may already pass via `EXTRA_ROW_FIELDS` on ledger; **also** require flags on **parquet dict** without `payload` key |
| 1A.7 | keep `test_app_flags_only_on_app_rows` | `tests/test_sim_inject.py` | EXISTS | genuine APP flags false | keep GREEN |

**Stop-gate:** 1A.1, 1A.3, 1A.4 RED then GREEN.  
**Weak test to reject:** only checking `payload` on the live event before replay.

---

### Ticket 1B — Unique degree + burst

**RED today:** `burst_velocity = float(fan_out_1h)`; no `fan_in_unique_payers_1h`; deques are timestamps only.

| ID | Function | Fixture | Exact asserts | RED |
|----|----------|---------|---------------|-----|
| 1B.1 | `test_fan_in_unique_same_payer_twice` | Two debit events, same payer→payee, Δt < 1h, after first append | second snapshot: `fan_in_1h == 2`, `fan_in_unique_payers_1h == 1` | KeyError / unique==2 |
| 1B.2 | `test_burst_velocity_unique_outbound_not_event_count` | Same payer, three payments to **same** payee in 1h | last snapshot: `fan_out_1h == 3`, `burst_velocity == 1.0` | `burst_velocity == 3.0` |
| 1B.3 | `test_seasoning_burst_still_uses_burst_velocity_name` | load `v0_rules.yaml` | some rule `id==seasoning-burst` and `"burst_velocity"` in `when` text | keep |
| 1B.4 | keep `test_causal_payee_history_ignores_future` | `tests/test_sim_world.py` | EXISTS | keep |
| 1B.5 | `test_coverage_equiv_unique_fan_in` | `COVERAGE_EQUIV` | `"fan_in_unique_payers_1h" in COVERAGE_EQUIV` | RED |

**Stop-gate:** 1B.1 and 1B.2. Do **not** assert `burst_velocity != fan_out_1h` on mule inbound-only rows (SSOT: burst is outbound uniqueness).

---

### Ticket 2 — Metrics contract

**RED today:** no `n_pos`; `_metrics_pass` does not require it; `score_run(all_rows=True)` ablation is a stub note.

| ID | Function | Exact asserts | RED |
|----|----------|---------------|-----|
| 2.1 | `test_fit_metrics_include_n_pos_all_families` | `set(metrics["n_pos"]) == set(LABEL_FAMILIES)`; all values `int`; `metrics["n_pos"]["normal"] >= 0` | KeyError `n_pos` |
| 2.2 | `test_not_comparable_when_n_pos_below_30` | for each fraud family: `metrics["not_comparable"][fam] is (metrics["n_pos"][fam] < 30)` | KeyError |
| 2.3 | `test_score_run_all_rows_n_pos_matches_y_length_by_family` | build y from scored frame; `n_pos[f] == (y==f).sum()` | missing / mismatch |
| 2.4 | `test_gtest_ablation_copied_not_refit` | `score_run(..., all_rows=True)`; `app_ablation_source == "champion_fit"`; `with_app_flags` / `without_app_flags` keys exist | stub `note` only |
| 2.5 | `test_metrics_pass_false_without_n_pos` | call `_metrics_pass` on a copy with `n_pos` deleted → `False` | currently may True |
| 2.6 | `test_cost_sketch_lab_not_india` | `cost_sketch["unit"] == "lab_not_india"`; weights 10, 1, 3, 8 | missing |
| 2.7 | keep `test_app_ablation_reported` | EXISTS | keep |

**Stop-gate:** 2.1 and 2.5.  
**Weak:** `n_pos > 0` on n=20 for all families — **forbidden** (may be zero); use `not_comparable` instead.

---

### Ticket 3 — Nested protocol

**RED today:** threshold from outer eval (`fit.py` ~372–381); no `inner_folds_from_train`; HGB has no `early_stopping=False`.

| ID | Function | Exact asserts | RED |
|----|----------|---------------|-----|
| 3.1 | `test_inner_val_is_last_20pct_train_calendar` | construct split_df with known timestamps; inner_val max ts ≥ all inner_fit ts; count ≈ 20% of **train** rows by calendar span not row shuffle | ImportError |
| 3.2 | `test_op_threshold_event_ids_subset_inner_val` | spy/record ids passed into `_tpr_at_fpr`; `ids <= inner_val_event_ids`; `ids.isdisjoint(outer_eval_ids)` | fail (ids from eval) |
| 3.3 | `test_diagnostic_ap_by_family_present` | `"diagnostic_ap_by_family" in metrics`; `"inner_val_protocol" == "last_20pct_train_calendar"` | missing |
| 3.4 | `test_hgb_early_stopping_false` | `inspect.getsource(fit_champion)` contains `early_stopping=False` **or** mock `HistGradientBoostingClassifier` and assert kwarg | fail |
| 3.5 | keep shuffle tests | EXISTS | keep |
| 3.6 | `test_recipe_hash_sha256_features_json` | `len(metrics["recipe_hash"]) == 64` hex | missing |
| 3.7 | `test_inner_fold_never_opens_seed_43_path` | monkeypatch `Path.read_text` / parquet read; fail if path contains `make-gtest` or sidecar `world_seed==43` | should pass if T3 does not touch 43 |

**Stop-gate:** 3.2.

---

### Ticket 4 — Makefile

Not Plan 08 pytest. **Unit the Makefile as text.**

| ID | Function | File | Exact asserts | RED |
|----|----------|------|---------------|-----|
| 4.1 | `test_makefile_generate_scale_has_no_t13_vector_id` | `tests/test_makefile_defend.py` **ADD** | `Path("Makefile").read_text()`; `"generate-scale"` block does **not** contain `t13-upi-impersonation-app` | currently contains it |
| 4.2 | `test_makefile_generate_validate_still_t13` | same | `generate-validate` **does** contain that vector_id | keep |
| 4.3 | `test_makefile_has_defend_gtest_all_rows` | same | targets `defend-fit`, `defend-gtest`, `defend-gdev` exist as `.PHONY` or recipe names | missing |
| 4.4 | `test_validate_all_does_not_call_generate_scale` | `validate-all` recipe has no `generate-scale` | keep |

Plan 08 E2E is **human**: `make generate-scale defend-fit defend-gtest` — not CI.

---

### Ticket 5 — Optuna (SHOULD)

| ID | Function | Exact asserts | RED |
|----|----------|---------------|-----|
| 5.1 | `test_tune_champion_never_reads_world_seed_43` | wrap parquet/sidecar open; raise if 43 | ImportError until T5 |
| 5.2 | `test_best_params_json_written` | after tune, `models/{run_id}/best_params.json` exists; `score_run` works if study pickle deleted | |
| 5.3 | `test_optuna_skipped_small_n` | n=20 → metrics or log `optuna_skipped_small_n` | |
| 5.4 | `test_optuna_objective_is_not_min_family_ap` | `inspect.getsource(tune_champion)` must not contain `min(` over family AP as objective; must contain penalty or `average_precision` | |

---

### Ticket 6 — Loop M

**RED today:** no `n_pos` in comparison; no `family_chosen_from_slice`.

| ID | Function | Exact asserts | RED |
|----|----------|---------------|-----|
| 6.1 | keep `test_loop_m_g_test_new_seed_reports_ap_and_fpr` | `catalog_solved is False`; seeds 42≠43; extra cap | GREEN |
| 6.2 | `test_loop_m_comparison_n_pos` | `"n_pos" in comparison` or `comparison["n_pos_before"]` documented — **lock:** `comparison["n_pos_before"]` and `n_pos_after` dicts of families | missing |
| 6.3 | `test_loop_m_rejects_family_chosen_from_gtest` | `run_loop_m(..., family_chosen_from_slice="gtest")` raises; `"43"` rejected | TypeError/missing arg then must raise |
| 6.4 | keep HTTP denylist | EXISTS | |
| 6.5 | `test_loop_m_extra_seed_offset_10007` | sidecar of extra run `world_seed == 42 + 10007` | check existing code |
| 6.6 | keep `test_loop_m_rejects_same_seed` | EXISTS | |

**Stop-gate:** 6.3.

---

### Ticket 7 — Loop T (MUST) — `tests/test_loop_t.py`

Use **tmp copies** of `v0_rules.yaml`; never commit approve against repo YAML in CI (patch `DEFAULT_RULES_PATH`).

| ID | Function | Exact asserts | RED |
|----|----------|---------------|-----|
| 7.1 | `test_mine_synthetic_fn_emits_parseable_predicate` | synthetic matrix; each `when` clause `parse_predicate` OK; `op in {==,!=,>=,<=,>,<}` | ImportError |
| 7.2 | `test_jaccard_duplicate_rejected` | candidate `when` Jaccard `(field,op)` vs `mule-fan-in-burst` > 0.8 → `verdict=="duplicate_of_live_rule"` | |
| 7.3 | `test_stamp_columns_not_in_tree_feature_list` | exported feature names ∩ `{call_active_flag,copy_paste_payee_flag,pause_ms,urgency_pressure,beneficiary_changed,gstin_checksum_ok,lookalike_domain_flag}` == ∅ | |
| 7.4 | `test_gate_fpr_rejects_above_0_002` | construct candidate that fires on >0.2% of **gdev_gate** genuines → not in `proposed` | |
| 7.5 | `test_gdev_mine_gate_event_ids_disjoint` | `len(mine & gate)==0`; mine earlier calendar than gate | |
| 7.6 | `test_mine_never_opens_seed_43` | any path with `world_seed==43` or `make-gtest` → test fails the mine call | |
| 7.7 | `test_llm_cannot_mutate_when` | stub LLM returns `{"id":"x","reason":"y","when":["fan_in_1h >= 99"]}`; draft `when` equals tree `when` | |
| 7.8 | `test_draft_not_in_load_v0_rules_until_approve` | after mine, `load_v0_rules(tmp)` ids unchanged; after `approve`, new id present | |
| 7.9 | `test_yaml_remains_list_root_no_meta_key` | `yaml.safe_load` after approve is `list`; no document key `_meta` | |
| 7.10 | `test_rollback_restores_backup_file` | approve → `data/rules/backups/v0_rules.v1.yaml` exists → rollback → live YAML equals backup of v0 | |
| 7.11 | `test_insufficient_fn_skipped` | n_fn < 10 → `status=="skipped"`, `reason=="insufficient_fn"` | |
| 7.12 | `test_insufficient_gate_skipped` | gate genuines < 30 → `insufficient_gate` | |
| 7.13 | `test_forbidden_field_never_enqueued` | inject `when` with `technique_id` → `parse_predicate` fail, not queued | |
| 7.14 | `test_http_four_routes_only` | `defend.py` source: `/defend/loop-t/mine`, `/rules/drafts`, `/rules/approve`, `/rules/reject` present; `/rules/edit` and `/fp-propose` **absent** | |
| 7.15 | `test_fp_inbox_function_threshold_0_005` | Python `fp_inbox(gdev_df)` not HTTP; rule with FPR>0.005 listed | optional helper |

HTTP E2E: `tests/test_defend_api.py` after T7:

- `POST /defend/loop-t/mine` body `{"train_run_id": "...", "gdev_run_id": "...", "family": "mule"}` → 200; if skipped, `reason` in `{insufficient_fn, insufficient_gate}` only.
- Approve on tmp rules path via dependency injection if needed.

**Stop-gate:** 7.6, 7.8, 7.9.

---

### Ticket 8 — Isolation Forest — `tests/test_eval_iso.py`

| ID | Function | Exact asserts | RED |
|----|----------|---------------|-----|
| 8.1 | `test_iso_not_called_when_pred_mule` | mock IF `predict`; `pred_family="mule"` → predict call count 0 | |
| 8.2 | `test_brake_iso_upgrades_allow_only` | `brake(..., iso_notify=True)` after T8 kwarg: mule still `mule_credit_restrict`; APP `hold` unchanged; `allow`→`notify` and `"iso_anomaly"` in reasons | need kwarg |
| 8.3 | `test_iso_feature_cols_stamp_free` | frozen list equals SSOT: `account_age_days, payee_history_count, amount_vs_p30, fan_in_1h, fan_out_1h, fan_in_unique_payers_1h, burst_velocity, is_new_payee, is_new_device`; no APP/invoice/`rule__` | |
| 8.4 | `test_iso_aborts_if_genuine_notify_gt_0_05` | force high notify rate → `enabled_default` false / IF not in score path | |
| 8.5 | `test_coverage_named_gaps_unchanged_by_iso` | T06,T07,T20,T21,T22,T23 still `named_gap` | |

---

### Ticket 9 — Isotonic

| ID | Function | Exact asserts |
|----|----------|---------------|
| 9.1 | `test_ece_before_after_keys` | both present, floats in [0,1] |
| 9.2 | `test_stage2_skipped_n_pos_lt_50` | log or metrics flag |
| 9.3 | `test_calibrated_pmap_sums_to_one` | per-row sum abs err < 1e-6 |

---

### Ticket 10 — Bootstrap / permutation

| ID | Function | Exact asserts |
|----|----------|---------------|
| 10.1 | `test_cluster_bootstrap_ci_ordered` | `low < high` per family with n_pos≥1; `n_resamples==200` in CI tests |
| 10.2 | `test_permutation_on_inner_val_not_gtest` | importance path not `make-gtest`; features ⊆ allowlist |
| 10.3 | `test_top_features_not_correlation_only` | `inspect.getsource(_top_features)` uses `permutation_importance` after T10 |

---

## 4. Brake / rules (already GREEN — extend, do not weaken)

| EXISTS | Must remain |
|--------|-------------|
| `test_brake_app_not_decline_ato_may_decline_mule_payee_restricts` | APP never decline; ATO may; mule restrict |
| `test_calm_down_allow_even_if_weak_model_score` | calm + no hard → allow |
| `test_forbidden_predicate_rejected` | `parse_predicate` |
| `test_v0_yaml_has_required_kinds_and_no_forbidden_fields` | 9 live rules |

**ADD 8.2** when Brake gains `iso_notify`.

---

## 5. ML validation — `tests/test_ml_validation.py` (ADD)

`n_customers=20` unless marked slow. **Do not require n_pos>0 for all five families on n=20.**

| ID | Function | Pass | Fail-if-weak |
|----|----------|------|----------------|
| ML.1 | `test_n_pos_key_complete` | `n_pos` keys == `LABEL_FAMILIES` | asserting all fraud n_pos>0 |
| ML.2 | `test_app_ablation_with_ge_without` | `with_app_flags["average_precision"] >= without` − 1e-9 (stamp direction; equality allowed if no APP rows) | forcing `>` when n_app=0 |
| ML.3 | `test_invoice_ap_finite_when_n_pos_positive` | if `n_pos["invoice_fraud"]>0` then AP is finite | requiring AP on n=20 always |
| ML.4 | Loop M disjoint / solved | call existing tests | duplicate |
| ML.5 | `test_y_not_technique_id` | EXISTS in fit | |
| ML.6 | SLOW `test_n80_all_fraud_families_positive_n_pos` | `@pytest.mark.slow`; `n_customers=80`; all five fraud `n_pos >= 1` | putting this in default CI |

---

## 6. E2E Defend HTTP — extend `tests/test_defend_api.py`

Existing `test_defend_fit_and_score_http`: n=20, seed 42, postgres. **After T2 it is RED** until `n_pos` is in metrics (add assert).

| ID | Sequence | Body / params | Must assert | Must not |
|----|----------|---------------|-------------|----------|
| E.1 | `POST /defend/fit` | `{"run_id":"defend-cd-http","world_seed":42}` | 200; `protocol==time_cut_2_3_plus_entity_holdout`; after T2 `n_pos` | denylist strings |
| E.2 | `POST /defend/score` | `{"run_id","model_run_id"}` | 200; `action_histogram` keys ⊆ Brake enum; sum counts == n_rows | `all_rows` default is **not** G-test |
| E.2b | ADD `POST /defend/score` or internal `score_run(all_rows=True)` on a **seed-43** pop | generate second pop `world_seed=43`, same n, `run_id=defend-cd-gtest` | `protocol == "g_test_full_population"` (see `fit.py` all_rows branch); `n_pos` sums to row count | using eval-fold protocol as headline |
| E.3 | `POST /defend/loop-m` | existing + after T6 `family_chosen_from_slice":"diagnostic"` | 200; `catalog_solved is False`; `train_seed != gtest_seed` | inferring family from 43 |
| E.4 | `GET /defend/coverage-map` | | `technique_count==24` | |
| E.5 | T7 mine | see 7.14 | 200 | 500 |
| E.6 | T7 approve on **tmp yaml** | | live list grows | mutating committed `data/rules/v0_rules.yaml` in CI |

Banned in every JSON: `TRAIN_DENYLIST` names (already in existing test).

---

## 7. E2E Generate → Defend — `tests/test_generate_defend_e2e.py` (ADD)

All in tmp `runs_dir`. No Plan 08.

| ID | Steps | Exact | RED until |
|----|-------|-------|-----------|
| GD.1 | `run_population(None, run_id="gd1", n_customers=20, n_merchants=8, sim_days=45, world_seed=42, pin=True, vector_id=None)` → `fit_champion` → `score_run` default | sidecar `world_seed==42`; metrics keys after T2 | T2 keys |
| GD.2 | After T1A: train parquet of GD.1 | invoice cols present; if any `label_family==invoice_fraud`, those rows `beneficiary_changed==True` | T1A |
| GD.3 | Second pop `run_id="gd1-gtest", world_seed=43`, same n; `score_run(gd1-gtest, model from gd1, all_rows=True)` | `world_seed` 43 sidecar; 42 parquet mtime unchanged (stat before/after) | |
| GD.4 | `run_loop_m("gd1", "app_fraud", train_seed=42, gtest_seed=43)` | extra sidecar seed `10049`; extra event_ids ∩ gtest ids == ∅ | EXISTS pattern |
| GD.5 | `GET` coverage after generate+seed catalog | 24 cells; T07 named_gap | EXISTS handoff |

---

## 8. Coverage / Identify handshake

| ID | Function | File | Assert |
|----|----------|------|--------|
| C.1 | `test_coverage_map_has_24_techniques` | handoff | EXISTS |
| C.2 | `test_named_gaps_t06_t07_t20_t21_t22_t23` | ADD `tests/test_defend_handoff.py` | each `coverage_status==named_gap` (or catalog `generate_mode==name_only` as SSOT) |
| C.3 | `test_named_gap_for_t07` | EXISTS | keep |
| C.4 | T7 approve (tmp): if new rule fields overlap a `case_only` spec, that cell becomes `live_rule` | ADD after T7 | do not fake 24 live_rule |

---

## 9. VALIDATION.md G1–G7 → tests

| Gate | Test |
|------|------|
| G1 future leak | `test_causal_payee_history_ignores_future` EXISTS; 1B.1 must snapshot **before** append |
| G2 split | `test_eval_split.py` EXISTS + 3.1 |
| G3 APP flags ≠ truth | ablation EXISTS + ML.2 |
| Allowlist | export + fit denylist |
| Loop M photographer | 6.1, GD.4 |
| Loop T | 7.6–7.9 |
| Coverage honesty | C.1–C.2 |
| Latency hang | existing `batch_seconds_1k < 120` in HTTP test |

---

## 10. Metrics contract checklist (`_metrics_pass`)

After T2, `_metrics_pass` **must** require: `ap_by_family`, `n_pos`, `not_comparable`, `tpr_at_fpr` with keys `"0.001"`,`"0.005"`,`"0.01"`, `genuine_fp`, `f1_at_op`, `app_ablation`, `authgate_ms`, `mule_entity_recall`, `protocol`.  
After T3 also: `inner_val_protocol`, `diagnostic_ap_by_family`, `recipe_hash`.  
Test: 2.5 plus `test_metrics_pass_requires_tpr_keys` ADD (delete `"0.001"` → fail).

---

## 11. Existing tests — do not delete (inventory)

`test_eval_fit.py`: `test_fit_y_is_family_enum_not_technique`, `test_reported_split_is_not_shuffle`, `test_app_ablation_reported`, `test_fit_reproducible_seed_42`  
`test_eval_split.py`: schema, time cut, entity holdout, party ids not in X, join-safe  
`test_eval_loop_m.py`: new seed AP/FPR, same-seed reject  
`test_eval_rules_brake.py`: yaml kinds, fan_in value, calm_down, Brake typology, invoice no gstin, forbidden predicate, coverage 24, yaml when list  
`test_defend_api.py`: fit+score+coverage+loop-m HTTP  
`test_defend_handoff.py`: Loop I T13, coverage 24, T07 gap, miss stays open  
`test_sim_world.py`: causal history, linear FeatureComputer  
`test_sim_inject.py`: mix families, T12 ATO, fan_in not catalog, APP no ledger scan, APP flags, invoice checksum event (payload-level — **insufficient alone for T1A**)

---

## 12. Definition of done (sprint)

| Bar | Evidence |
|-----|----------|
| Honesty | 1A.1–1A.4 and 1B.1–1B.2 GREEN after being RED |
| Metrics | 2.1, 2.5, MET keys GREEN |
| Nested | 3.2 GREEN |
| Makefile | 4.1 GREEN (no T13 on scale) |
| Loop M | 6.1 GREEN, 6.3 GREEN |
| Loop T | 7.6, 7.8, 7.9 GREEN |
| E2E | GD.1–GD.4 GREEN on n=20 |
| Honesty | n=20 Loop M `not_comparable` **allowed**; do not force `improved` |
| Walkthrough | Plan 08 JSON is Makefile, not pytest |

If a new test is GREEN on `HEAD` before the ticket: **it is invalid.** Fix the oracle.
