# AegisLoop Defend — agent continuation handoff

**Audience:** a coding agent that has not read the council chat.  
**Repo:** `/home/aarush_linux/projects/Mastercard`  
**Do not implement tickets from this file.** Index: [`README-defend.md`](README-defend.md). Code: [`defend-execution-ssot.md`](defend-execution-ssot.md). Tests: [`defend-test-tracker.md`](defend-test-tracker.md). Section 9 tickets 7–8 below (Loop G / optional T) are stale.  
**Verified:** 2026-08-28. Key paths listed below exist on disk. Seed YAML has **29** rows covering **T01–T24**. `v0_rules.yaml` has **9** live rules.

---

## 0. Locked council ruling (do not reopen)

**Win condition:** one closed loop you can demo; an honest coverage map; one fast GBDT + YAML rules + Brake; Loop M miss → retrain; nested validation; HITL rules; FN ≠ FP.

| Locked | Meaning |
|---|---|
| AuthGate | **One** multiclass `HistGradientBoostingClassifier`, `y = label_family`. Family AP is a **metric**. At most **one** OVR adapter later **if** a family is dead on G-test. **Not five live models.** |
| HPO | Optuna nested, **train-only**, freeze `models/features.json`. AutoGluon overnight **challenger only**, never hot path. |
| Forbidden live | AutoResearch, GNN live, Featuretools/DFS on events, CaseScore LLM on auth, auto-promote rules, auto-`solved` catalog |
| FN | → Generate / Loop M (blind spots). Harvest off **reported** G-test (use G-dev or same-run diagnostic). |
| FP | → calm-downs / extra AND (friction). **Separate inboxes.** |
| Headline metrics | G-test **new `world_seed`**. |
| Rules | v0 **9 YAML stay LIVE floor**. Drafts from Loop I + **mandatory** Loop T (≤5 drafts, ≤4 predicates, inner-val-only mining). Identify-shaped HITL promote. No auto-promote — every rule goes through HITL queue + FPR gate first. |
| Invoice | Payload flags are **not** in train `X` today. **Must fix** before invoice OVR/AP means anything. |
| Duplicate | `burst_velocity == fan_out_1h` in `packages/sim/features.py`. |
| Default Generate | `DEFAULT_SIGNALS` in `mix.py`, **not** Atlas cards, unless `vector_id` is passed. |
| Loops coded | **I**, **C** (read), **M**. Loop **G / R / T** not coded. |
| Demo size | Plan 08: `n_customers=2400`, `n_merchants=120`, `sim_days=90`. CI uses `n=20`. |

**Do not “helpfully” ship five pickled family models, AutoGluon on path, or nine working loops.** Architect’s earlier vote for five HGBs is **overruled**.

### Build order (architect, council-confirmed)

1. Honesty floor: invoice allowlist + unique fan-in counterparties 1h + coverage/APP ablation in artifacts  
2. Nested protocol + frozen G-test seed  
3. Volume for submission / walkthrough run  
4. Optuna freeze  
5. Loop M as the clickable loop (already exists — demo + chart; **do not claim Loop G**)  
6. Loop G knob search **only if M is green**  
7. Rule mining HITL if time  

### MUST / SHOULD / SKIP (council synthesis)

| Idea | Effort | Verdict |
|---|---|---|
| Coverage honesty + APP ablation in walkthrough / UI / score artifacts | S | **MUST** |
| Invoice columns in `X` + unique `fan_in` counterparties 1h | S | **MUST** |
| Nested protocol + G-test as the reported number | S | **MUST** |
| Cost-weighted $ at operating point + AuthGate p50/p99 (laptop, already partly in `fit.py`) | S | **MUST** |
| Loop M demo + before/after chart | M | **MUST** (code exists; polish + honest n_pos) |
| Bounded Optuna, freeze recipe | M | **SHOULD** |
| Loop I draft in the UI (API already coded) | S | **SHOULD** |
| ≤5 gated interaction features | S | **SHOULD** if tickets 1–5 green |
| Loop G knob search | M | **LATER** |
| Loop T + two-inbox HITL (FN mine → backtest → HITL queue → versioned YAML) | M | **MUST — Ticket 7 (NOT optional; promoted from LATER)** |
| One OVR adapter if a family is dead on G-test | S | **LATER / result-driven** |
| Five live models, AutoGluon path, GNN, Featuretools, auto-promote, CaseScore LLM | — | **SKIP** |

SSOT for code: [`02-defend-build.md`](02-defend-build.md) (Plan 12) for Defend; [`08-generate-world-build.md`](08-generate-world-build.md) for Generate; [`LOCKED.md`](../LOCKED.md) for planning spine. **Do not implement Defend from** `02-generate-defend-loop-lock.md` or from `feedback-loop.md` nine-loop prose.

