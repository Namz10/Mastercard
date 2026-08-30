# Generate full context pack

**Purpose:** single context dump for Generate work. Feed this file as-is. Do not implement Generate from Plan 07, from `packages/sim/injectors.py` (stub), or from Defend docs.

**Canonical siblings (do not contradict):**

| Doc | Role |
|-----|------|
| [`Docs/plans/08-generate-world-build.md`](../../Docs/plans/08-generate-world-build.md) | **Generate SSOT.** Quiet world, four injectors, Parquet allowlist, population/canary, WorldCalibrator |
| [`Docs/LOCKED.md`](../../Docs/LOCKED.md) | Plan 08 wins for Generate. Plan 07 is superseded |
| [`Docs/plans/01-identify-catalog-lock.md`](../../Docs/plans/01-identify-catalog-lock.md) | AttackSpec, T01-T24, `simulatable_signals`, generate vs name-only |
| [`docs/agent/DEFENSE-FULL-CONTEXT.md`](DEFENSE-FULL-CONTEXT.md) | What Defend consumes from this ledger. Do not train AuthGate in a Generate pass |
| [`Docs/generate_app_ablation.md`](../../Docs/generate_app_ablation.md) | Phase G APP-flag ablation paragraph |
| [`MC_PS.md`](../../MC_PS.md) | Identify, Generate, Defend as one loop |

**Product one-liner.** Identify maps fraud write-ups to `AttackSpec` recipes. Generate loads versioned `data/priors.json`, builds a quiet UPI-like world in code, then replays approved recipes as extra labeled rows. Defend trains only on **computed** pay-time columns, never on recipe knobs.

This is a **research lab prototype** for Mastercard Innovation Challenge @ GFF 2026. Not live UPI. Not India prevalence. Not a production rail.

**Status:** Plan 08 phases A-G are implemented. Do not reopen the stub world.

---

## 0. What you must not mix

| Forbidden mix | Why |
|---------------|-----|
| Quiet world with a glued-on fraud CSV | Fraud is a constrained perturbation of the same ledger |
| Catalog knobs copied into train columns | `fan_in_1h: 18` in YAML is a range center. Train on **computed** windows |
| `label_family` = `T13` | Train target is six families only. Technique ids live in sidecar |
| T12 labeled `identity_burst` | T12 is `ato`. Else Brake cannot decline ATO while holding APP |
| Population jitter on canary rows | Population ±50%. Canary **pins** catalog knobs |
| Seed 42 API default with v1 photography seeds 46/47/48 | Runner default `world_seed=42`. Frozen Defend worlds are 46/47/48/49. Do not regenerate seed 48 |
| `packages/config/scale.py` seeds 42/43/44/45 as v1 photography | Museum scale constants |
| PSI vs own priors as "this is live UPI" | Sampler QA only |
| Lab 1-3% fraud rate as India prevalence | Write-up must say lab oversample |
| LLM writing rupees or mule edges | Amounts and graph edges come from **code** |
| `packages/sim/injectors.py` as the engine | Stub. Real engines are `packages/sim/inject/` |
| WorldCalibrator filling hours from fraud news | Hours stay `assumption` until a cited hourly table exists |
| APP session flags as an SDK | Synthetic flags. Ablation must report APP metric with flags zeroed |
| Train on `is_authorized_push` | Denylist. APP vs ATO is `label_family`, not that bit |
| GSTIN + 3DS + VPA + chat embedding on every row | Thin envelope. Typed payload only where the injector needs it |
| Plan 07 | Superseded by Plan 08 |

---

## 1. Job in the brief

Generate must simulate identified attacks at scale with fidelity close enough that a detector can train and be stress-tested. Quiet life first. Fraud is extra labeled rows on that tape, not a second file.

Identify owns the catalog. Generate owns the world. Defend owns the scorer. Generate does **not** fit AuthGate, pick thresholds, or run Brake except the Plan 08 Phase G leakage/ablation smoke (report only).

Pattern for every family:

```
structured params (catalog simulatable_signals, jittered or pinned)
    → deterministic engine (code)
    → verifier (accept or bounded repair)
    → only code may accept a sample
```

---

## 2. Pipeline

```
data/priors.json + Atlas (generate-eligible AttackSpec rows)
    → generate_quiet_world(seed, n_customers, n_merchants, sim_days)
    → apply_mix (four injector families, lab oversample)
        or inject_fincen_chain (canary, pinned, one shared account chain)
    → verify_events (amount > 0, no use-before-create, reject flood)
    → evaluate_fidelity (PSI, fraud-rate band, mule fan-in median, anti-stub)
    → export_run → train.parquet + split.parquet + sidecar.json
```

