# Plan 12 — Defend build (locked SSOT)

**Filename:** `02-defend-build.md` (Defend takes the Plan 02 *slot* the way Plan 08 took Generate.)  
**Status:** LOCKED — implement Defend from this file, not from [`02-generate-defend-loop-lock.md`](02-generate-defend-loop-lock.md)  
**Depends on:** Plan 08 Generate **done** (A–G sign-off), Plan 01 catalog, Plan 00 naming/status, MC_PS, HACKATHON_RESEARCH  
**Does not reopen:** Identify Job A, WorldCalibrator live NPCI, Cat 4 public API, LLM-on-authorization, AutoGluon as live scorer, GNN live scorer, SDV/CTGAN

**Product one-liner:** Generate already writes a quiet UPI-like world plus labeled injectors to **train Parquet + sidecar**. Defend scores **pay-time columns only**, **flags** with rules that fire on **row values**, **mitigates** with Brake (APP hold ≠ ATO decline ≠ mule credit restrict), reports **PR-AUC / TPR@FPR / genuine FP** honestly (including APP **without** synthetic session flags), and runs **Loop M once** (miss → retrain → G-test better, genuine FPR not worse).

**Do not start coding until this file is the accepted Defend SSOT (it is).** Implement in phases 0 then A–E below. Each phase’s tests must pass before the next.

---

## Why Plan 02-as-written is not the build

[`02-generate-defend-loop-lock.md`](02-generate-defend-loop-lock.md) stays the **architecture lock** for: no LLM on the hot path; APP ≠ stolen-card; PR-AUC not accuracy; causal `G(t−)`; Cat 4 **offline**; HoldoutVault *protocol*; nine-loop *names*; `solved` *meaning* after real arms-race.

It is **not** the implementation SSOT. Generate (Plan 08) already overrode its ledger/injectors/population/canary/PSI. Following leftover Plan 02 Generate sentences or training on today’s `train.parquet` as if it had timestamps and party ids would be a **leak or a broken split**. Following nine loops + FLAML + AutoGluon + DuckDB + LangGraph `defend_graph` + unverified SAML-D in one sprint would fail MC_PS **detection efficacy** and **feasibility**.

This file **wins** for Defend v1 the same way 08 won for Generate fidelity.

---

## Authority: when this file beats Plans 02 / 03 / 08-export

Plans 00–03 stay SSOT for **Identify, safety, naming, Cat 4 offline, AuthGate later as a *story***. Plan 08 stays SSOT for **the world and train allowlist/denylist**. For **Defend v1**, this file wins:

| This file | Beats | Keep |
|-----------|--------|------|
| Consume Plan 08 Parquet + a **split artifact** (`event_ts`, party ids) that is **not** model input | Plan 02 “DuckDB + `attack_id` on every auth row”; current export with no clock | Allowlist/denylist **unchanged** for `X`; extra columns only in `split.parquet` / eval join |
| `y = label_family` (multiclass or one-vs-rest); Brake uses **predicted** family | Plan 02 `label_class` as train target; binary `is_fraud` only | `economic_class` stays sidecar/metrics — **never** in `X` |
| One GBDT (sklearn HGB **or** LightGBM), `average_precision`, `scale_pos_weight` from **this run’s** base rate | Plan 02 FLAML + overnight AutoGluon as required | AutoGluon remains optional overnight **challenger**, never demo hot path |
| G-test = **new `world_seed`** same engine + entity holdout | Plan 02 “family B frozen engine” as a second simulator | Forbidden: random 80/20 as the **reported** number; Cat 4 rows in G-test |
| Rules evaluate **numeric/boolean thresholds on rows** | Current `match_rules_to_features` key-presence; YAML knobs as `when` keys | Loop I/C coverage map stays; v0 YAML rewritten to allowlist fields |
| AuthGate = in-process score + **ms/row**; Brake enum persisted | Plan 02 50–300 ms issuer envelope as a **claim** without a bench | Latency **measured** on laptop; do not claim Mastercard production SLA |
| v1 loops: **I/C exist**; **M must work once**; R/T/A/G/F/H named or recorded | Plan 02 nine loops as v1 scope | Cat 4 public API still forbidden |
| Phase 0 Generate HTTP + `fidelity.pass` + honest live gates | Silent handoff (`event_count>1` only) | Plan 08 injectors/world **untouched** except export **add** split file |