---

## 1. Mission and problem-statement criteria

From [`MC_PS.md`](../../MC_PS.md): Mastercard Innovation Challenge @ GFF 2026 — **Identify, Generate, Defend** as one closed red-team / blue-team system. Submission: public GitHub repo, `TeamName.docx` walkthrough, working web prototype.

Judges score:

| Axis | PS wording | How Defend scores it (honest) |
|---|---|---|
| **Diversity of attacks identified** | Breadth and depth of GenAI-powered payment fraud | Identify census T01–T24 + coverage map with **named gaps**. Do **not** claim 24 detectors. Diversity is Atlas + four injectors / five fraud families. |
| **Fidelity of attacks in simulation** | Realistic distributions, behaviours, edge cases | Quiet world + injectors + PSI vs **this run’s priors** (`fidelity.py`). Sampler QA, **not** live UPI. APP **without** session flags must be reported. |
| **Detection efficacy** | Precision, recall, F1 / AUC; low FP on genuine | Lead with **PR-AUC / AP by `label_family`**, TPR@FPR 0.1/0.5/1%, `genuine_fp`, F1 secondary at the same op. `n_pos` on every family cell. Headline = G-test new seed. |
| **Novelty** | Overall solution | Closed loop: miss → Generate extra → retrain → G-test, plus HITL rules, Brake APP ≠ ATO ≠ mule. Novelty is **not** AutoGluon or five models. |
| **Real-world feasibility** | Live payments | Laptop in-process `predict_proba` p50/p99; rules + HGB + Brake; LLM **off** auth path; HITL; synthetic-only ethics. Do not claim Mastercard issuer SLA 50–300 ms. |

PS also asks detect, **flag**, **mitigate**. Rules flag; HGB scores; Brake maps to `allow | notify | step_up | hold | decline | mule_credit_restrict | case`.

---

## 2. System map (honest taper)

```
Identify (LangGraph HITL catalog)
    Scout → Curator → Extractor → Grounder → TierScorer → Corroborator → Librarian
    → proposed rows → HITL approve/reject/edit → open
         │
         │  (handshake: eligible cards; default Generate does NOT consume Atlas recipes)
         ▼
Generate (ShadowRail)
    quiet Poisson world → four injectors via apply_mix → causal FeatureComputer
    → PSI/fidelity → train.parquet + split.parquet + sidecar.json
         │
         ▼
Defend (no graph)
    9 YAML rules → one multiclass HGB (rule__ bits on X) → Brake
    Loop I drafts, Loop C coverage (read), Loop M miss→retrain
```

**Honest 24 → 4 engines / 5 families → 1 model + 9 rules:**

| Layer | Count | Reality |
|---|---|---|
| Taxonomy | 24 `TechniqueId` | Coverage cells. Seed **29** rows (duplicates on T13/T02/T11/T24). |
| `generate_mode=generate` | ~22 seed rows | `name_only`: T06, T07, one T19, T20–T23 (and high dual-use / Cat 4). |
| Injector engines | **4** | `graph_mule`, `identity_trajectory`, `app_session`, `doc_beneficiary` |
| `label_family` | **6** incl. normal | `normal \| mule \| identity_burst \| ato \| app_fraud \| invoice_fraud` |
| Live YAML | **9** | Coverage `live_rule` is **feature-name overlap**, not fire-rate |
| Champion | **1** multiclass HGB | `ap_by_family` is OVR AP from **one** head |

Family ← injector (`packages/sim/runner.py` `_families_for_spec`): `graph_mule→mule`, `app_session→app_fraud`, `doc_beneficiary→invoice_fraud`, `identity_trajectory` + T12 → `ato`, else → `identity_burst`. T08/T09/T10 generate cards **collapse to `identity_burst`**, not a KYC detector.

Live scoring order (Plan 12): **rules → AuthGate → Brake**. LLM may polish analyst text from reason codes. Never between 1 and 2.

---

## 3. Verified repo state (file paths)

All of these existed when this handoff was written.

### 3.1 Identify

| Piece | Path |
|---|---|
| Graph | `packages/agents/identify_graph.py` — linear LangGraph, **no** sim nodes |
| Nodes | `packages/agents/nodes/{scout,curator,extractor,grounder_node,tier_scorer,corroborator,librarian}.py` |
| HITL payload | `packages/agents/librarian_db.py` `hitl_payload_for_spec` |
| HITL HTTP | `apps/api/routes/identify.py` — `POST /identify/run`, `GET /identify/hitl`, `POST /identify/approve/{vector_id}`, `/reject`, `/reject-unsafe`, `/decision/{vector_id}` |
| Status enum | `packages/catalog/status.py` — `proposed \| rejected \| rejected_unsafe \| open \| generating \| defending \| solved` |
| HITL verbs | approve → `open`; reject; reject_unsafe; edit (`spec_patch`) |
| Seed | `data/catalog/seed.yaml` — **29** `AttackSpec` rows, T01–T24 |
| Loader / schema | `packages/catalog/loader.py`, `packages/catalog/models.py`, `packages/catalog/schemas.py` |
| Mount | `apps/api/main.py` |

