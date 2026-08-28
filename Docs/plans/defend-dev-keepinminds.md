# AegisLoop Defend — developer keep-in-minds (pre-mortem)

**Audience:** a coding agent and a human ticking boxes **during PRs and tickets**, not a forum for architecture debate.  
**SSOT for how to code:** [`defend-execution-ssot.md`](defend-execution-ssot.md). Architecture meaning: [`defense-architecture.md`](defense-architecture.md). Ticket map: 7 = Loop T MUST, 8 = IF, 9 = isotonic, 10 = bootstrap. Loop G is not a ticket.  
**How to use:** Agent handbook is the Cursor Defend Peak plan. Implement from [`defend-execution-ssot.md`](defend-execution-ssot.md). Tests from [`defend-test-tracker.md`](defend-test-tracker.md). This file is PR do-nots only.  
**Verified leak primitives (2026-08-28):** `packages/eval/split.py` `assert_no_x_leak`; `packages/sim/export.py` `TRAIN_DENYLIST` / `assert_train_schema`; `packages/policy/rules.py` `FORBIDDEN_RULE_FIELDS` / `parse_predicate`.

If a test already exists, the line says **exists:** path. If it does not, the line says **ADD:**.

---

## Frozen seed table (do not shop)

| Seed | Name | Allowed uses | Forbidden uses |
|------|------|----------------|----------------|
| **42** | Train world + champion `random_state` + `assign_folds` RNG | `run_population(..., world_seed=42)`; `models/features.json` `random_state`; fold entity holdout | Headline AP; HPO “try another train seed until AP looks good” |
| **43** | **G-test photographer** | One-shot headline AP, genuine FPR, Loop M **after** extras on train only (`score_run` / `all_rows=True`) | Family pick, specialist attach, Optuna, FE gate, rule mining, FN harvest, “just peek” |
| **44** | **G-dev** | Inner-protocol confirmation, harvest FN, optional one OVR attach decision, rule recall backtest | Headline slide; shopping then quoting 43 as if independent |
| **45** | Confirmation world | **Only if 43 was peeked** (HPO/FE/attach/mining/family pick). Then 45 is the reported number and 43 is burned | Using 45 as a third shopping catalog |
| **99** | Canary convention | FinCEN chain / `run_canary` vault; never mixed into champion train parquet | Training AuthGate; Loop M extras; quoting canary AP as G-test |
| **42 + 10007** | Loop M extra population | Extra family mix for train copy only (`packages/eval/loop_m.py`) | Same seed as G-test; appending extras onto 43 parquet |

Persist `gtest_opened_at` (ISO timestamp) the first time seed **43** metrics are computed for a walkthrough run_id. **ADD:** field on score/Loop M JSON + a test that a second “exploration” fit that reads 43 after that stamp cannot change the frozen headline blob without bumping a recipe version.

---

## Council rulings — do not reopen (tick while coding)

- [ ] **Do not** ship five live family models or five pickled HGBs. Live AuthGate is **one** multiclass `HistGradientBoostingClassifier` with `y = label_family`, **nine** live YAML rules (`data/rules/v0_rules.yaml`), and `packages/eval/brake.py`. Family AP is a **metric** (`ap_by_family`), not five heads.
- [ ] **Do not** put live decision-tree specialists on APP or invoice. Those families are **injector stamps** (`app_session` always writes the four session flags; `doc_beneficiary` always writes beneficiary+checksum+lookalike true). A depth-3 tree on those flags is the YAML rule with worse calibration.
- [ ] **Do not** attach even one OVR adapter by default. Default is **zero specialists, honestly**. At most **one** OVR later, gated on **G-dev 44** (not G-test 43), never on stamp columns (`call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`, invoice envelope booleans as the sole split).
- [ ] **Do not** put AutoGluon / FLAML / LightGBM AutoML on the demo path. **Optuna = AutoML** for this contest: nested, train-only, freeze `models/features.json`. AutoGluon is overnight write-up challenger only.
- [ ] **Do not** implement Loop M as the `else` of a “clean diagnose tree → YAML, else Generate” fork. **Loop M is the clickable data loop.** Trees = **Loop T** (execution SSOT Ticket 7, MUST). APP/invoice will **always** clean-split on injector flags; that must not skip Loop M for mule/ATO/identity.
- [ ] **Do not** use G-test **43** as a coach. Family pick / specialist attach / HPO / FE / rule mining **never** on 43. Use inner-val + G-dev **44**. If 43 was peeked, confirmation is **45**.
- [ ] **Do not** send G-test rows (or per-row feature dumps from 43) to an LLM. LLM output is **id + reason only**. `when` predicates come from tree splits **in code**. Equality check: LLM `when` strings must `parse_predicate` to the same `Predicate` tuples as the tree export.
- [ ] **Do not** build Loop G, live specialists, or an Optuna circus before **Ticket 1** (invoice booleans on `X`, `fan_in_unique_payers_1h`, `burst_velocity` not a clone of `fan_out_1h`). Honesty floor first.

