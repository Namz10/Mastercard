# Plan 08 — Generate: Real Build Plan
**Status:** PROPOSED — supersedes Plan 07 stub  
**Depends on:** Plan 01 (catalog / AttackSpec), Plan 02 (ledger schema, four injectors, fidelity gate)  
**Do not start coding until accepted.**

**Product one-liner:** Identify has two jobs. Job A (built) maps fraud write-ups → attack recipes. Job B maps public **volume** reports → a versioned `priors.json` (HITL). Generate builds a quiet UPI-like world from those priors, then replays approved recipes as extra labeled rows. Defend trains only on **computed** pay-time columns, never on recipe knobs.

---

## Why the current stub is garbage for training

`run_injector` copies catalog numbers onto one dummy JSON. `fan_in_1h: 18` is already filled in. The model reads a leftover label. That is not detection.

Need: many payments over time; a normal baseline; **causal** features from **past** rows only; `label_family` as **target**, never as an input.

---

## Research (keep short)

Use **PaySim-style world + typed injectors**. Do **not** use CTGAN/SDV/SMOTE for the ledger. Four injectors is standard (PaySim / SAML-D), not a hack.

---

## Two Identify jobs (never one schema)

| Job | Input | Output | Approve |
|-----|--------|--------|---------|
| **A — Attacks** | Fraud alerts | `AttackSpec` + ranges | HITL (exists) |
| **B — World priors** | NPCI / RBI **volume** pages only | `WorldPriors` **patch** (fields the page actually has) | HITL **required** |

Job B does **not** infer kirana spend from a mule article.

**Allowlist (code change when we build Job B):** add `npci.org.in` tier 1 next to `rbi.org.in`. Without this, Job B is fake.

**v1 fetch:** **HTML tables only**. If the page is PDF-only, **abstain** and keep last approved priors. Do not invent a PDF pipeline in this pass.

**Numeric gate before HITL:** if the page has volume and value, stored average must match `value/volume` within **5%**. Else abstain. Patch must list `source_url`, `as_of_month`, `raw_quotes`, `fields_updated[]`, `fields_unchanged[]`.

**Offline:** seed `data/priors.json` always ships. CI uses a **fixture HTML**, never live NPCI. Live Tavily is the same extract path with keys on.

**Job B may fill:** P2M category **mean tickets**, P2P/P2M split, UPI caps **if the page states a number**.  
**Job B must not fill:** hour-of-day, salary, rent — unless a cited table exists (v1: they stay `assumption` in seed).

Store `ticket_stat: "mean_from_value_over_volume"`. Never call it median.

**Allowed claim:** quiet life calibrated to the latest **approved** public aggregates, with provenance.  
**Forbidden claim:** cloned live UPI; normal spend extracted from fraud news.

New route, **not** AttackSpec: `POST /identify/calibrate-world` → proposed `WorldPriors` → HITL → write `data/priors.json` + `data/priors_history/{as_of}.json`.

---

## Layers

```
Job B (optional) → HITL → priors.json
Job A (exists)   → HITL → atlas recipes
       ↓
Load priors → quiet world → four injectors → verifier → fidelity vs THIS priors
       ↓
Parquet (Defend allowlist columns only)
```

Replace guts of existing `POST /generate/population` and `POST /generate/canary`. Do not add a third generate product.

### Population API (locked)

`POST /generate/population` **always** builds one world from current priors, then runs **all** generate-eligible injectors (mix budget below).  
`vector_id` **optional filter**: only that recipe family is injected; world still full quiet life.  
Response: `run_id`, Parquet path, fidelity pass/fail, **row counts by `label_family`**. HTTP body must **not** dump `simulatable_signals` into anything Defend might train on.

### Canary API (locked)

`POST /generate/canary`: **one** `world_seed`, **one** chain of synthetic accounts. Stages T09 → T11 → T13 → T02 write onto **the same ledger in time order**, not four fresh stubs.

**Calendar:** population default `sim_days: 90` (identity seasoning **clamped**, metadata `seasoning_clamped`).  
**Canary default `sim_days: 180`** so catalog `seasoning_days: 150` can actually run, then APP + mule cash-out still have calendar left. UI must show sim_days. Do not silently pretends 76 days is 150.

---

## Layer 1 — Seed priors + sampling

Seed file in-repo with `provenance` URLs. Category **means** from public NPCI tables (grocery ~₹214, fast food ~₹113, utilities ~₹1,345, etc.).

**Amount draw (locked):** lognormal per bucket, **mean matched** to stored mean, round to integer rupees, clamp to UPI-like caps. Not Uniform(1, 1e5).

Hour-of-day: seed **assumption** (bimodal 10–12 and 19–22) until a real public hourly table exists.

Caps (verifier): default ₹1–₹1,00,000 per txn / ₹1,00,000 per day unless priors override.

---

## Layer 2 — Quiet world

```
seed 42, n_customers 800, n_merchants 80, tick 15 min
population sim_days 90 | canary sim_days 180
```

Personas: salaried, kirana_shopper, small_biz, young_urban. Known payees. Running **balances**.