Identify **never** calls Generate or Defend. `IDENTIFY_MAX_HITL` caps staging (`packages/agents/nodes/librarian.py`). **Nothing in fit/score/Loop M writes `solved`.** Loop M returns `catalog_solved: False`. `POST /defend/miss/{vector_id}` only forces status `open`.

### 3.2 Generate

| Piece | Path |
|---|---|
| Live runner | `packages/sim/runner.py` — `run_population` default `n_customers=2400`, `n_merchants=120`, `sim_days=90`, `world_seed=42` |
| Mix | `packages/sim/inject/mix.py` — `DEFAULT_SIGNALS`, `DEFAULT_SHARES`, `apply_mix(..., families=, signals=)` |
| Four engines | `packages/sim/inject/graph_mule.py` (funnel/cashout/smurf/hop/dust), `identity.py`, `app_session.py`, `doc_beneficiary.py` |
| Canary | `packages/sim/inject/canary.py` — FinCEN chain; **not** the train champion path |
| Jitter | `packages/sim/inject/jitter.py` — ±50% unless `pin` |
| Quiet world | `packages/sim/world.py` — `rebuild_features()` → `replay_features` (this **wipes** payload flags from `features_auth`) |
| Causal features | `packages/sim/features.py` — `G(t−)` deques; 1h + 30d amounts |
| Export | `packages/sim/export.py` — `TRAIN_ALLOWLIST`, `TRAIN_DENYLIST`, `SPLIT_COLUMNS` |
| PSI | `packages/sim/fidelity.py` — PSI amount ≤0.25, hour ≤0.35, fraud rate 0.5–3.5% when all families, mule fan-in median >5 |
| HTTP | `apps/api/routes/generate.py` — `/population`, `/canary`, `/calibrate-world` |
| **Do not train from** | `packages/sim/injectors.py` — stub; `label_family` can be `T13` |
| Ablation smoke | `packages/sim/ablation.py` — **not** the champion |

**Default population:** `run_population(db=None, vector_id=None)` uses all five fraud families and `DEFAULT_SIGNALS`. `db` without `vector_id` only checks generate-eligible Atlas is non-empty, then still uses default mix. `vector_id` set → one family + that spec’s `simulatable_signals` into **one** mix key.

CI / Makefile: `FAST_CUSTOMERS = 20`; `make generate-validate` uses 16 customers; `make generate-scale` is the Plan 08 size pin (currently T13-filtered). **Walkthrough metrics must use Plan 08-sized full mix, not CI n=20.**

### 3.3 Defend

| Piece | Path |
|---|---|
| Fit | `packages/eval/fit.py` — `fit_champion`, `score_run`, APP ablation, AuthGate bench, JSON denylist |
| Split | `packages/eval/split.py` — time 2/3 + entity holdout |
| Loop M | `packages/eval/loop_m.py` — extra family on train only, G-test seed ≠ train |
| Brake | `packages/eval/brake.py` |
| Recipe | `models/features.json` |
| Rules YAML | `data/rules/v0_rules.yaml` — 9 live |
| Rule engine | `packages/policy/rules.py` — row predicates; `EXTRA_ROW_FIELDS` invoice booleans allowed on **row** eval, **not** currently on parquet |
| Loop I | `packages/policy/loop_i.py` — `draft_rule_from_spec` |
| Loop C | `packages/policy/coverage.py` — `build_coverage_map` |
| HTTP | `apps/api/routes/defend.py` — coverage-map, scout-topics, rules/v0, loop-i/draft, miss, fit, score, loop-m |

No `packages/eval/loop_g.py`. No Optuna. No `defend_graph`. `pyproject.toml` ML extra is scikit-learn.

### 3.4 Tests to extend (do not delete; add)

| Test | Why |
|---|---|
| `tests/test_sim_export.py` | Allowlist, denylist, APP flags only on APP rows, invoice family present |
| `tests/test_sim_inject.py` | Injector labels, invoice payload |
| `tests/test_eval_split.py` | Leak assertions, time+entity |
| `tests/test_eval_fit.py` | Family y, ablation keys, no denylist in X |
| `tests/test_eval_loop_m.py` | New seed, extras not on G-test, `solved` false |
| `tests/test_eval_rules_brake.py` | Row predicates, APP not decline, mule restrict |
| `tests/test_defend_api.py` | Fit/score HTTP, denylist absent in JSON |
| `tests/test_defend_handoff.py` | Coverage 24 cells |
| `tests/test_generate_api.py` / `test_generate_handoff.py` | Population HTTP honesty |

