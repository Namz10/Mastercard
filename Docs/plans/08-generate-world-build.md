# Plan 08 — Generate: Real World Build
**Status:** LOCKED — supersedes Plan 07 stub  
**Depends on:** Plan 01 (`AttackSpec`, T01–T24, `simulatable_signals`), Plan 02 (four injectors, Defend later, Cat 4 offline), Plan 03 (safety, `/generate/*` demo paths)  
**Generate-specific overrides of Plans 02/03** are listed in § Authority. Do not reopen Identify, naming, Cat 4-on-API, or AuthGate here.

**Product one-liner:** Identify (built) maps fraud write-ups → `AttackSpec` recipes. Generate loads a versioned `priors.json`, builds a quiet UPI-like world, then replays approved recipes as extra labeled rows. Defend trains only on **computed** pay-time columns, never on recipe knobs.

**Do not start coding until this file is the accepted Generate SSOT (it is).** Implement in phases A–G below. Each phase’s tests must pass before the next.

---

## Why the current stub is garbage for training

`packages/sim/injectors.py` copies catalog numbers onto one dummy JSON. `fan_in_1h: 18` is already filled in. `label_family` is `T13`. `liveness_score` defaults to `1.0` on every row. The model would read leftover labels and knobs. That is not detection.

Need: many payments over time; a normal baseline; **causal** features from **past** rows only; `label_family` as **target**, never as an input.

```
priors.json + Atlas
       ↓
quiet world (event-driven) → four injectors (mix budget) → verifier → fidelity
       ↓
Train Parquet (allowlist)  +  sidecar (knobs, technique_id)
```

Replace guts of existing `POST /generate/population` and `POST /generate/canary`. Do not add a third generate product (`/sim/run` is not the public path).

---

## Authority: when 08 beats Plans 00–03

Plans 00–03 stay SSOT for **Identify, safety, naming, Cat 4 offline, AuthGate later**. For **Generate fidelity**, this file wins:

| 08 choice | Beats | Keep |
|-----------|--------|------|
| Population = full quiet world + **all** generate-eligible injectors; `vector_id` is a **filter** | Plan 02 “one recipe → one event”; current `tests/test_generate_handoff.py` | Rewrite those tests; keep `POST /generate/population` and `POST /generate/canary` |
| PSI vs **this run’s** priors; drop KS p > 0.05 | Plan 02 “KS or PSI” | **Plus** independent `fan_in_1h` recompute (required or the stub still “passes”) |
| `label_family` train target, never `T01`…`T24` | Stub + Plan 02 `label_class` as the only label | Keep `economic_class` + `label_ts` on the **full ledger / sidecar**, not as a train feature |
| No CTGAN/SDV/SMOTE on the ledger; hand-authored `data/priors.json` | Plan 03 “fit SDV GaussianCopula” | Explicit supersede of that seed sentence |
| Canary = **one** 180-day ledger, T09→T11→T13→T02 on **shared** `VID-SIM-…` accounts | Stub’s four independent JSONs | Pin catalog knobs on canary |
| Deterministic world; LLM never writes rupees or mule edges | Plan 02 “strong LLM persona” for Cat 2 | v1 identity is Poisson + rules; LLM trajectories are post-ledger |

**MC_PS / research:** benign world then perturbation; APP ≠ stolen-card; mule graph as computed windows; synthetic only; ablation without APP flags.

---

## Lock 1 — WorldCalibrator, not Identify Job B

Identify stays **Job A only**: articles → `AttackSpec` (already built). Do not split Identify into two products.

World priors live under **Generate**:

- Seed file `data/priors.json` always ships in-repo with `provenance` URLs.
- Category **means** from public NPCI-style tables (grocery ~₹214, fast food ~₹113, utilities ~₹1,345, etc.).
- Store `ticket_stat: "mean_from_value_over_volume"`. Never call it median.
- Hour-of-day: seed **assumption** (bimodal 10–12 and 19–22) until a cited public hourly table exists.
- Caps (verifier): default ₹1–₹1,00,000 per txn / ₹1,00,000 per day unless priors override.

**MVP:** ship the seed file. Optional last phase (F): fixture HTML → HITL → patch file.  
**No** `POST /identify/calibrate-world`. If a route exists, it is `POST /generate/calibrate-world`.  
**No** live NPCI/Tavily in this Generate pass. **No** `npci.org.in` allowlist change until that optional phase.

WorldCalibrator **may** fill (when a fixture/page actually has the number): P2M category mean tickets, P2P/P2M split, UPI caps.  
WorldCalibrator **must not** fill: hour-of-day, salary, rent — unless a cited table exists (v1: they stay `assumption` in seed).