HTTP must never dump `simulatable_signals` into a body Defend might train on.

Code path:

```
packages/sim/priors.py          load WorldPriors
packages/sim/world.py           Poisson quiet life
packages/sim/features.py        O(n) causal FeatureComputer
packages/sim/inject/mix.py      population mix budget
packages/sim/inject/*.py        four engines + canary chain
packages/sim/verifier.py        ledger invariants
packages/sim/fidelity.py        PSI + mix + anti-stub
packages/sim/export.py          allowlist Parquet + sidecar
packages/sim/runner.py          run_population / run_canary
packages/sim/calibrator.py      fixture HTML → HITL patch of priors
packages/sim/ablation.py        Phase G APP-flag smoke, not Defend
apps/api/routes/generate.py     public HTTP
```

---

## 3. The quiet world

Deterministic, event-driven, Poisson. Not "every agent every 15 minutes." 15 min is a **velocity bin**, not an actor tick.

| Knob | Default | Notes |
|------|--------:|-------|
| Customers | 2400 | `VID-SIM-C-NNNNNN` |
| Merchants | 120 + 3 hubs | Merchants `VID-SIM-M-*`; hubs `VID-SIM-HUB-001/002/003` |
| Calendar | 90 days population, 180 days canary | `t0 = 2024-01-01T00:00:00+00:00` |
| Rail | `upi_like` | IMPS hop exists only as mule injector rail-switch |
| Currency | `INR` | `amount_minor` = integer **paise**. ₹1 = 100 |
| Schema | `gff.txn.v1` | Thin envelope |

Never real PAN / VPA / Aadhaar.

### 3.1 Party prefixes

| Prefix | Meaning |
|--------|---------|
| `VID-SIM-C-` | Customer |
| `VID-SIM-M-` | Merchant |
| `VID-SIM-HUB-` | Legitimate high-fan-in hub. Hard negative for mule |
| `VID-SIM-U-` | Mule payee |
| `VID-SIM-APP-` | APP-related synthetic party |
| `VID-SIM-CHAIN-` | Canary shared accounts |
| `evt-NNNNNNNNNN` | Event ids |
| `evt-lm-*` | Loop M extras (Defend, train only — Generate must not write these onto holdout seeds) |

### 3.2 Personas

From `data/priors.json`:

| Persona | Weight | Txn / day (λ) | Spend buckets | KYC |
|---------|-------:|--------------:|---------------|-----|
| `salaried` | 0.35 | 1.1 | grocery, utilities, telecom, p2p, fuel | tier2 |
| `kirana_shopper` | 0.30 | 2.0 | grocery×2, utilities, p2p | tier2 |
| `small_biz` | 0.15 | 3.2 | fuel, telecom, utilities, p2p, grocery | tier2 |
| `young_urban` | 0.20 | 1.7 | fast_food, telecom, p2p, grocery | **tier1** |

Known-payee list per customer: bucket merchants + 2-4 friend customers + with p=0.45 one hub. ~4% of customers get a genuine device upgrade mid-run.

P2M share = 0.62. Hour-of-day is a **stated assumption** (bimodal 10-12 and 19-22), not a cited NPCI hourly table.

### 3.3 Amounts and caps

Lognormal per bucket, **mean matched** to stored category mean, round to integer rupees via paise, clamp to caps. Not `Uniform(1, 1e5)`. Stored `ticket_stat` is `mean_from_value_over_volume`. Never call it median.

| Cap / prior | Value | Human |
|-------------|------:|-------|
| `txn_min_minor` | 100 | ₹1 |
| `txn_max_minor` | 10_000_000 | ₹1,00,000 |
| `day_max_minor` | 10_000_000 | ₹1,00,000 / day / payer |
| Lognormal σ | 0.55 | Mean-matched then clamped |
| Customer opening float | uniform 15e6-40e6 paise | ₹1.5L-₹4L |
| Merchant opening | 80e6 paise | ₹8L |
| Hub opening | 500e6 paise | ₹50L |

Category means (public aggregate value/volume, **not** live UPI rows): grocery 214, fast_food 113, utilities 1,345, fuel 620, telecom 399, p2p 850. Salary 28,000 and rent 12,000 are **assumptions**.

Wallet: amount ≤ 0 rejected; use-before-create rejected; insufficient float = skip that payment (no Western overdraft). Daily cap: skip if over. Mule out-same-tick is deferred.

**Allowed claim:** quiet life calibrated to the latest approved public aggregates, with provenance. **Forbidden claim:** cloned live UPI; normal spend extracted from fraud news.