### 3.5 Docs that overclaim (do not copy into comments or the walkthrough)

| Doc | Overclaim vs code |
|---|---|
| `Docs/feedback-loop.md` | **Nine loops** (I, R, T, M, A, F, C, H, G) + AutoML LightGBM + LLM on the live order. **Coded:** I, C read, M. Live estimator is HGB. |
| `Docs/defense_architecture.md` | AutoML/FLAML/LightGBM, LLM case extractor on path, ~12–18 rules, “all loops” |
| `Docs/ARCHITECTURE.md` | LoopGovernor, Canary Vault, LangGraph defend story |
| `Docs/V1_MASTERPLAN.md` | Forked; superseded by `LOCKED.md` |
| `Docs/plans/02-generate-defend-loop-lock.md` | Architecture names only; **not** Defend SSOT |

Plan 12 already says v1 loops: I/C exist, M must work once; R/T/A/G/F/H named or recorded.

---

## 4. Data contracts — FN → Generate

Loop M **already** calls `run_population(..., families=frozenset({miss_family}), world_seed=train_seed+10007)`. It does **not** load sidecar knobs. That is “more of the same injector,” not Loop G.

### 4.1 What Generate can consume

```text
run_population(
    db=None,                    # Loop M: no Atlas
    run_id=...,
    world_seed=<new int>,       # never the reported G-test seed
    n_customers, n_merchants, sim_days, pin,  # copy train sidecar scale
    families=frozenset({label_family}),       # one of FRAUD_FAMILIES
    runs_dir=...,
)
```

`apply_mix(..., families, signals, target_rate, pin)`:

- Mix budget: lab fraud **1–3%** (`fraud_row_target`). Shares: mule 0.40, identity_burst 0.25, ato 0.05, app_fraud 0.20, invoice_fraud 0.10.
- Family-filtered run sets `require_mix_rate=False` in fidelity.
- Extra row cap: `models/features.json` `loop_m.extra_row_cap_frac` default **0.15** of original train length.

**Sidecar (`data/runs/<run_id>/sidecar.json`):** `world_seed`, `n_customers`, `n_merchants`, `sim_days`, `pin`, `knobs_used`, optional `vector_id` / `technique_id`. Legal for Generate. **Forbidden in train X and Defend HTTP JSON.**

**`knobs_used` keys engines honor** (denylist for X):

| Mix key | Fields |
|---|---|
| `graph_mule` | `fan_in_1h` (funnel inbound, min 16), `fan_out_ttl_hours`, `smurf_cap_ratio`, `mule_account_age_days` |
| `identity_burst` / `ato` | `seasoning_days` (clamped to sim_days−14), `seasoning_txn_count`, `device_hash_shift` (ato), liveness/doc on **onboarding rows only** |
| `app_session` | `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`, `new_payee` |
| invoice | **No mix-signal blob.** Count = `alloc["invoice_fraud"]`. Payload flags always true in engine. Catalog `DocBeneficiarySignals` unused by `inject_invoices`. |

Fidelity gate (`packages/sim/fidelity.py`): PSI amount/hour vs this run’s priors; fraud-rate band when all families; mule `fan_in_1h` median > 5; independent recompute of `fan_in_1h`.

Loop M extras: ids `evt-lm-*`, timestamps shifted to train calendar `t0`, `force_train_event_ids` so they stay in train. G-test is a **new population** `world_seed=gtest_seed` (default 43), scored with `score_run(..., all_rows=True)`. Extra ids must be disjoint from G-test `event_id`s.

### 4.2 What Generate cannot consume