Numeric gate before HITL (phase F): if the page has volume and value, stored average must match `value/volume` within **5%**. Else abstain. Patch must list `source_url`, `as_of_month`, `raw_quotes`, `fields_updated[]`, `fields_unchanged[]`. PDF-only → abstain; keep last approved priors. No PDF pipeline in this pass.

**Allowed claim:** quiet life calibrated to the latest **approved** public aggregates, with provenance.  
**Forbidden claim:** cloned live UPI; normal spend extracted from fraud news; infer kirana hours from a mule article.

---

## Lock 2 — Envelope + train allowlist / denylist

Schema: `gff.txn.v1`.

Full ledger (not the train file) includes:

- `event_id`, `event_ts`, `rail`, `party_ids` (payer / payee), `amount_minor` (integer paise), `currency`
- `label_family` (training target), `label_ts`, `economic_class` (Brake typology; sidecar / metrics only)
- Computed auth columns below

IDs: ULID events; `VID-SIM-…` parties. Never real PAN/VPA/Aadhaar.

**`label_family` enum (locked):** `normal | mule | identity_burst | ato | app_fraud | invoice_fraud`  
**Never** `T01`…`T24` as the train target. Technique ids stay in **run metadata / sidecar**.

| Catalog | Quiet rows | Fraud / burst rows |
|---------|------------|--------------------|
| T11 | `normal` | `identity_burst` after seasoning |
| T12 (`device_hash_shift`) | `normal` | **`ato`** (not `identity_burst` — else Brake cannot hold APP vs decline ATO) |
| T01–T05 | — | `mule` |
| T13 (and other APP injectors) | — | `app_fraud` |
| T24 | — | `invoice_fraud` |
| T08/T09/T10 onboarding | liveness / `doc_consistency` **only on those rows**; later payments **NULL** | — |

**Train Parquet allowlist:** `rail`, `kyc_tier`, computed windows (`account_age_days`, `payee_history_count`, `amount_vs_p30`, `fan_in_1h`, `fan_out_1h`, `is_new_payee`, `is_new_device`, `burst_velocity`), APP flags **only on APP rows** (`call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`), `label_family`.