---

## Leakage

The single biggest way this looks great in dev and dies at judging.

- [ ] No denylist column in model `X`: `vector_id`, `world_seed`, `technique_id`, `is_authorized_push`, `label_class`, `payload`, `gstin` string, `transcripts`, plus the rest of `TRAIN_DENYLIST` (`injector_id`, `simulatable_signals`, `persona_type`, `economic_class`). **exists:** `assert_no_x_leak` in `packages/eval/split.py`; `assert_train_schema` in `packages/sim/export.py`; called from `fit_champion` / `_attach_rule_bits` / `score_run` in `packages/eval/fit.py`. **Keep calling it on every fit**, not only CI once. **exists:** denylist column checks in `tests/test_sim_export.py`, `tests/test_eval_split.py`, `tests/test_eval_fit.py`, `tests/test_defend_api.py`.
- [ ] HTTP / Loop M JSON never dumps knobs. **exists:** `assert_no_denylist_payload` in `packages/eval/fit.py`; Loop M body check in `tests/test_eval_loop_m.py`.
- [ ] Split-time leakage: never `train_test_split(shuffle=True)` on events. Every published eval path uses time-sorted 2/3–1/3 plus entity holdout (`assign_folds`, protocol `time_cut_2_3_plus_entity_holdout`). **exists:** `tests/test_eval_split.py` `test_time_cut_uses_event_ts_not_shuffle`; `tests/test_eval_fit.py` `test_reported_split_is_not_shuffle`; `tests/test_eval_loop_m.py` source grep. Do not add a shuffled split “for speed” in debugging and then quote it.
- [ ] Entity leakage: the same mule payee (`VID-SIM-U-*`, `VID-SIM-APP-*`, `VID-SIM-CHAIN-*`) or held-out customer (`VID-SIM-C-*`) must not be treated as a clean train example in eval. `assign_folds` already unions late calendar **or** entity holdout. **Do not skip** entity holdout when testing a new feature. **exists:** `assign_folds` in `packages/eval/split.py`. **ADD:** an explicit test that a mule payee in the hold set never has `fold==train`.
- [ ] Rule-mining leakage: do not mine a threshold from FN rows in one fold, then backtest and report recall on **that same fold**. Do not reuse G-test 43 for diagnosis and headline. Enforce three disjoint pools mechanically: train inner-val, G-dev 44, G-test 43. **ADD:** test that the same `event_id`s do not appear in more than one of {inner-val of train run, G-dev population, G-test population}. (Same-run outer eval is diagnostic only and must be labeled as such.)
- [ ] Loop M leakage: generated extras must never land in the G-test parquet. Check `event_id` disjointness with an assertion, not a comment. **exists:** `packages/eval/loop_m.py` extra_ids ∩ G-test ids; `tests/test_eval_loop_m.py` (`evt-lm-*` disjoint from G-test).
- [ ] Harvest FN from G-test: **do not** take misses from the fold you quote in the walkthrough, generate extras, Loop M again, and report the second number on the same 43. Harvest off inner-val, same-run diagnostic (logged, not headline), or G-dev 44.
- [ ] Feature leakage via “helpful” engineering: windowed features use only events **strictly before** the scored instant (auth-time `G(t−)`). Today `FeatureComputer.snapshot_and_apply` prunes deques then appends the current edge **after** the snapshot (`packages/sim/features.py`). Any new feature must keep that order. **ADD:** a tiny synthetic-clock fixture (two inbound after t vs before t) if you add unique in-degree or extra windows.
- [ ] Synthetic APP tells as free wins: `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure` are always on for `app_session` injects (`DEFAULT_SIGNALS["app_session"]` in `packages/sim/inject/mix.py`) and forced false on non-APP train rows (`train_rows` in `export.py`). Ablate with vs without those four columns and report **both**. Do not lead with only the flattering AP. **exists:** `_app_ablation` + `tests/test_eval_fit.py` `test_app_ablation_reported`. **ADD:** run that ablation on **G-test 43**, not only same-run G-eval.
- [ ] APP flags as near-label: treating the four flags as `y` by another name. **Do not** train interaction products of those flags. **Do not** attach an APP specialist whose only splits are those flags.
- [ ] Invoice tautology: engine always sets `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag` true on invoice injects; genuine rows will be **always false** until (and unless) you simulate genuine beneficiary change. Check the genuine-row distribution is not degenerate before trusting invoice AP. After Ticket 1, YAML `invoice-beneficiary-swap` firing is expected on **injected** invoice rows; that is a stamp, not BEC skill. Do not invent GSTIN identity features to “fix” noise AP.
- [ ] Coverage `live_rule` vs fire-rate: `packages/policy/coverage.py` is **feature-name overlap** (`COVERAGE_EQUIV` in `rules.py`), not “this rule fired on T14 traffic.” T14–T19 share `app_session`. Do not sell fire-rate per TechniqueId.
- [ ] Fusion softmax splice (only if someone prototypes an OVR anyway): replacing one family’s probability without renormalizing the remaining classes silently steals mass from `normal` / mule / ATO. See Specialist risks.
- [ ] `packages/sim/injectors.py` is a **stub**: `label_family` can be `T13`. Do not train from it; do not revive it; do not delete without import check. **exists:** `tests/test_eval_loop_m.py` asserts `"injectors" not in` Loop M source.
- [ ] PSI vs this run’s priors (`packages/sim/fidelity.py`) is **sampler QA**, not live UPI fidelity. Do not write walkthrough sentences that PSI proves NPCI match.
- [ ] AuthGate hang guard is **120s / 1k rows** (`hang_guard_seconds_1k` in `models/features.json`). Do not claim Mastercard issuer SLA 50–300 ms.
- [ ] Auto-`solved`: catalog `solved` has no writer in fit/score/Loop M. Loop M returns `catalog_solved: False`. `POST /defend/miss/{vector_id}` only forces `open`. **exists:** `tests/test_eval_loop_m.py`. Do not auto-promote rules or auto-set `solved`.