- Exact FN row vectors (“replay this payment”)
- `technique_id` as a mix key (families only)
- New AttackSpecs from miss clusters (Identify Librarian + HITL only)
- Scout topic strings auto-running Identify (`GET /defend/scout-topics` is hints only)
- `POST /defend/miss/{vector_id}` as a generate trigger (status handshake only)
- Denylist columns as features: `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, `transcripts`, `is_authorized_push`, `economic_class`, `label_class`, `gstin`, `payload`

### 4.3 Harvest vs headline (leak trap)

You must not mine rules, tune thresholds, or generate extras from the fold you quote in the walkthrough.

| Slice | Use |
|---|---|
| Inner val | Last chunk of **train** calendar (nested). HPO + operating-point threshold. |
| Same-run eval | Diagnostic / FN harvest **or** use a third seed **G-dev**. |
| **G-test** | New `world_seed` (lock **43** for reported; optionally freeze **44** never-touch). Headline AP, genuine FPR, Loop M after. |

Loop M currently compares before/after on G-test — good. Do **not** harvest FN from that same G-test to generate extras for a second Loop M you then report on the same G-test.

---

## 5. Validation protocol (copy-paste for implementer)

Keep existing `assign_folds`: sort by `event_ts`, `event_id`; first **2/3** of **this run’s** calendar = train candidate; last 1/3 = eval; **plus** hold out mule payees (`VID-SIM-U-*`, `VID-SIM-APP-*`, `VID-SIM-CHAIN-*`) and a fraction of `VID-SIM-C-*`. Protocol string today: `time_cut_2_3_plus_entity_holdout`. Never `train_test_split(shuffle=True)` as the published number. Split columns never in X (`assert_no_x_leak`).

**Add nested inner (ticket 2):**

1. After outer train fold is assigned, take the **last 20% of train calendar** (or last 1/5 of train rows by time) as **inner val**. Remainder = **inner fit**.
2. Optuna / threshold search **only** on inner fit → score inner val. Genuine-FPR floor from recipe.
3. Refit champion on **full outer train** with frozen params.
4. Same-run outer eval = diagnostic only (log it, do not lead the slide).
5. Generate G-test population: **same** `n_customers`, `n_merchants`, `sim_days`, `pin`, **`world_seed=43`**. Persist run_id. Score with frozen champion, `all_rows=True` or full population protocol `g_test_full_population`.
6. Loop M extras: train copy only; never append to G-test parquet.
7. APP ablation: report AP **with** vs **without** `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`. If `app_metric_died_without_synthetic_flags`, **document**. Do not glue flags onto genuine rows.
8. Seeds: train world **42**, G-test **43**, extra Loop M `42+10007`. If you add G-dev, use **44** and do not shop it.

**Metrics table (every family cell):**

| Field | Notes |
|---|---|
| `ap_by_family[fam]` | OVR AP from multiclass scores |
| `n_pos[fam]` | **Must add** — NaN AP without n_pos is a lie |
| `tpr_at_fpr` | 0.001, 0.005, 0.01 binary fraud vs normal |
| `genuine_fp` | FPR on gold `label_family==normal` |
| `f1_at_op` | Secondary, same threshold as TPR@1% FPR (recipe `operating_point_fpr`) |
| `app_ablation` | with / without four flags |
| `authgate_ms` | p50/p99, batch seconds 1k; hang 120s |
| `mule_entity_recall` | gold mule payee caught on ≥1 inbound |
| cost table (ticket) | miss $ vs decline vs APP hold at op — lab units, not India prevalence |

`y` is never `T01`…`T24`. Cat 4 rows must not appear in G-test.

---

## 6. Feature work

### 6.1 Invoice flags onto allowlist (first blocker — verified)

**Today:** `inject/doc_beneficiary.py` writes `payload`: `beneficiary_changed`, `gstin_checksum_ok`, `gstin`, `lookalike_domain_flag`. `world.rebuild_features` → `replay_features` rebuilds `features_auth` from graph/session only and **does not copy payload**. `export.train_rows` never reads those booleans. YAML `invoice-beneficiary-swap` therefore **cannot fire** on champion X. `EXTRA_ROW_FIELDS` in `rules.py` is a dead letter unless the row dict has those keys.

**Do:**

1. In `replay_features` / `snapshot_and_apply` (or immediately after replay): copy **booleans** from existing `ev["payload"]` at **t−** (the event being scored) into `features_auth`: `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag`. Default false on non-invoice rows. These are causal: they are on the payment envelope at auth, like APP flags.
2. Add those three names to `TRAIN_ALLOWLIST` and `train_rows`.
3. **Never** export `gstin` string, lookalike party id, or raw `payload`.
4. Keep `payload` on `TRAIN_DENYLIST`.
5. Rules evaluator already allows `EXTRA_ROW_FIELDS`; `_attach_rule_bits` will then light `rule__invoice-beneficiary-swap` on invoice rows.

**Must not:** identity-leak GSTIN as a categorical; train on checksum-fail amateur cases as the interesting BEC case (engine always checksum-ok + beneficiary changed).

### 6.2 Unique in-degree 1h (graph-lite)

**Today:** `fan_in_1h = len(payee_acc.inbound_ts)` — event count, not unique senders. `burst_velocity = float(fan_out_1h)` — duplicate.

**Do:** add `fan_in_unique_payers_1h` (unique payer ids in the last hour on the **payee**, past edges only). Keep `fan_in_1h` as event count (mule funnel still uses volume). Prefer using the unique column in rules that meant “many different senders.” Optionally stop writing `burst_velocity` as a clone: either drop from allowlist (breaking change — update YAML `seasoning-burst` to `fan_out_1h` or unique out) **or** redefine `burst_velocity` as a **different** causal quantity (e.g. outbound unique payees 1h). Do not keep two identical columns.

Windows remain O(n): extend `AccountRuntime` with a deque of `(ts, counterparty_id)`.

### 6.3 Optional ≤5 gated interactions

Only after inner-val lift vs base allowlist. Products of **allowlisted numerics** (e.g. `fan_in_1h * account_age_days`). Never Featuretools on the event log. Never denylist fields. Never APP-flag interactions that Generate always sets true on APP rows (that is the cheat the ablation exists to expose).

### 6.4 Still forbidden on X

Everything in `TRAIN_DENYLIST`; `liveness_score` / `doc_consistency` copied onto every payment (onboarding-only in ledger); `is_authorized_push`; embeddings.

---

## 7. Rules HITL shape (copy Identify verbs)

Identify pattern (`apps/api/routes/identify.py`):

- Queue: `GET /identify/hitl` lists `status=proposed`.
- Payload: `hitl_payload_for_spec` — field_diff vs nearest, badges, `generate_mode`.
- Actions: `approve | reject | reject_unsafe | edit`.
- Approve is the only path to `open`. No auto-on.

**Copy that for rule drafts:**

| Inbox | Source | Typical patch |
|---|---|---|
| FN / recall | Loop I from card; Loop T on **G-dev 44** misses | New hard_flag / nudge |
| FP / friction | Genuine holdout loud rules | Extra AND or calm-down |

v0 9 rules stay `status: live`. New YAML rows `status: draft` until HITL promote. **Forbidden as rule inputs** (`FORBIDDEN_RULE_FIELDS` in `rules.py`): `smurf_cap_ratio`, `seasoning_days`, `seasoning_txn_count`, `fan_out_ttl_hours`, `mule_account_age_days`, `gstin`, `is_authorized_push`, `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `economic_class`, `label_class`, `world_seed`, `transcripts`, `payload`, `persona_type`.