**MC_PS:** detect, **flag**, **mitigate**; precision/recall/F1/AUC; **low FP on genuine**; closed loop. Dashboard **leads** with PR-AUC by family and TPR at FPR 0.1/0.5/1%; F1 at the chosen operating point is **secondary** so judges who look for F1 still see it. Never lead with accuracy on a balanced toy mix.

---

## What already exists (do not rebuild)

| Piece | Path | Role in v1 |
|-------|------|------------|
| Quiet world + injectors + mix | `packages/sim/` | Training ground |
| Train allowlist/denylist | `packages/sim/export.py` | Model `X` + `y` |
| APP ablation smoke | `packages/sim/ablation.py`, `Docs/generate_app_ablation.md` | Honest APP metric; **not** the champion |
| Population / canary / calibrate HTTP | `apps/api/routes/generate.py` | Need **TestClient** tests (Phase 0) |
| Coverage + Loop I + miss | `packages/policy/*`, `apps/api/routes/defend.py` | Keep; miss path later feeds Loop M |
| v0 YAML | `data/rules/v0_rules.yaml` | **Rewrite conditions** to computed fields (Phase B) |
| sklearn in `dev` extra | `pyproject.toml` | Allowed champion |

**Do not** train from `packages/sim/injectors.py` stub. Live path is `runner.py`. Stub may stay until nothing imports it; do not revive it.

---

## Lock 1 — Artifacts: train vs split vs decision

Three files per `run_id` under `data/runs/<run_id>/` (`data/runs/` gitignored):

| File | Columns | Who reads |
|------|---------|-----------|
| `train.parquet` | Plan 08 **allowlist only** (includes `label_family`) | Champion `X` = all except `label_family`; `y` = `label_family` |
| `split.parquet` | `event_id`, `event_ts`, `payer`, `payee`, `amount_minor`, `label_family` | Time cut, entity holdout, mule-account recall, Brake eval. **Never** concatenated into `X` |
| `sidecar.json` | knobs, `technique_id`, `seasoning_*`, fidelity, `world_seed` | Humans, Loop M config — **not** the model |