---

## Overfitting

- [ ] Small-`n_pos` families: `ato` (mix share 0.05) and `invoice_fraud` (0.10) can memorize. Report **`n_pos` next to every AP**. Treat families with `n_pos` under a few dozen as `not_comparable`, not a win or loss. **ADD:** `n_pos` per family in `fit_champion` / `score_run` metrics (Ticket 2). CI `n_customers=20` is almost always not comparable — do not put it on the slide.
- [ ] Specialist trees on tiny data: a depth-3 tree on ~40 FN rows will split by accident. Require minimum leaf support and a held-out slice. Prefer **not building** these trees as live scorers (council). If Loop T drafts rules, same min-support applies.
- [ ] **3-row tree leaves:** reject any Loop T / diagnose path whose leaf support is 1–3 rows. That is memorizing exact FN vectors, not a pattern.
- [ ] Optuna overfitting to inner-val: 30–50 trials on a small inner-val chase noise. Cap trials vs inner-val size; wall-clock cap (~90s); sanity-check best params vs `features.json` defaults (`max_depth` 3, `max_iter` 80, `learning_rate` 0.08). Wild jumps usually mean noise.
- [ ] **Do not** use **min-family AP** as the Optuna objective. Use **binary-fraud AP** on inner-val with soft penalty `binary_AP - 10 * max(0, genuine_fp - 0.01)`. Family AP is report-only.
- [ ] **Do not** use sklearn HGB `validation_fraction` / internal early stopping as the published protocol. It ignores temporal ordering and hides a random holdout. Tune `max_iter` ∈ [40, 200] in Optuna instead; refit on full outer train with frozen `max_iter`.
- [ ] **Class imbalance:** champion must use balanced weighting (`sample_weight` per class via `_class_weight`, or equivalent) before any OVR adapter. Unweighted HGB naps on `normal`. Do not skip weights thinking a specialist will fix thin families.
- [ ] Gated interaction features (≤5): lift must be checked on inner-val **and** still hold on same-run diagnostic eval. Do not add a product that helps only one of the two. Never gate on 43.
- [ ] Rule promotion overfitting: a rule that catches three specific FN rows by exact values will look perfect on the mine set. G-dev (44) or inner-val genuine holdout is mandatory; do not skip under time pressure.
- [ ] **Winner’s curse Loop M:** picking the miss family from the **lowest G-test AP**, generating extras, then reporting improvement on **that same 43** is selection bias. Pick miss family from inner-val or G-dev 44 (with `n_pos` support). Rescore frozen 43 once. If you already used 43 to pick the family, you peeked — confirmation 45.
- [ ] **Inner-val vs Loop T:** Optuna uses inner-val. Loop T uses G-dev 44 `gdev_mine`/`gdev_gate`. Do not mine rules on inner-val.

---

## Training / validation