**Promotion backtest (same as Plan 12 / feedback-loop §6, but implement as tests, not theater):**

1. Evaluate candidate on genuine holdout (train inner val or frozen G-dev genuine rows). If FPR / alert volume blows a frozen epsilon → reject or convert to nudge.
2. Evaluate on frozen fakes **not** used to mine the rule (G-test or G-dev).
3. Human click promote (demo may auto-click **once**, labeled theater).
4. Version the YAML; keep previous file.
5. Do not mix APP and ATO in one `applies_to`.
6. Do not auto-set catalog `solved`.

Loop I templates already: APP call+paste+new payee; mule `fan_in_1h`; invoice beneficiary+checksum. Named gaps hardcoded T06, T07, T20–T23. Drafts are **not** written to `v0_rules.yaml` today — API returns a dict.

Loop T (MUST): ≤5 drafts, ≤4 predicates, **G-dev 44** trees. No generator-id conditions.

---

## 8. Judge-fake list (architect §7)

Do not write comments, UI copy, or walkthrough claims that a repo poke contradicts.

1. **Nine loops in docs vs three HTTP handlers** (`feedback-loop.md` vs `defend.py`).
2. **Coverage `live_rule` for techniques never injected as distinct behaviors** (T14–T19 share `app_session`). Map is feature-name overlap, not 24 detectors.
3. **`POST /generate/population` with Atlas up** still trains on `DEFAULT_SIGNALS`, not 22 generate cards.
4. **Invoice hard_flag in YAML** and `invoice_fraud` AP while train.parquet has no beneficiary columns (true until ticket 1).
5. **Loop M “improves AP”** on `n_customers=20` with `ap_equal_eps=0.05` and `not_comparable`.
6. **champion.joblib is one model** — do not say five family models in the walkthrough.
7. **`injectors.py` stub** still in tree with `label_family: T13`. Do not train from it; do not delete without checking imports; do not revive it.
8. **PSI vs own priors** sold as live UPI fidelity. It is sampler QA.
9. **AuthGate 50–300 ms Mastercard SLA** — hang guard is **120s / 1k rows**; comments already say laptop in-process.
10. **`solved` in the status enum** with no writer except a human; Loop M will not set it.
11. **Claiming every T0x is simulated** — T06/T07/T20–T23 are `name_only`. Canary is real (`inject/canary.py`); it is not 24 engines.
12. Retrain after generating attacks from the **same eval fold** quoted in the docx.

---

## 9. Concrete next tickets (sequence)

First ticket **is** the true first blocker after path verification: invoice flags are generated but not in X; unique in-degree does not exist; `burst_velocity` is a clone.