### 3.4 Causality

Feature at payment `t` uses only edges with timestamp `< t` (`G(t-)`). Snapshot **before** applying the current edge to running state, then apply. O(n) per-account deques (1h / 24h / 7d / 30d), not O(n²) full-ledger scans.

Defaults if no history: `hours_since_prev_txn` = 168.0; `hours_since_payee` = 720.0; `amount_vs_p30` / `amount_vs_7d_mean` = 1.0.

Leakage test: full-graph vs `G(t-)` must **diverge**. If they match, features are leaking.

---

## 4. Four injectors

YAML point knobs = range centers. Never copy knobs into train columns.

**Population jitter:** ±50%, clamped to schema (`liveness_score` in [0,1], `smurf_cap_ratio` in (0,1], amounts inside caps).  
**Canary:** pin exact `simulatable_signals`. No ±50%.

v1 identity is Poisson + rules. Plan 02 LLM persona / `next_prompt` is post-ledger, not this pass.

### 4.1 `graph_mule` — T01-T05, one engine

| Mode | Catalog | Behavior |
|------|---------|----------|
| `funnel` | T01 | Many senders → young mule. **Compute** `fan_in_1h` from edges |
| `cashout` | T02 | TTL then sink MCC/flag. Not live crypto |
| `smurf` | T03 | Amounts just under cap (`smurf_cap_ratio`) |
| `hop` | T04 | Typed UPI-like → IMPS-like hop in sim time |
| `dust` | T05 | Many tiny outbound edges |

T06 / T07 stay `name_only`. T20-T23 stay Cat 4 / named. T19 = session flags only.

Majority of mule budget is `funnel_fast` so median computed inbound `fan_in_1h` > 5. Harder variants are a minority.

### 4.2 `identity_trajectory`

Onboarding row with liveness in range. Quiet payments `normal`.

- T11 burst after seasoning → `identity_burst`
- T12 device-hash shift burst → `ato`

Population: clamp seasoning to `sim_days - 14`; sidecar `seasoning_clamped`. Canary 180d: honor catalog `seasoning_days: 150`. Quiet txn **count** is whatever Poisson produced; sidecar records actual vs catalog `seasoning_txn_count`. Do not fail if count ≠ 45. **Do fail if burst never happens.**

### 4.3 `app_session`

Many victims after day 30 on a 90d world (not one JSON). Same device, new payee, amount large vs **that victim's** p30. Session flags only on those rows: `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`. Transcript optional sidecar, **not** a train column.

### 4.4 `doc_beneficiary`

`small_biz`. GSTIN checksum **passes in code**. Wrong account → `invoice_fraud`. Amateur checksum-fail rows are not the interesting case.

### 4.5 Knob centers (never in X)

| Injector | Knob | Center |
|----------|------|-------:|
| graph_mule | `fan_in_1h` | 18 |
| graph_mule | `fan_out_ttl_hours` | 4.0 |
| graph_mule | `smurf_cap_ratio` | 0.85 |
| graph_mule | `mule_account_age_days` | 3 |
| identity_burst | `seasoning_days` | 150 |
| identity_burst | `seasoning_txn_count` | 45 |
| ato | `device_hash_shift` | true |
| app_session | `call_active_flag` | true |
| app_session | `copy_paste_payee_flag` | true |
| app_session | `pause_ms` | 1800 |
| app_session | `urgency_pressure` | 0.85 |
| app_session | `new_payee` | true |

Anti-stub: computed `fan_in_1h` on the ledger must not equal the knob on every mule row. Variance must be > 0.

---

## 5. Labels

Exactly six. **Never** `T01`…`T24` as the train target.

| `label_family` | How it gets on a row | Catalog |
|----------------|----------------------|---------|
| `normal` | Quiet Poisson world | — |
| `mule` | graph_mule T01-T05 | T01-T05 |
| `identity_burst` | identity_trajectory T11 after seasoning | T11 |
| `ato` | identity_trajectory T12 device-hash shift | T12 |
| `app_fraud` | app_session | T13 and other APP injectors |
| `invoice_fraud` | doc_beneficiary, checksum passes, wrong account | T24 |

`economic_class` and `label_class` stay on the full ledger / sidecar. Not train features. Technique ids stay in run metadata.

T08/T09/T10 onboarding: liveness / `doc_consistency` **only on those rows**. Later payments for the same account are NULL.

---

## 6. Mix (lab oversample, not India)

Target fraud **rate of rows**: ~2% (clamped 1-3% in mix code). Fidelity gate **0.5%-3.5%**. If the band fails, **change mix in config**, do not loosen the gate.