- [ ] Nested protocol: HPO and rule mining touch inner-val / train only. G-test 43 is touched **exactly once** per reported number, at the end, for scoring. Re-running 43 while iterating and reporting the best is leakage in disguise. Policy: **one-shot 43**; if you peeked, move the headline to **45**.
- [ ] **Inner-HPO vs inner-sel:** after outer train (first 2/3 calendar minus entity holdout), take the last 20% of **train** calendar as inner val (`defend-peak-handoff.md` Ticket 3). If you both tune and select features/rules, nest further or time-box so Optuna does not see the rule-mining slice. **ADD:** inner split in `packages/eval/split.py` / `fit.py`; test that HPO code cannot open G-test parquet.
- [ ] Refit on **full outer train** after HPO with frozen params. Scoring the inner-fit-only model against a full-train baseline is an unfair comparison. Champion path today fits the outer train fold once (`fit_champion`) — when Optuna lands (Ticket 5), refit is mandatory.
- [ ] Frozen recipe: after `models/features.json` is frozen for a G-test run, do not quietly edit and re-score without bumping a version / recording `recipe_hash`. Study pickle is not required to score.
- [ ] Calibration: multiclass `predict_proba` is not per-class calibrated. Threshold from inner-val (`operating_point_fpr`, default **0.01** in recipe) may not transfer. Check a calibration curve before calling a G-test drop a “regression.”
- [ ] Headline JSON field is G-test, not same-run eval. Label same-run outer eval **diagnostic**. Walkthrough grabs the G-test blob (`gtest_before` / `gtest_after` in Loop M, or `score_run` on the 43 run_id).
- [ ] Named seeds 42 / 43 / 44 / 45 / 99 canary — see table above. Do not invent a sixth “lucky” seed for the slide.
- [ ] `gtest_opened_at`: first read of 43 for a submission run is logged; further coaching on 43 is a protocol violation.
- [ ] `n_pos` every cell of `ap_by_family`, TPR tables, Loop M before/after. **ADD:** Ticket 2.
- [ ] APP ablation on **43**, not only G-eval. **exists** on current `fit_champion` eval fold; **ADD:** persist ablation on G-test score JSON.
- [ ] Cat 4 rows must not appear in G-test. `y` is never `T01`–`T24`. **exists:** `build_matrix` / `fit_champion` technique-id assertions; `tests/test_eval_fit.py` `test_fit_y_is_family_enum_not_technique`.
- [ ] Genuine FPR epsilon **conflict**: `VALIDATION.md` promotion gate uses **ε = 0.002**; `models/features.json` `loop_m.genuine_fpr_eps` is **0.02**. **Pick both, named, in the recipe — not one anonymous epsilon.** Freeze `loop_m.genuine_fpr_eps = 0.02` as Loop M **comparison slack** (noisy, especially n=20). Freeze `rule_promote_genuine_fpr_eps = 0.002` for HITL **rule** promotion on genuine holdout when Ticket 10 exists. Do not apply 0.002 to Loop M on CI fixtures (false fails). Do not apply 0.02 as a production-like promotion story. Operating-point FPR for TPR curves stays `operating_point_fpr: 0.01` (0.1% / 0.5% / 1% via `tpr_at_fpr`).
- [ ] **Isotonic calibration (Ticket 8, SHOULD):** fit on inner-val only, never G-test. Stage 1: isotonic on binary `fraud_score = 1 - pmap["normal"]` for operating-point threshold. Stage 2 (optional): per-family isotonic OVR, then **renormalize** calibrated probs to sum to 1. Report `ece_before_cal` / `ece_after_cal` on G-dev **44** before walkthrough claims. Calibrate base HGB before any OVR adapter.
- [ ] **Bootstrap CI (Ticket 9):** cluster-bootstrap by payee entity on G-test 43 — **not** IID row bootstrap (mule rows correlate within entity). n=1000 resamples; report 2.5th/97.5th percentiles as 95% CI. Wide CI on thin families is honest.
- [ ] **Permutation importance (Ticket 9):** compute on inner-val or G-dev **44**, not G-test 43, before freeze. Log top features for walkthrough explainability. Post-freeze G-test importances are informational only — no feature re-selection from them.

---

## Feature engineering

- [ ] Duplicate/collinear: today `burst_velocity == fan_out_1h` in `packages/sim/features.py`. Ticket 1: drop from allowlist **or** redefine as a **different** causal quantity (e.g. unique outbound payees 1h). Update `seasoning-burst` in `data/rules/v0_rules.yaml` if the name changes. Afterward, grep for other accidental clones before adding columns.
- [ ] Unique in-degree: add `fan_in_unique_payers_1h` (unique payer ids, last hour, **payee**, past edges only). Keep `fan_in_1h` as event count. Two inbound from the same payer in 1h → unique=1, count=2.
- [ ] Invoice booleans onto allowlist: copy `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag` from `ev["payload"]` through `replay_features` / `snapshot_and_apply` into `features_auth`, then `TRAIN_ALLOWLIST` / `train_rows`. **Never** export `gstin` string or raw `payload` (`payload` stays on `TRAIN_DENYLIST`).
- [ ] Auto-FE ≤5 products of **allowlisted numerics** only, after Tickets 1–5 green, after inner-val lift vs base allowlist. Check **correlation with mains**, not only standalone AP. `fan_in_1h * account_age_days` that tracks `fan_in_1h` is not a new measurement.
- [ ] **No Featuretools / DFS** on the event log.
- [ ] **No APP-flag products** (and no invoice-flag products that are tautological stamps).
- [ ] **No GSTIN** as a categorical / identity leak.
- [ ] Near-constant engine artifacts (flags always true on one label, always false on genuine) get ablated and documented, not celebrated as AP.
- [ ] Windows stay **O(n) deques** on `AccountRuntime`. Do not re-scan full history per row before the Plan 08 2400×120×90 run.
- [ ] Self-median (or mean) amount windows already in `amount_vs_p30` beat random pairwise products. Prefer missing **measurements** (invoice envelope, unique in-degree) over products.
- [ ] Still forbidden on X: denylist; `liveness_score` / `doc_consistency` copied onto every payment (onboarding-only); `is_authorized_push`; embeddings.