### Ticket 1 — Honesty floor: invoice X + unique in-degree 1h

**Files:** `packages/sim/features.py`, `packages/sim/world.py` (replay), `packages/sim/export.py`, `packages/policy/rules.py` (allowlist if needed), `data/rules/v0_rules.yaml` (if `burst_velocity` redefined), `tests/test_sim_export.py`, `tests/test_sim_inject.py`, `tests/test_eval_rules_brake.py`, `tests/test_eval_fit.py`.

**Do:**

- Copy invoice booleans from payload through rebuild into `features_auth` and `TRAIN_ALLOWLIST`.
- Add `fan_in_unique_payers_1h` (causal, O(n)).
- Deduplicate `burst_velocity` (drop or redefine). Update `seasoning-burst` if needed.
- Do not add GSTIN string.

**Acceptance tests:**

- Invoice rows: `beneficiary_changed` / `gstin_checksum_ok` true on parquet; genuine rows false.
- `gstin` not in train columns; `payload` absent.
- After fit, `rule__invoice-beneficiary-swap` can be 1 on an invoice fixture row.
- Unique in-degree: two inbound from **same** payer in 1h → unique=1, `fan_in_1h`=2 (or equivalent fixture).
- `burst_velocity` is not equal to `fan_out_1h` unless you documented a temporary alias and removed it from X.

**Done when:** `pytest` those files green; small population parquet has invoice columns; champion X includes them; allowlist extra columns still pass `assert_train_schema`.

### Ticket 2 — Coverage / APP ablation honesty in artifacts

**Files:** `packages/eval/fit.py` (add `n_pos` per family; keep ablation), `packages/policy/coverage.py` (optional `coverage_status` notes in JSON), walkthrough later — **not** fake fire-rates. Score JSON must include ablation + `n_pos`.

**Acceptance:** `ap_by_family` keys each have `n_pos`; APP ablation keys present on `/defend/score`; coverage map still 24 cells; comments/docs say feature-name overlap.

**Done when:** metrics JSON from `fit_champion` contains `n_pos` and ablation; no walkthrough sentence claiming 24 live rules without named_gap.

### Ticket 3 — Nested protocol + frozen G-test seed

**Files:** `packages/eval/split.py`, `packages/eval/fit.py`, `packages/eval/loop_m.py` (do not change G-test isolation), `tests/test_eval_split.py`, `tests/test_eval_fit.py`.

**Do:** inner val from train calendar; threshold/HPO only there; freeze G-test seed 43; persist protocol string; same-run eval labeled diagnostic.

**Acceptance:** test that HPO cannot read G-test parquet; G-test `world_seed != train`; `n_pos` on G-test families.

**Done when:** recipe/docs state seeds 42/43; tests fail if shuffle split is used as reported protocol.

### Ticket 4 — Volume for submission run

**Files:** `Makefile` (optional `defend-scale` / document `generate-scale` **without** T13-only pin for the champion world), scripts or README command. Not CI.

**Do:** one documented command: full mix, 2400×120×90, seed 42, then G-test 43 at same scale. Store run_ids. Do not check 50k-row artifacts into git (`data/runs/` gitignored).

**Acceptance:** walkthrough run_id recorded; CI still n=20.

**Done when:** a human can reproduce headline metrics from that command without using Loop M’s 20-customer fixture.

### Ticket 5 — Optuna freeze (SHOULD; after 1–4)

**Files:** `pyproject.toml` optional extra, `packages/eval/fit.py`, `models/features.json`, `models/<run_id>/best_params.json`, tests that study uses inner val only.

**Bounds:** ~30–50 trials; `max_depth`, `learning_rate`, `max_iter`; objective PR-AUC or min-family AP with genuine-FPR floor. Freeze into `features.json`. **No AutoGluon on path.**

**Done when:** refit with frozen params is deterministic; study pickle is not required to score.

### Ticket 6 — Loop M as the clickable loop

**Files:** already `loop_m.py`, `POST /defend/loop-m`. UI/walkthrough/chart later (Plan 11). **Do not claim Loop G.**

**Do:** demo script: train 42 → score G-test 43 → pick miss family with support → `run_loop_m` → chart AP before/after + genuine FPR + `n_pos`. Report `regressed` / `not_comparable` honestly.

**Acceptance:** existing `tests/test_eval_loop_m.py` stay green; extras not on G-test; `catalog_solved is False`.

**Done when:** one HTTP (or CLI) path produces the before/after JSON on a **Plan 08-sized** run if possible; CI remains small.

### Ticket 7 — Loop G knob search — **DO NOT BUILD**

Deferred. Not in this sprint. Implement Loop T from `defend-execution-ssot.md` instead.