**Denylist stays Plan 08:** `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `is_authorized_push`, `economic_class`, `label_class`, GSTIN, transcripts, `world_seed` as a **feature**.

**Export change (minimal):** `export_run` also writes `split.parquet`. Do not add `event_ts` to `train.parquet` (keeps Plan 08 schema tests). Ablation may join on index/`event_id` from split.

**Split protocol (locked):**

1. Sort by `event_ts`, `event_id`.
2. Time cut: first **2/3** calendar of **that run** = train; last **1/3** = eval **candidate**.
3. **Plus** hold out a disjoint set of mule payee ids (`VID-SIM-U-*`, `VID-SIM-APP-*`, `VID-SIM-CHAIN-*`) and a fraction of customer ids so the model cannot memorize entities. Those rows are eval-only even if they fall in the first 2/3.
4. **G-test (family B v1):** generate a **second** population with `world_seed != train seed` (e.g. 42 vs 43), same `n_*` / `sim_days`. Report transfer there. Same engine, new seed — not a second product.

---

## Lock 2 — Model, labels, metrics

**Champion (one recipe, freeze in `models/features.json`):**

- Estimator: `HistGradientBoostingClassifier` (already in ablation) **or** LightGBM if added as one extra. Pick **one** in Phase C and do not swap for leaderboard shopping.
- Objective: **average precision** (PR-AUC), not accuracy.
- Imbalance: `scale_pos_weight` / class weight from **this run’s** fraud rate (lab ~0.5–3.5%, sign-off bench ~0.77%). No SMOTE/CTGAN.
- **Multiclass** `label_family` **or** one-vs-rest with a shared feature matrix. Binary `is_fraud` may exist as a **derived** score for operating-point charts, not as the only head if Brake cannot tell APP from ATO.
- Inputs: Plan 08 allowlist minus `label_family`. Optional **rule-hit bits** computed at train time from Phase B rules (same functions as serve). No embeddings. No `liveness_score` copied onto every payment (onboarding-only in ledger; already NULL on later rows).

**Reported metrics (dashboard / `.docx` order):**

1. PR-AUC / AP **by** `label_family` (at least `app_fraud`, `mule`, `ato`, `invoice_fraud`; `identity_burst` if present).
2. TPR at FPR **0.1% / 0.5% / 1%** on eval (binary fraud vs `normal` at a frozen threshold).
3. **Genuine FP:** false positive rate on rows with gold `label_family == normal`.
4. F1 at the **same** operating point as (2) — secondary, for PS wording.
5. APP **with vs without** `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure` (reuse ablation; if APP dies, **document**, do not hide).
6. AuthGate **p50/p99 ms/row** on a ≥1k-row batch (in-process `predict`). Not an issuer SLA.
7. Entity mule recall: gold mule **payee** caught on ≥1 inbound in eval (not only last edge).

**Forbidden claims:** live UPI; India prevalence; “we beat production”; SAML-D/PaySim **scores** until Plan 02 §10 checklist is ticked (`LOCKED.md` still unset). Lab mix ≠ India. Synthetic flags ≠ SDK. PSI is Generate sampler QA.

---

## Lock 3 — Rules then model then Brake

**Live order:** rules → AuthGate (sees rule-hit bits) → Brake. LLM is case/polish **grounded in reason codes only**. Never between 1 and 2.

### Rules (Phase B)

`when` is a list of predicates on **computed** columns, e.g. `fan_in_1h >= 6`, `is_new_payee == true`, `call_active_flag == true`.  

**Forbidden as rule inputs:** `smurf_cap_ratio`, `seasoning_days`, `fan_out_ttl_hours`, `mule_account_age_days` as catalog knobs, `gstin` string, `is_authorized_push`.

**Required kinds:** `hard_flag`, `nudge`, **`calm_down`**. Calm-downs from genuine shape: known payee (`is_new_payee == false`) + `amount_vs_p30` in a usual band + `is_new_device == false`. Not from the fraud catalog.

Evaluate on **row dicts**, not on `features_expected` key sets. Coverage map Loop I may still draft from catalog; **promotion** of a draft requires the row engine + genuine-FP smoke.

### Brake (mitigation — the product)

Persist on a **decision record** (not in train `X`): `policy_action`, `reason_codes[]`, `score`, `pred_label_family`.

| Predicted / rule band | Action | Must not |
|-----------------------|--------|----------|
| Low / calm-down wins | `allow` | Experiment on genuine kirana/rent |
| APP elevated | `notify` and/or `hold` | Silent hard decline of known payee |
| High ATO | `decline` | Mix gold APP rows into ATO decline in the **demo script** |
| Mule **payee** | `mule_credit_restrict` | Only scoring the sender |
| Invoice / BEC | `hold` or `case` | Amateur checksum-fail as the interesting case |

Enum: `allow | notify | step_up | hold | decline | mule_credit_restrict | case`.

SHAP optional. **Reason codes required** (rule ids + top features). LLM may polish analyst text from codes only.

---

## Lock 4 — APIs (keep existing; add score)

Keep `GET /defend/coverage-map`, `scout-topics`, `rules/v0`, `POST /loop-i/draft/{vector_id}`, `POST /miss/{vector_id}`.

**Add:**

| Method | Path | Body / behavior |
|--------|------|-----------------|
| `POST` | `/defend/fit` | `{ "run_id": "...", "world_seed": 42 }` — fit champion on that run’s train+split; write `models/<run_id>/` |
| `POST` | `/defend/score` | `{ "run_id": "...", "model_run_id": "..." }` — score split/eval rows; return metrics + action histogram; **no** `simulatable_signals` |
| `POST` | `/defend/loop-m` | Miss family → extra mix **or** retrain; compare G-test AP and genuine FPR |

HTTP bodies must not dump knobs or denylist columns. `fidelity` stays a Generate field; Defend reports `metrics.pass` against frozen floors in a fixture (not “KS p>0.05”).

No LangGraph `defend_graph` in v1. No Redis/ARQ. Fit/score are **sync** on demo-sized runs (same as Generate small `n_customers` in CI).

---

## Lock 5 — Tests that must exist before Defend is “done”

CI, not a notebook:

1. `train.parquet` columns ⊆ Plan 08 allowlist; denylist absent; `split.parquet` has `event_ts` + payer/payee; join does not put party ids into `X`.
2. `label_family` never `T01`…`T24`; `y` is family enum.
3. Reported split is **time + entity**, not `train_test_split(shuffle=True)` as the published number.
4. G-test uses **different `world_seed`**; AP on G-test is **reported** (may drop vs G-eval — honesty).
5. Rules: `fan_in_1h >= 6` fires on a fixture mule inbound row; does **not** fire because the key exists on a normal row with `fan_in_1h == 0`.
6. Calm-down: known payee + usual amount + old device → `allow` even if a weak model score.
7. Brake: predicted `app_fraud` → not `decline` by default; predicted `ato` → `decline` allowed; mule payee → `mule_credit_restrict`.
8. APP ablation AP **reported** with and without four session flags.
9. No `is_authorized_push` / `economic_class` / `technique_id` in model matrix.
10. `POST /defend/score` TestClient: 200, metrics keys present, no denylist in JSON.
11. Loop M: after injecting extra rows of one family (or retrain), G-test catch for that family **improves or is documented equal**; genuine FPR **not worse** beyond a frozen epsilon.
12. AuthGate bench: p99 ms/row logged; test fails only if scoring 1k rows takes **minutes** (hang), not if p99 is 5 ms vs 50 ms.

---

## Phase 0 — Generate handoff + live honesty (before Defend A)

Minimal overhead. **No** injector/world/fidelity-threshold changes. Do not loosen PSI or fraud-rate gates to make signs green.

### 0.1 `fidelity.pass` on validate

- `Makefile` `generate-validate`: assert `r['fidelity']['pass'] is True` (in addition to `event_count>1`, no `simulatable_signals`, `app_fraud>=3`).
- `scripts/validate_all_live.py` `_handoff`: same for population; canary may use `require_mix_rate=False` already — still assert no `simulatable_signals` and four stages. If canary fidelity fails mix-rate, **do not** skip; only skip mix-rate if the runner already does; still require `verify.pass` / non-flood.

### 0.2 HTTP tests `POST /generate/*`

New `tests/test_generate_api.py` (Postgres + `TestClient`):

- `POST /generate/population` small `n_customers` / `sim_days`, pin T13 filter optional; `event_count>1`; no `simulatable_signals`; `fidelity` key present; parquet path exists.
- `POST /generate/canary` campaign default; four `lifecycle_stages_logged`; shared `party_id`.
- `POST /generate/calibrate-world` `{ "fixture_id": "good_p2m_table" }` → `status=propose`; PDF fixture → `abstain`.
- No `POST /identify/calibrate-world`.

### 0.3 Telemetry gate (honest)

**What failed:** IC3 CSA PDF yielded 5 IPs; LLM/rules labeled **T13** → `classify_vector` → `human_social`; script asserted `vector_class == network_footprint`.

**Do not** coerce T13 deepfake/APP advisories to `network_footprint` to pass CI. IPs in a social-engineering alert are **indicators on a documentary case**, not proof of a mule botnet.

**Lock:** `scripts/validate_telemetry.py` passes when:

- ≥1 sanitized indicator extracted, **and**
- `corroboration_type` ∈ `{network-telemetry, documentary-case, not-yet-corroborated}`, **and**
- if `vector_class == network_footprint`, GreyNoise miss without API key is OK (already printed); **do not invent hits**, **and**
- if `vector_class == human_social`, still pass **if indicators were extracted** — print `telemetry_class=human_social indicators_kept_as_documentary` so the gate is about **extract+sanitize**, not a class lie.

Optional later: a **second** seed URL known to be T01/T07/bot. Not required to fake the first PDF.

### 0.4 Windows `./run.sh --check`

`run.sh` is bash; PowerShell has no `make`. **Add** `scripts/run.ps1` (or `run.ps1` at repo root) that: `docker compose up -d postgres --wait`; uses `.venv\Scripts\python.exe`; runs `scripts/validate_all_live.py` then `scripts/validate_telemetry.py`. Same stages as `run.sh`. Do not rewrite Identify. Makefile `validate-all-live` may call bash `run.sh` on Unix and document the ps1 on Windows.

### 0.5 Groq TPM 429

Transport **already** retries `{429,…}`. Sign-off saw TPM 8000 vs burst Identify. **Do not** disable Identify or shrink the catalog.

**Lock:**

- `.env.example`: Groq profile snippet + `IDENTIFY_MAX_DOCS=8` (or similar) **commented** as TPM hygiene; `AEGIS_LLM_MAX_RETRIES` / `AEGIS_LLM_RETRY_BASE_MS` documented.
- When `AEGIS_LLM_PROFILE=groq`, default retries **≥2** and honor `Retry-After` (already parsed). Optional small sleep between extract calls — **Identify settings only**, not Generate.
- Live log may still show 429s after retries; graph producing HITL rows is success. Do not assert zero 429s.

### 0.6 `pytest -m live_llm`

`conftest._isolate_llm_env` **always** deletes `GROQ_API_KEY` and forces OmniRoute — so `live_llm` skips even when the user configured Groq.

**Lock:** if the test item is marked `live_llm` or `live_identify`, **do not** strip provider keys / do not force OmniRoute. Offline default tests **keep** isolation. `test_live_omniroute_optional` rename comment to “live provider”; skip if `not is_llm_configured()`.

**Phase 0 tests must pass** before Phase A. Offline suite stays green.

---

## Build order (Defend)

Each phase: implement → **that phase’s tests green** → next. Full `pytest -m "not live_llm and not live_identify"` stays green.

### Phase A — Split artifact + schema

Write `split.parquet` next to train. Helper `packages/eval/split.py` (or `packages/policy/split.py`): time 2/3 + entity holdout; matrix builder drops split-only columns.

**Tests:** schema; shuffling ids into `X` fails an assertion; time cut uses `event_ts`.

### Phase B — Row-value rules + Brake table (no GBDT yet)

Rewrite `data/rules/v0_rules.yaml` + `evaluate_rules(row) -> hits, kind`. Fixture ledger rows. Brake function: family + hits + score → `policy_action`.

**Tests:** lock-5 items 5–7 on **fixtures** (no training). Coverage map still 24 techniques.

### Phase C — Champion fit + metrics + ablation

`packages/eval/fit.py` (name as you like): load run, split, fit, write `models/<run_id>/`. Metrics JSON. Reuse APP flag drop from ablation.

**Tests:** items 2, 3, 8, 9; small `n_customers` in CI (not 800). Seed 42 reproducible.

### Phase D — `POST /defend/fit` + `/defend/score` + latency log

Wire routes. Score does not require Atlas `vector_id`.

**Tests:** item 10–12; TestClient; p99 hang guard.

### Phase E — Loop M once

Miss list or `label_family` oversample → second fit → compare G-test (`world_seed=43`) AP for that family and genuine FPR.

**Tests:** item 11. Catalog `solved` **not** auto-set. `POST /defend/miss` still keeps `open`.

**Not in this pass:** Plan 11 Next.js, Cat 4 subgraph, HoldoutVault downloads, FLAML, PageRank, DuckDB, Redis, `defend_graph`.

---

## Implementation file map

Stay in `packages/eval/` (new, small) + `packages/policy/` + defend routes + `packages/sim/export.py` (split file only) + Phase 0 scripts/tests. Deps: existing `scikit-learn`; LightGBM **only if** Phase C picks it over HGB.

| Module | Role |
|--------|------|
| `packages/sim/export.py` | Also `split.parquet` |
| `packages/eval/split.py` | Time + entity holdout; `X`/`y` |
| `packages/eval/fit.py` | Champion fit + metrics |
| `packages/eval/brake.py` | Action enum |
| `packages/policy/rules.py` | Row-value evaluator |
| `apps/api/routes/defend.py` | fit / score / loop-m |
| `tests/test_eval_*.py`, `test_defend_api.py`, `test_generate_api.py` | Phase tests |
| `scripts/run.ps1` | Windows live e2e |
| `Makefile` `generate-validate` | `fidelity.pass` |
| `models/features.json` | Frozen recipe |

---

## Plan 02 strong points kept (do not drop)

- No LLM on authorization.
- APP ≠ ATO ≠ mule credit story (Brake table).
- PR-AUC / operating points; no accuracy-on-balanced-mix headline.
- Causal features only (`G(t−)` already in Generate windows: `fan_in_1h`, etc.). v1 does **not** add PPR; may add 24h/7d **later** in Generate then consume.
- Cat 4 unauthenticated API **off**; poisoning/HoldoutVault **named** in docx.
- Loop M must work once; `solved` is not ROC-on-G-dev.
- Case LLM optional, hostile input, never overwrites txn fields.

---

## Done when

- Phase 0 green: `fidelity.pass` in generate-validate; HTTP generate tests; telemetry honest; `run.ps1` documented; live_llm can see Groq; Groq retries documented.
- Champion trains on Plan 08 allowlist; split artifact enables time+entity cut.
- Rules fire on values; calm-downs exist.
- Brake APP ≠ ATO ≠ mule payee in tests and score histogram.
- Metrics include genuine FPR and APP ablation.
- Loop M once on G-test seed ≠ train seed.
- `/defend/score` returns actions + metrics; no knobs in JSON.

**Not done if:** knobs or `is_authorized_push` in `X`; random row split as the headline; Brake is “probability only”; APP win is only session flags and ablation is hidden; telemetry gate forces `network_footprint` on T13 PDFs; Generate still validated as 1-row stub.

---

## Gaps (docx — say out loud)

Laptop GBDT ≠ issuer AuthGate. No verified public-table HoldoutVault. Lab fraud rate ≠ India. Synthetic call/paste ≠ SDK. One retrain ≠ nine loops. PSI ≠ live UPI. Cat 4 is a recorded chart later, not a public red API.