---

## Isolation Forest (Ticket 8, conditional GO)

Architecture SSOT: **GO with mandatory modifications.** IF is a stamp-free **notify** upgrade on confident-normal rows — not a family detector, not Cat-4 coverage, not a substitute for Loop M.

- [ ] **Do not** train IF on champion X (APP flags, invoice booleans, `rule__*` bits are stamps). Freeze `iso_feature_cols`: stamp-free numerics only (`fan_in_1h`, `fan_in_unique_payers_1h`, `fan_out_1h`, `account_age_days`, `payee_history_count`, `amount_vs_p30`, `is_new_payee`, `is_new_device`, `burst_velocity`/replacement, `rail`, `kyc_tier`).
- [ ] **Do not** train IF on G-test 43/44 or tune `contamination` on G-test. Train on quiet-world `label_family == normal` rows from **inner-fit** calendar only. Pick `iso_contamination` on inner-val genuine rows where `iso_genuine_notify_rate <= iso_genuine_fpr_floor` (default 0.01); abort IF if no contamination satisfies the floor.
- [ ] **Champion confidence gate:** IF runs only when `pred_family == "normal"` AND `pmap["normal"] >= iso_p_normal_ceiling` (frozen on inner-val — high-confidence all-clear, not merely low fraud score).
- [ ] **Brake insertion:** after step 8 (`allow`), if `iso_notify` → upgrade to `notify` with `reason_codes += ["iso_anomalous"]`. IF must **not** undo mule restrict, APP hold, decline, step_up, or existing notify.
- [ ] **Do not** claim IF closes T06/T07/T20–T23 named gaps or detects BIN testing / poisoning. IF = unusual pattern on existing stamp-free features only.
- [ ] Report `iso_genuine_notify_rate`, `iso_triggered_rate`, and genuine FPR **with vs without** IF at the same operating point. If notify volume exceeds `iso_genuine_fpr_floor`, leave IF off.

---

## Specialist risks

**Specialists are NOT the default architecture.** Council default: zero live specialists. APP/invoice DTs are injector stamps, not skill. If someone still prototypes **at most one** OVR adapter, these bugs apply. Activation **never** on G-test 43; only G-dev 44, and never using stamp columns as the attach criterion.

Keep the fusion / threshold / activation checks:

- [ ] Score-fusion: the adapter may override **only its own family’s** column; remaining class probabilities stay a valid simplex (renormalize explicitly). A confident specialist must not silently zero or distort the other families / `normal` (softmax splice).
- [ ] Threshold mismatch: champion and adapter are calibrated on different objectives. Do not compare raw scores as “who wins the row.” Document one fusion rule (e.g. override only if adapter score exceeds its **inner-val / G-dev** calibrated threshold). Do not hand-tune per family on 43.
- [ ] Activate with a number: champion AP for that family measurably dead given `n_pos`, on **inner-val or G-dev 44**, not “invoice looked low while scrolling,” and not G-test AP then quoting G-test again.
- [ ] Do not pickle five family models “just in case.” `champion.joblib` is **one** model.

---

## LLM-in-the-loop

- [ ] LLM never sees G-test rows, 43 feature tables, or FN vectors from the reported fold. Inputs: train/inner-val **statistics**, tree split export, catalog card fields already in Identify HITL — not live auth scoring (`VALIDATION.md` G7 / anti-pattern: LLM scores the live payment).
- [ ] LLM schema is **`{"id": str, "reason": str}` ONLY**. LLM MUST NOT output, modify, or invent `when` clauses, `kind`, `min_score`, `applies_to`, or `technique_ids`. Anything else in LLM output is silently ignored.
- [ ] Schema equality of `when` (HARD CHECK in `loop_t.py`): after LLM returns, assert `draft["when"] == candidate_tree_when` (exact list equality). Mismatch → **hard-reject, use auto-id, do not trust English**. This is the single most important LLM containment check in Loop T.
- [ ] LLM input NEVER contains G-test parquet rows, per-row feature dumps from seed 43, FN row vectors, or `event_id` lists. Input shape: `{"when_clauses": list[str], "applies_to": str, "family": str, "reason_examples": list[str]}` only.
- [ ] `FORBIDDEN_RULE_FIELDS` / `TRAIN_DENYLIST` validated in code before backtest, not by prompt hope. **exists:** `parse_predicate` rejects forbidden fields; `tests/test_eval_rules_brake.py`. **ADD (Ticket 7):** Loop T draft `when` runs through `parse_predicate` before HITL enqueue; test in `tests/test_loop_t.py`.
- [ ] Nearest-live novelty: Jaccard of `(field, op)` pairs vs live `v0_rules.yaml`. Jaccard > 0.8 same-`applies_to` → `verdict: duplicate_of_live_rule`, do not enqueue. Do not promote a draft restating the v0 APP rule.
- [ ] `injector_separable`: if ALL tree `when` fields are APP flags → `verdict: injector_separable_app`, no-draft. Same for invoice-only booleans. Logged and skipped; not promoted.
- [ ] FP inbox vs FN inbox: both use same `data/rules/drafts.json` but `source: "loop_t"` vs `source: "loop_t_fp"`. Identify-style verbs: `approve | reject | reject_unsafe | edit`. No auto-on. Never mix APP and ATO in one `applies_to`.
- [ ] Nondeterminism: pin prompt + model; log input/output in a ledger so the walkthrough is reproducible.
- [ ] Do not mix APP and ATO in one `applies_to`. v0 nine rules stay `status: live`. New rows stay `draft` until HITL.