**Speed (done-when):** causal features via per-account running state, **not** full-ledger scan per row. Target: **50k rows in under 5 minutes** on a laptop.

Envelope: ids, time, rail, payer, payee, amount, `label_family`, `label_ts`.

**Computed (past only):** `account_age_days`, `payee_history_count`, `amount_vs_p30`, `fan_in_1h`, `fan_out_1h`, `is_new_payee`, `is_new_device`, `burst_velocity`.

**Flags (synthetic sensors):** call / paste / urgency / pause on **APP payment rows only**.  
`liveness_score` / `doc_consistency`: **only onboarding rows**, **NULL on later payments**. Never a constant on every row of a fraud account (that is an account-id leak).

---

## Layer 3 — Four injectors

YAML point knobs = **range centers** (±50%) until schema grows min/max. **Never copy knobs into train columns.**

**Fraud mix (of fraud rows, not of customers):** ~1–3% of all rows are fraud. Of fraud rows: mule ~40%, identity ~30%, APP ~20%, invoice ~10%. Tune injector counts to hit this; if the fidelity fraud-rate band fails, **change mix in config**, do not loosen the gate blindly.

### `graph_mule` — T01–T05 as one engine
Young mules, fan-in under cap, TTL then sink. Train on **computed** windows.

### `identity_trajectory`
Onboarding row with liveness in range. Quiet payments **`normal`**. Burst after seasoning → `identity_burst`. Population: clamp seasoning to `sim_days − 14`. Canary 180d: honor 150d.

Quiet txn **count** is whatever the Poisson world produced; run metadata records actual count vs catalog `seasoning_txn_count`. Do not fail the run if count ≠ 45; do fail if burst never happens.

### `app_session`
Many victims after day 30 (not one JSON). Same device, new payee, large vs **that victim’s** p30, `is_authorized_push=true`. Transcript optional sidecar, **not** a train column.

### `doc_beneficiary`
small_biz, checksum **passes** in code, wrong account → `invoice_fraud`.

---

## Layer 4 — Verifier

Reject: amount ≤ 0, overdraft, use-before-create. Defer mule out-same-tick. Reject rate > 20% of injector output → **fail run**.

---

## Layer 5 — Fidelity

Drop textbook “KS p > 0.05” as the gate. Use **PSI (or binned KS)** vs **this run’s** priors, thresholds **frozen in a fixture test**.

| Check | Pass |
|-------|------|
| Amount PSI, **normal** rows, by modeled buckets | PSI < T (fixture) |
| Hour PSI vs **hour prior actually used** | PSI < T |
| Fraud rate | 0.3%–5% |
| Mule inbound: median computed `fan_in_1h` | > 5 |
| Causal + export schema | tests |

---

## Labels and Defend columns (locked)

**`label_family` enum (training target):** `normal | mule | identity_burst | app_fraud | invoice_fraud`  
**Never** `T01`…`T24` as the train target. Technique ids stay in **run metadata / sidecar**, not Parquet train file.

**Parquet train allowlist:** computed windows + APP flags on those rows + `rail` + `kyc_tier` + `label_family` (target).

**Parquet / train denylist:** `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, transcripts, **`is_authorized_push`** (APP would become a one-bit oracle).

Schema test in CI: train file columns ⊆ allowlist.

**Split:** time (e.g. first 2/3 of **that run’s** calendar vs last 1/3).

**Lab sanity:** LightGBM PR-AUC by `label_family`. **Ablation:** same model with call/paste/urgency/pause **dropped**. If APP dies, say so in the doc.

---

## LLM

Job A: articles → recipes. Job B: tables → **validated** patch. World writes rupees. LLM never writes amounts or mule edges.

---

## Gaps (docx)

Synthetic flags ≠ SDK. Laptop ≠ NPCI volume. No real-fraud holdout. T06/T07/T20–T23 named. Job B cannot invent hours from a monthly bulletin.

---

## Build order

**MVP (must ship):**  
1. Seed priors + `WorldPriors`  
2. World + balances + O(n) features  
3. Four injectors + mix budget  
4. Verifier + fidelity fixture  
5. Population/canary internals + Parquet allowlist test  
6. Job B **fixture HTML → HITL → file** (no live NPCI required for MVP)

**Same sprint if time:** live Job B (allowlist + Tavily) after fixture works.  
**Canary 180d chain** is MVP for demo, not a leftover stub.

---

## Done when

- Fidelity pass vs **approved** priors; amounts from lognormal-mean match, not flat noise.  
- Four injectors write histories; `fan_in_1h` computed.  
- Population APP = many victims; mix in band.  
- Train Parquet matches allowlist/denylist tests.  
- Job B fixture: good table → proposed patch; bad/PDF → abstain; reject keeps seed.  
- Canary = one 180-day world, T09→T11→T13→T02 in order on shared accounts.  
- 50k rows < 5 min. Ablation without synthetic APP flags reported.

**Not done if:** knobs in train columns; Job B fills hours from fraud news; `label_family` is `T13`; liveness copied onto every payment; model only wins because `is_authorized_push` or `label_family` leaked in.