Of fraud rows (`packages/sim/inject/mix.py` `DEFAULT_SHARES`):

| Family | Share of fraud rows |
|--------|--------------------:|
| mule | 0.40 |
| identity_burst | 0.25 |
| ato | 0.05 |
| app_fraud | 0.20 |
| invoice_fraud | 0.10 |

`vector_id` on `POST /generate/population` is an **optional filter**: still a full quiet world; only that recipe family is injected.

---

## 7. Genuine-world noise (hard negatives in quiet life)

So the model cannot treat every stamp as fraud:

| Noise | Rate | Effect |
|-------|-----:|--------|
| Weak APP-shaped flags on normals | 2% | call p=0.15, paste p=0.25, pause 0-800, urgency U(0,0.35) |
| Paste-only on normals | 0.4% | paste true, pause 200-1200, no call, urgency 0 |
| Invoice-shaped payload on `small_biz` normals | 0.6% | `beneficiary_changed=True`, checksum ok, lookalike false |
| Device upgrade | ~4% of customers | genuine `is_new_device` |
| Hub fan-in | structural | legitimate `fan_in_1h` can exceed mule rule threshold |

---

## 8. Train export

`packages/sim/export.py`.

**Allowlist (train Parquet columns ⊆ this):**  
`rail`, `kyc_tier`, `account_age_days`, `payee_history_count`, `amount_vs_p30`, `fan_in_1h`, `fan_out_1h`, `fan_in_unique_payers_1h`, `is_new_payee`, `is_new_device`, `burst_velocity`, `fan_in_24h`, `fan_out_24h`, `fan_in_unique_payers_24h`, `txn_velocity_24h`, `hours_since_prev_txn`, `hours_since_payee`, `amount_vs_7d_mean`, `unique_payees_7d`, `payee_fan_out_1h`, `in_out_asymmetry_24h`, `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`, `beneficiary_changed`, `gstin_checksum_ok`, `lookalike_domain_flag`, `label_family`.