---

## Metrics / reporting honesty

- [ ] AP without `n_pos` is the lie the handoff already names. Every family cell includes both.
- [ ] No cherry-picked G-test: one-shot 43 (or 45 if burned). Declare N=1.
- [ ] Loop M “improvement” always ships **cost-shaped and genuine FPR** together: AP before/after, `genuine_fp` before/after, `genuine_fp_ok` vs frozen `genuine_fpr_eps`, `n_pos`. A recall gain with an FPR spike is a disclosed trade, not a win. **exists:** comparison block in `loop_m.py` / `tests/test_eval_loop_m.py`. **ADD:** lab cost sketch (miss $ vs decline vs APP hold) at the same operating point (architecture §14 MUST).
- [ ] **ADD (Ticket 10):** `bootstrap_ci[fam]` cluster-bootstrap 95% CI per family on G-test score JSON. **ADD (Ticket 9):** `ece_before_cal` / `ece_after_cal`. **ADD (Ticket 8 if IF deployed):** `iso_genuine_notify_rate`, `iso_triggered_rate`.
- [ ] Brake typology: APP ≠ ATO ≠ mule (`packages/eval/brake.py`: APP hold / not silent decline; ATO may decline; mule `mule_credit_restrict`). Do not report a single binary “caught fraud.”
- [ ] Coverage language matches the **24 vs 4 vs 1 taper**: 24 `TechniqueId` census / 29 seed rows; **4** injector engines; **5** fraud families + `normal`; **1** multiclass HGB + **9** YAML rules. Do not claim 24 detectors or 22 Atlas recipes in default Generate.
- [ ] `champion.joblib` is one model. Do not say five family models in the walkthrough or UI.
- [ ] AuthGate latency is **laptop in-process** `predict_proba` p50/p99 (`fit.py` bench), not Decision Intelligence Pro / issuer SLA / 50–300 ms production.
- [ ] Loop M on `n_customers=20` with `ap_equal_eps=0.05` will often be `not_comparable`. Report that string. Do not claim a G-test win from the CI fixture.
- [ ] Do not lead with accuracy, “AUC 0.99,” or “beats production.” Lead with PR-AUC / AP by family, TPR@FPR 0.1/0.5/1%, genuine FPR (`VALIDATION.md` §0.2).

---

## Time-budget / scope

- [ ] **Tickets 1–4 before everything else:** (1) invoice X + unique in-degree + burst clone; (2) coverage / APP ablation / `n_pos` in artifacts; (3) nested protocol + frozen 43; (4) Plan 08 volume command (2400×120×90, full mix, not T13-only `generate-scale` pin for champion world). Anything built on an unfixed leak is redone.
- [ ] Ticket 5 Optuna is SHOULD, after 1–4. Hard wall-clock on HPO; 30–50 trials; binary AP + genuine-FPR floor objective; no HGB `validation_fraction` early stopping; do not burn the day for 0.01 AP.
- [ ] Ticket 6: Loop M is the demo loop (MUST; code exists: `packages/eval/loop_m.py`, `POST /defend/loop-m`). Polish honesty (`n_pos`, Plan 08 scale if possible). **Do not claim Loop G.**
- [ ] Ticket 7 Loop T + two-inbox HITL is **MANDATORY** (NOT optional). `packages/eval/loop_t.py` (mine), `packages/policy/rule_hitl.py` (queue/promote/rollback), `data/rules/drafts.json`, `data/rules/versions.json`. FN mining → backtest FPR gate on G-dev 44 genuine → LLM packages `id+reason` ONLY → HITL queue → approve → versioned YAML. FP inbox separately.
- [ ] Ticket 8 Isolation Forest is SHOULD, after Ticket 5. Stamp-free subset, inner-fit genuine train, contamination ablation on inner-val, Brake notify-only insertion. Abort if FPR floor fails.
- [ ] Ticket 9 isotonic + ECE is SHOULD, after Ticket 5. Inner-val fit; validate ECE on G-dev 44.
- [ ] Ticket 10 bootstrap CI + permutation importance is SHOULD, after Ticket 5. Cluster bootstrap on G-test; permutation on G-dev/inner-val only.
- [ ] **Do not fake nine loops.** Coded after these tickets: I (draft API), C (coverage read), M, T (HITL pipeline). No `packages/eval/loop_g.py`. Do not add HTTP theater for R/A/F/H/G.
- [ ] Specialist rabbit hole: timebox to zero by default. If a prototype adapter does not beat champion on G-dev with `n_pos` support, drop it and write that honestly.
- [ ] LLM packaging: one end-to-end pass with a simple prompt; no prompt-engineering loop instead of Ticket 1.
- [ ] Kill triggers (from handoff §10): Loop M `not_comparable` on n=20 → do not fake loops; APP AP dies without flags → document ablation, do not glue flags onto genuine; invoice AP still noise after flags in X → no GSTIN identity; clock dying → skip Loop G, Optuna, five models; user asks five models → translate, do not implement; Featuretools / GNN / CaseScore LLM → refuse; auto-promote / auto-`solved` → disallowed; train on eval / harvest FN from reported G-test → disallowed; `injectors.py` as train source → forbidden; live UPI / India prevalence / beat production → forbidden.