**Train Parquet denylist:** `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, transcripts, **`is_authorized_push`**, `economic_class`, `label_class` if it encodes fraud type, GSTIN + 3DS + VPA + embeddings concatenated on every row.

Schema test in CI: train file columns ⊆ allowlist; denylist columns absent.

Sidecar JSON (not Defend train): knobs, `technique_id`, campaign stage, `seasoning_clamped`, actual vs catalog `seasoning_txn_count`.

**Split (document now, Defend later):** time cut (first 2/3 vs last 1/3 of **that run’s** calendar) **plus** hold out some mule components / customer ids so the model cannot memorize entities.

---

## Lock 3 — Four injectors and modes

YAML point knobs = **range centers**. **Never copy knobs into train columns.** Train on **computed** windows.

**Jitter:** population ±50%, clamped to schema (`liveness_score` in [0,1], `smurf_cap_ratio` in (0,1], amounts inside caps).  
**Canary: pin exact `simulatable_signals`.** No ±50% on canary rows.

### `graph_mule` — T01–T05 as one engine (modes)

| Mode | Catalog | Behavior |
|------|---------|----------|
| `funnel` | T01 | Many senders → young mule; **compute** `fan_in_1h` from edges |
| `cashout` | T02 | TTL then sink MCC/flag; not live crypto |
| `smurf` | T03 | Amounts just under cap (`smurf_cap_ratio`) |
| `hop` | T04 | Typed UPI-like → IMPS-like hop in sim time |
| `dust` | T05 | Many tiny outbound edges |

T06 / T07 stay `name_only`. T20–T23 stay Cat 4 / named. T19 = session flags only.

### `identity_trajectory`

Onboarding row with liveness in range. Quiet payments `normal`.  
T11 burst after seasoning → `identity_burst`.  
T12 device shift burst → `ato`.  
Population: clamp seasoning to `sim_days − 14`; metadata `seasoning_clamped`.  
Canary 180d: honor catalog `seasoning_days: 150`.  
Quiet txn **count** is whatever the Poisson world produced; sidecar records actual vs catalog `seasoning_txn_count`. Do not fail the run if count ≠ 45; **do fail if burst never happens**.

v1 is **deterministic** (Poisson + rules). Plan 02 LLM persona / `next_prompt` is post-ledger, not this pass.

### `app_session`

Many victims after day 30 (not one JSON). Same device, new payee, large vs **that victim’s** p30. Session flags only on those rows. Transcript optional sidecar, **not** a train column.

### `doc_beneficiary`

`small_biz`; checksum **passes** in code; wrong account → `invoice_fraud`. Amateur checksum-fail rows are not the interesting case.

---

## Lock 4 — Population vs canary (API)

Keep `apps/api/routes/generate.py` paths.

### Population

`POST /generate/population` **always** builds one world from current priors, then runs **all** generate-eligible injectors (mix budget).  
`vector_id` **optional filter**: only that recipe family is injected; world still full quiet life.

Defaults: `world_seed=42`, `n_customers=2400`, `n_merchants=120`, `sim_days=90`.

Response: `run_id`, Parquet path, fidelity pass/fail, **row counts by `label_family`**. HTTP body must **not** dump `simulatable_signals` into anything Defend might train on.

### Canary

`POST /generate/canary`: **one** `world_seed`, **one** chain of synthetic accounts. Stages T09 → T11 → T13 → T02 write onto **the same ledger in time order**, not four fresh stubs. Campaign pin: `packages/catalog/campaigns.py` (`fincen-fin-2024-alert004`). Default `sim_days: 180` so catalog `seasoning_days: 150` can run, then APP + mule cash-out still have calendar left. UI must show `sim_days`. Do not silently pretend 76 days is 150. Knobs **pinned**.

### Mix (lab oversample, not India prevalence)

~**1–3%** of all rows are fraud. Of fraud rows: mule ~40%, `identity_burst` ~25%, `ato` ~5%, APP ~20%, invoice ~10%. Tune injector counts to hit this. If the fidelity fraud-rate band fails, **change mix in config**, do not loosen the gate.

**Gate:** 0.5%–3.5% fraud rows. Write-up must say this is lab oversample.

### World mechanics

- **Event-driven** Poisson per persona (`salaried`, `kirana_shopper`, `small_biz`, `young_urban`). Not “every agent every 15 min”.
- 15 min is the **velocity bin**, not the actor tick.
- Amount draw: lognormal per bucket, **mean matched** to stored mean, round to integer rupees via `amount_minor`, clamp to UPI-like caps. Not Uniform(1, 1e5).
- Causal features via per-account running state, **not** full-ledger scan per row. Target: **50k rows in under 5 minutes** on a laptop (Phase G; `slow` marker — do not fail CI on 6 min; **do** fail if still a 1-row stub).
- Wallet: reject amount ≤ 0 and use-before-create. Insufficient float = reject/defer that payment. **Do not** invent a Western overdraft product story.
- Defer mule out-same-tick.
- High injector reject rate: **warn + retune**. Fail the run only on invariant flood (e.g. >20% of injector output is amount ≤ 0 / use-before-create), not because caps are tight.

---

## Lock 5 — Tests that must exist before Generate is “done”

CI, not a notebook:

1. Train Parquet columns ⊆ allowlist; denylist columns absent.
2. `label_family` never equals `T01`…`T24`.
3. Independent recompute: `fan_in_1h` from edges on a fixture ledger **≠** catalog YAML copy; median mule inbound `fan_in_1h` > 5.
4. `liveness_score` / `doc_consistency` NULL on post-onboarding payments for the same account.
5. APP flags false/null on non-APP rows.
6. Canary: one 180-day world, four stages in order, **shared** party ids, catalog knobs pinned (no ±50% on those rows).
7. Population with `vector_id=t13`: quiet world exists; only `app_fraud` extra family (plus `normal`); many APP victims, not one row.
8. PSI amount (normal, by bucket) and hour vs **this run’s** priors; thresholds frozen in a fixture; seed 42 reproducible.
9. Causal: feature at t uses only events with `time < t` (tiny synthetic clock test).
10. Seasoning clamp metadata on 90d population vs 150d catalog T11.
11. 50k-row smoke under ~5 min (mark `slow`; fail if still 1-row stub).
12. Ablation smoke (sklearn / LightGBM OK): same model without call/paste/urgency/pause — APP metric must be **reported**; if APP dies, that is a documented result, not a silent cheat.

PSI vs this run’s priors is a **sanity check** (catches Uniform noise). It is **not** proof of live UPI. Independent `fan_in_1h` recompute is the anti-stub gate.

---

## Fidelity (Layer 5)

Drop textbook “KS p > 0.05” as the gate. Use **PSI (or binned KS)** vs **this run’s** priors, thresholds **frozen in a fixture test**.

| Check | Pass |
|-------|------|
| Amount PSI, **normal** rows, by modeled buckets | PSI < T (fixture) |
| Hour PSI vs **hour prior actually used** | PSI < T |
| Fraud rate | 0.5%–3.5% |
| Mule inbound: median computed `fan_in_1h` | > 5 |
| Causal + export schema | tests in lock 5 |

---

## LLM

Identify Job A: articles → recipes (exists). WorldCalibrator: tables → **validated** patch (phase F fixture only). World **code** writes rupees. LLM never writes amounts or mule edges.

---

## Non-goals (this Generate pass)

Live NPCI, PDF pipeline, SDV/CTGAN/SMOTE, Cat 4 public API, Next.js, AuthGate/Brake as the product, Redis/ARQ, LangGraph generate subgraph, Plan 02 LLM identity proposer, T06 merchant cycles, T07 CNP.

Lab LightGBM is **only** the leakage/ablation smoke (done-test 12), not Defend.

---

## Implementation file map

Stay in `packages/sim/` + generate routes + tests. Add deps only as needed: `numpy`, `pandas`, `pyarrow`.

| Module | Role |
|--------|------|
| `packages/sim/priors.py` + `data/priors.json` | Load/validate WorldPriors |
| `packages/sim/world.py` | Personas, Poisson events, balances, RNG seed |
| `packages/sim/features.py` | O(n) running causal features |
| `packages/sim/injectors/` | Replace stub engines; keep `run_injector` as dispatcher |
| `packages/sim/verifier.py` | Invariants |
| `packages/sim/fidelity.py` | PSI + mix gate + recompute checks |
| `packages/sim/export.py` | Train Parquet + sidecar |
| `packages/sim/runner.py` | Rewrite population/canary |
| `tests/test_sim_*.py` | Phase tests |
| Rewrite `tests/test_generate_handoff.py` and Makefile `generate-validate` | Stop asserting 1-event stub + `simulatable_signals` in body |

---

## Build order (implement after this lock)

Each phase: implement → **phase tests must pass** before the next. Full `pytest -m "not live_llm and not live_identify"` stays green (rewrite stub tests in the phase that breaks them, not later).

### Phase A — Priors + sampling

`WorldPriors` Pydantic; seed `data/priors.json`; lognormal mean-match; hour assumption; caps.

**Tests:** schema validates; Uniform(1, 1e5) would fail mean-match; clamp to caps; `ticket_stat` is mean not median.

### Phase B — Quiet world + O(n) features

Defaults 2400 customers × 120 merchants, seed 42, event-driven, `amount_minor`, `VID-SIM-…`.

**Tests:** all `label_family=normal`; no future leakage on `payee_history_count` / `is_new_payee`; never pay before create; 1k-row microbench uses running state not O(n²).

### Phase C — Four injectors + mix

Modes T01–T05, T11 vs T12, APP many victims, checksum-pass invoice.

**Tests:** families present; T12 → `ato`; knobs not equal to `features_auth.fan_in_1h`; APP flags only on APP rows; liveness NULL after onboarding; mix in 1–3% on a small seeded run.

### Phase D — Verifier + fidelity fixtures

**Tests:** amount ≤ 0 rejected; PSI fixture golden; fraud-rate gate; mule median `fan_in_1h` > 5; independent recompute.

### Phase E — Population / canary + Parquet

Wire APIs; 90d / 180d; sidecar vs train.

**Tests:** done-list items 1–10; canary shared ids; `vector_id` filter; HTTP body has no `simulatable_signals`; `generate-validate` checks Parquet path + counts, not `event_count==1`.

### Phase F (MVP last, no live net) — WorldCalibrator fixture

Fixture HTML good table → patch proposal; PDF/bad → abstain; reject keeps seed.

**Tests:** that path only. Skip live Tavily.

### Phase G (same sprint if time) — 50k smoke + APP ablation report

Mark `slow`; write one paragraph for the later `.docx`.

---

## Done when

- Fidelity pass vs **approved** priors; amounts from lognormal-mean match, not flat noise.
- Four injectors write histories; `fan_in_1h` **computed**, not copied from YAML.
- Population APP = many victims; mix in band; T12 labeled `ato`.
- Train Parquet matches allowlist/denylist tests; lock-5 tests 1–10 green.
- WorldCalibrator fixture (phase F): good table → proposed patch; bad/PDF → abstain; reject keeps seed.
- Canary = one 180-day world, T09→T11→T13→T02 in order on shared accounts, knobs pinned.
- 50k-row smoke exists (phase G); ablation without synthetic APP flags reported.

**Not done if:** knobs in train columns; WorldCalibrator fills hours from fraud news; `label_family` is `T13`; liveness copied onto every payment; T12 collapsed into `identity_burst`; model only wins because `is_authorized_push` or `label_family` leaked in; canary still four independent stub JSONs.

**After Generate:** implement Defend from [`02-defend-build.md`](02-defend-build.md) (split artifact, champion, Brake, Loop M). Phase 0 of that plan hardens `fidelity.pass` + `POST /generate/*` tests without reopening injectors.

---

## Gaps (docx — say out loud)

Synthetic flags ≠ SDK. Laptop ≠ NPCI volume. No real-fraud holdout. T06/T07/T20–T23 named. Hours are assumptions. Lab fraud rate ≠ India prevalence. PSI vs own priors is sampler QA, not “this is live UPI.”