### Ticket 8 — Rule mining HITL — **see execution SSOT Ticket 7 (MUST)**

Loop I already drafts. Loop T is mandatory. Two inboxes. Promote like Identify. v0 stays live. ≤5 drafts. Full spec: `Docs/plans/defend-execution-ssot.md` §7 Ticket 7.

---

## 10. Non-goals and kill triggers

| If this happens | Do not |
|---|---|
| Loop M `not_comparable` / noisy on n=20 | Fake nine loops; claim G-test win without n_pos |
| APP AP dies without session flags | Glue flags onto genuine traffic; hide ablation |
| Invoice AP still noise after flags in X | Invent GSTIN identity features; claim invoice OVR |
| Clock dying | Skip Loop G, Optuna, five models; keep honesty floor + Loop M chart |
| User asks for five live models | Translate (section 12); do not implement |
| Featuretools / GNN / CaseScore LLM | Refuse; cite this section |
| Auto-promote rules or auto-`solved` | Disallowed |
| Train on eval / harvest FN from reported G-test | Disallowed |
| LangGraph `defend_graph`, Redis, DuckDB, Cat 4 public API | Plan 12 non-goals |
| `packages/sim/injectors.py` as train source | Forbidden |
| Claiming live UPI / India prevalence / beat production | Forbidden |

Kill trigger: **if Loop M is not a clickable, honest before/after, do not spend remaining time on Loop G or nine-loop docs.** Ship coverage honesty + invoice X + G-test table.

---

## 11. Winning narrative (PM — walkthrough later)

Atlas maps **24 techniques** with named gaps for what payment-time rails cannot see. ShadowRail builds a quiet UPI-like world and injects **five economic classes** through **four engines**, with causal features and a fidelity gate against our own priors — not a claim that this is NPCI production data. AuthGate is **one** fast histogram GBDT plus **nine** explainable YAML rules; Brake holds APP, declines ATO, and credit-restricts mule payees instead of treating fraud as a single decline. When blue misses a family, Generate adds a capped extra mix on **train only**, we refit the **frozen** recipe, and we only call it a win if **average precision on a new world seed** does not collapse and **genuine false positives** do not rise. Coverage is a census, not 24 detectors. Session flags are synthetic; we show APP with and without them. Invoice tells are on the payment at t− once they are in X, not GSTIN identity. That is Decision Intelligence you can click, not an AutoML bake-off.

---

## 12. How to talk to the user (translate peak asks)

The user asked for peak Defend: five models, AutoML, auto FE, FN loop, self-learning rules. Translate; do not secretly implement the over-scope.

| User ask | What we actually build |
|---|---|
| Five live family models | One multiclass HGB; **family AP as metric**; at most one OVR adapter if a family is dead on G-test |
| AutoML / AutoGluon / FLAML | Nested **Optuna** on train, freeze `features.json`; AutoGluon overnight **write-up challenger only** |
| Auto feature engineering / DFS | Invoice booleans + unique in-degree 1h; optional ≤5 gated interactions; **no Featuretools** |
| FN loop / self-learning Generate | **Loop M** (exists): miss family extra, new seed G-test. Loop G knobs **later** |
| Self-learning rules | v0 live floor; Loop I drafts; Loop T MUST; **HITL promote**; never auto-on |
| Nine feedback loops | Demo **I + C + M**. Name the rest as roadmap. Do not fake handlers |
| Peak novelty | Closed loop + honest coverage + Brake typology + nested G-test |
| Live 50–300 ms AuthGate | Measured laptop p50/p99; not an issuer SLA |

If the user repeats “five models,” answer: council locked one multiclass head; implementing five pickles now fights the walkthrough and the Brake table we already have.

---

## 13. Quick commands (when implementing)

```bash
# CI-sized (not headline)
pytest tests/test_sim_export.py tests/test_eval_fit.py tests/test_eval_loop_m.py tests/test_eval_rules_brake.py tests/test_eval_split.py -q

# Offline suite
pytest tests/ -q -m "not live_llm and not live_identify"

# Coverage 24
make defend-validate

# Plan 08 scale Generate (T13 pin today — champion world should be full mix, not this pin)
make generate-scale
```

Do not commit `data/runs/` or `models/*/champion.joblib` secrets. Freeze recipe JSON is source-controlled (`models/features.json`).

---

## 14. First action for the next agent

Implement **Ticket 1** only. Do not start Optuna, Loop G, or five estimators. Do not edit `feedback-loop.md` to pretend loops exist unless you are adding a one-line “v1 coded: I, C, M” honesty note (optional, not required for Ticket 1).

When Ticket 1 is green, continue Ticket 2 → 3 → 4 before any model shopping.