---

## Identify / Generate contracts (Defend must not break)

- [ ] Default Generate does **not** consume Atlas recipes. `run_population(db=None, vector_id=None)` uses all five fraud families and `DEFAULT_SIGNALS` in `packages/sim/inject/mix.py`. `db` without `vector_id` only checks generate-eligible Atlas is non-empty, then still uses the default mix. `vector_id` set → one family + that spec’s `simulatable_signals` into **one** mix key. Walkthrough must not say “we trained on 22 generate cards” unless `vector_id` was passed per run.
- [ ] Generate **cannot** consume FN row vectors (“replay this payment”), `technique_id` as a mix key, new AttackSpecs from miss clusters (Identify Librarian + HITL only), or scout strings as auto-Identify (`GET /defend/scout-topics` is hints). Loop M calls `run_population(..., families=frozenset({miss_family}), world_seed=train_seed+10007)` — more of the same injector, **not** Loop G knobs.
- [ ] `world.rebuild_features()` → `replay_features` **wipes** payload flags from `features_auth` unless Ticket 1 copies booleans back. Do not assume invoice YAML can fire before that copy exists.
- [ ] `label_family` is `normal | mule | identity_burst | ato | app_fraud | invoice_fraud`, never `T01`–`T24`. Stub `injectors.py` uses technique ids — do not export that as train.
- [ ] Identify never calls Generate or Defend. Nothing in fit/score/Loop M writes `solved`.
- [ ] Sidecar `knobs_used` is legal for Generate and **forbidden** in train X and Defend HTTP JSON.
- [ ] Extra row cap: `loop_m.extra_row_cap_frac` default **0.15** of original train length; ids `evt-lm-*`; timestamps shifted to train calendar; `force_train_event_ids`.
- [ ] Brake mule-first vs APP hold: `brake()` checks mule before APP (`packages/eval/brake.py`). Do not “fix” a mule+APP overlap by declining APP. Calm-down + no hard_flag → allow.
- [ ] Fidelity: PSI amount/hour vs **this run’s** priors; fraud-rate band when all families; mule `fan_in_1h` median > 5; independent recompute (anti-stub). Family-filtered Loop M sets `require_mix_rate=False`.
- [ ] Lab fraud mix 1–3% ≠ India prevalence. Shares: mule 0.40, identity_burst 0.25, ato 0.05, app_fraud 0.20, invoice_fraud 0.10.

---

## Tests that must exist or be added