**Denylist (must be absent from train file):**  
`vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, transcripts, `is_authorized_push`, `economic_class`, `label_class`, `gstin`, `payload`.

Split artifact (eval join only, not concatenated into X): `event_id`, `event_ts`, `payer`, `payee`, `amount_minor`, `label_family`, `campaign_id`.

Sidecar JSON (not Defend train): knobs, `technique_id`, campaign stage, `seasoning_clamped`, actual vs catalog `seasoning_txn_count`, seed, mix tallies.

CI: train columns ⊆ allowlist; denylist columns absent; `label_family` never equals `T01`…`T24`.

---

## 9. Fidelity and verifier

Verifier (`packages/sim/verifier.py`): amount ≤ 0 and use-before-create are rejects. Fail the run on invariant flood (>20% of rows failing those), not because caps are tight. High injector reject rate: warn + retune.

Fidelity (`packages/sim/fidelity.py`) vs **this run's** priors. Not KS p > 0.05.

| Gate | Pass (code constants) |
|------|------|
| Amount PSI, normal rows, by bucket | PSI < 0.25 (`PSI_AMOUNT_MAX`) |
| Hour PSI vs hour prior actually used | PSI < 0.35 (`PSI_HOUR_MAX`) |
| Fraud rate | 0.5%-3.5% |
| Median mule inbound computed `fan_in_1h` | > 5 |
| Anti-stub | computed `fan_in_1h` ≠ knob copy; variance > 0 |
| Causal clock | features at t ignore future edges |
| APP flags | false/null on non-APP rows except explicit genuine noise |
| `liveness_score` / `doc_consistency` | NULL on post-onboarding payments |
| 50k-row smoke | < ~5 min laptop (`slow` marker). Fail if still a 1-row stub |

HTTP `fidelity.pass` is true only if **both** fidelity and verifier pass.

PSI vs own priors ≠ PSI vs live UPI.

---

## 10. Population vs canary vs calibrate

Keep paths in `apps/api/routes/generate.py`. Do not add `/sim/run` as a third product.

### Population — `POST /generate/population`

Always one world from current priors, then **all** generate-eligible injectors unless `vector_id` filters the family. Quiet world is still full.

Defaults in runner: `world_seed=42`, `n_customers=2400`, `n_merchants=120`, `sim_days=90`, `pin=false`.

Response: `run_id`, parquet path, split path, sidecar path, fidelity pass/fail (PSI, fraud rate, mule fan-in median, reasons), **row counts by `label_family`**. No `simulatable_signals` in the body.

### Canary — `POST /generate/canary`

One world, one chain of synthetic accounts. Stages **T09 → T11 → T13 → T02** write onto the **same ledger in time order**, not four fresh stubs.

Campaign pin: `packages/catalog/campaigns.py` `fincen-fin-2024-alert004`  
vector_ids: `t09-deepfake-vkyc`, `t11-identity-farming`, `t13-upi-impersonation-app`, `t02-mule-fan-out`  
lifecycle: onboarding_kyc → account_access_ato → payment_initiation → disbursement_mule  
primary: `t13-upi-impersonation-app`

Default `sim_days: 180` so catalog `seasoning_days: 150` can run, then APP + mule cash-out still have calendar. Do not silently pretend 76 days is 150. Knobs **pinned**. UI must show `sim_days`.

Single-vector canary (db + `vector_id`, `canary_eligible`) reuses population with `pin=True`.

### WorldCalibrator — `POST /generate/calibrate-world`

Not Identify Job B. No `POST /identify/calibrate-world`. Fixture HTML in-repo only. No live NPCI/Tavily in this pass.

May fill: P2M category mean tickets, P2P/P2M split, UPI caps, when the page actually has the number.  
Must not fill: hour-of-day, salary, rent unless a cited table exists.

Numeric gate: if the page has volume and value, stored average must match value/volume within 5%. Else abstain. PDF-only → abstain; keep last approved priors. HITL approve/reject. Reject keeps seed.

---

## 11. APP flag ablation (Phase G, not Defend)

`packages/sim/ablation.py`. Same sklearn HistGradientBoosting twice on one seeded ledger: once with the four APP columns, once with them zeroed. Time cut last third of **that run's** calendar. Report ROC-AUC and average precision on APP. If APP detection collapses without the flags, that is a documented lab result, not a silent cheat.

`is_authorized_push` and `label_family` are not train inputs in that smoke. Not India prevalence. Not proof of live UPI. See [`Docs/generate_app_ablation.md`](../../Docs/generate_app_ablation.md).

---

## 12. What Generate does not build

Live NPCI, PDF pipeline, SDV/CTGAN/SMOTE, Cat 4 public API, AuthGate/Brake as the product, Redis/ARQ, LangGraph generate subgraph, Plan 02 LLM identity proposer, T06 merchant cycles, T07 CNP as generated traffic, dark-web scrape, exploit write-ups.

Named in catalog, not generated: card/3DS/network vectors, T06, T07, T20-T23.

---

## 13. Hand-off to Defend

Generate emits a labeled `gff.txn.v1` ledger + train Parquet + sidecar + fidelity badge.

Defend (not this pack) fits a GBDT on allowlisted columns, chooses a threshold on train inner validation, scores a **separate** holdout world once, maps score + family + rules → Brake action. Misses may return as Identify tickets or capped oversample. Generate must not write Loop M extras onto reserved holdout seeds `{43, 46, 47, 48, 49}`.

Do not regenerate seed 48. Do not claim Generate metrics as Defend photography.

---

## 14. Tests that define "done"

CI, not a notebook. Plan 08 lock 5:

1. Train Parquet columns ⊆ allowlist; denylist absent
2. `label_family` never equals `T01`…`T24`
3. Independent `fan_in_1h` recompute ≠ catalog YAML copy; median mule inbound > 5
4. `liveness_score` / `doc_consistency` NULL on post-onboarding payments
5. APP flags false/null on non-APP rows (except explicit genuine noise)
6. Canary: one 180-day world, four stages in order, shared party ids, knobs pinned
7. Population `vector_id=t13`: quiet world exists; only `app_fraud` extra family plus `normal`; many APP victims
8. PSI amount and hour vs this run's priors; seed 42 reproducible
9. Causal: feature at t uses only `time < t`
10. Seasoning clamp metadata on 90d population vs 150d catalog T11
11. 50k-row smoke under ~5 min (`slow`; fail if 1-row stub)
12. Ablation smoke: APP metric reported with flags zeroed

**Not done if:** knobs in train columns; WorldCalibrator fills hours from fraud news; `label_family` is `T13`; liveness copied onto every payment; T12 collapsed into `identity_burst`; model only wins because `is_authorized_push` leaked in; canary is four independent stub JSONs.

---

## 15. Gaps to say out loud

Synthetic flags ≠ SDK. Laptop ≠ NPCI volume. No real-fraud holdout. T06/T07/T20-T23 named only. Hours are assumptions. Lab fraud rate ≠ India prevalence. PSI vs own priors is sampler QA, not "this is live UPI."