- [ ] `assert_no_x_leak` on every fit/score matrix. **exists:** `packages/eval/split.py`; used in `packages/eval/fit.py`. **exists:** `tests/test_eval_split.py`.
- [ ] Export denylist / allowlist. **exists:** `packages/sim/export.py` `assert_train_schema`; `tests/test_sim_export.py`.
- [ ] `FORBIDDEN_RULE_FIELDS` on live YAML. **exists:** `parse_predicate`; `tests/test_eval_rules_brake.py`.
- [ ] Forbidden fields in YAML **drafts** (Loop I / optional T). **ADD:** parse draft `when` before HITL.
- [ ] `event_id` disjoint pools: train inner-val vs G-dev vs G-test. **ADD.**
- [ ] Loop M extras not in G-test. **exists:** `tests/test_eval_loop_m.py` and `loop_m.py`.
- [ ] APP ablation keys (`with_app_flags`, `without_app_flags`, `app_metric_died_without_synthetic_flags`). **exists:** `tests/test_eval_fit.py` `test_app_ablation_reported` (today on fit eval). **ADD:** same keys on G-test 43 score JSON.
- [ ] Invoice columns after Ticket 1: `beneficiary_changed` / `gstin_checksum_ok` true on invoice parquet rows; genuine false; `gstin` and `payload` absent; `rule__invoice-beneficiary-swap` can be 1 on an invoice fixture. **ADD:** extend `tests/test_sim_export.py`, `tests/test_sim_inject.py`, `tests/test_eval_rules_brake.py`, `tests/test_eval_fit.py`.
- [ ] Unique in-degree fixture (same payer twice → unique=1, `fan_in_1h`=2). **ADD.**
- [ ] `burst_velocity` not equal to `fan_out_1h` unless documented temporary alias removed from X. **ADD.**
- [ ] `n_pos` keys for every `ap_by_family` family. **ADD.**
- [ ] HPO cannot read G-test parquet. **ADD** with Ticket 5 (and Ticket 3 protocol string).
- [ ] No shuffle split as reported protocol. **exists:** source greps in split/fit/loop_m tests.
- [ ] Coverage still 24 cells. **exists:** `tests/test_defend_handoff.py`.
- [ ] `catalog_solved is False`. **exists:** `tests/test_eval_loop_m.py`.
- [ ] Do not delete existing suites listed in handoff §3.4; extend them.
- [ ] IF stamp-free cols + contamination floor + Brake notify upgrade (Ticket 8). **ADD:** `tests/` for `iso_genuine_notify_rate <= iso_genuine_fpr_floor` on inner-val; IF cannot train on G-test parquet.
- [ ] Isotonic renormalization + ECE on G-dev 44 (Ticket 9). **ADD:** test that calibrated probs sum to 1 after renormalize.
- [ ] Cluster bootstrap CI keys on G-test score JSON (Ticket 9). **ADD:** test that bootstrap resamples entities, not rows.
- [ ] Champion uses `sample_weight` / balanced weighting. **ADD:** test or assert in `fit_champion` path.

---

## Walkthrough language bans

Do not write comments, UI copy, or `.docx` / `TeamName.docx` claims that a repo poke contradicts. (Handoff §8 + `VALIDATION.md` §12.2.)

- [ ] **Nine loops** vs three HTTP handlers (`Docs/feedback-loop.md` vs `apps/api/routes/defend.py`). Say I, C (read), M; name the rest as roadmap.
- [ ] **Coverage `live_rule`** as 24 distinct injected behaviors. T14–T19 share `app_session`. Map is feature-name overlap, not fire-rate.
- [ ] **`POST /generate/population` with Atlas up** still trains on `DEFAULT_SIGNALS`, not 22 generate cards.
- [ ] **Invoice hard_flag + invoice AP** while train.parquet lacks beneficiary columns (true until Ticket 1 is green). After Ticket 1, do not call stamp AP “BEC detection.”
- [ ] **Loop M improves AP** on `n_customers=20` / `ap_equal_eps=0.05` without `not_comparable` / `n_pos`.
- [ ] **Five family models** — `champion.joblib` is one HGB.
- [ ] **Training from `injectors.py`** or implying it is ShadowRail.
- [ ] **PSI = live UPI** / “this is live UPI data.”
- [ ] **AuthGate 50–300 ms Mastercard SLA** / Decision Intelligence Pro latency.
- [ ] **`solved` from a metric bump** or Loop M.
- [ ] **Every T0x is simulated** — T06/T07/T20–T23 are `name_only`; canary (`inject/canary.py`) is not 24 engines.
- [ ] **Retrain after generating attacks from the same eval fold** quoted in the docx (43 as coach).
- [ ] **“99.9% accuracy”**, **“beats production”**, **“AUC of 0.99”**, **“we detect all 24 attacks”**, **“Cat 4 evasion API”** (`VALIDATION.md` §12.2).
- [ ] **AutoGluon / five models / Featuretools / GNN / CaseScore LLM on path** as the novelty story. Novelty is miss → Generate extra → retrain → new-seed G-test, plus HITL rules and Brake typology.
- [ ] **G-eval numbers in the headline slot.** Headline = G-test new `world_seed`.
- [ ] **Lab fraud rate = India rate.**
- [ ] **IF detects all 24 / closes T06/T07/Cat-4 named gaps** — IF is stamp-free weirdness → `notify` only.
- [ ] **IID bootstrap CI** presented without the cluster-resampling disclaimer.

---

## Ticket reminder (execution order — `defend-execution-ssot.md` §13.14)

1. Honesty floor (invoice `X`, unique in-degree, burst clone)  
2. `n_pos` / APP ablation copy on G-test JSON  
3. Nested protocol + frozen 43 (+ 44 G-dev)  
4. Volume for submission (Plan 08 full mix)  
5. Loop M polish (MUST; code exists)  
6. Loop T HITL (MUST)  
7. Optuna freeze (SHOULD; after T7 if time)  
8. Isolation Forest notify (SHOULD)  
9. Isotonic calibration + ECE (SHOULD)  
10. Cluster bootstrap CI + permutation importance (SHOULD)  

**Loop G** is not a ticket. Do not start Optuna, IF, or five estimators before Ticket 1.
