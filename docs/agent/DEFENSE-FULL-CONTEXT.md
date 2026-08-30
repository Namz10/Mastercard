# Defense full context pack

**Purpose:** single context dump for defense work — simulated world, units, current champion metrics, validation protocol, and live architecture. Feed this file as-is. Do not mix museum seed-43 numbers with v1 seed-46/47/48.

**Canonical siblings (do not contradict):**

| Doc | Role |
|-----|------|
| [`docs/submission/FROZEN-MODEL.md`](../submission/FROZEN-MODEL.md) | Frozen champion numbers only |
| [`docs/submission/DEFENSE.md`](../submission/DEFENSE.md) | Official technical defense |
| [`docs/submission/HANDOFF.md`](../submission/HANDOFF.md) | Pickup / chronology |
| [`docs/agent/final-v1-metrics.md`](final-v1-metrics.md) | Exhaustive scorecard + SAML-D |
| [`Docs/defense_architecture.md`](../../Docs/defense_architecture.md) | Design spec (target architecture) |
| [`VALIDATION.md`](../../VALIDATION.md) | Lab validation spec (G1–G7, metric definitions) |
| [`Docs/ARCHITECTURE.md`](../../Docs/ARCHITECTURE.md) | Identify → Generate → Defend lab |
| [`Docs/plans/08-generate-world-build.md`](../../Docs/plans/08-generate-world-build.md) | World SSOT |

**Product one-liner.** KillChain Atlas catalogs 24 techniques → ShadowRail simulates a quiet UPI-like world then injects labeled fraud → AuthGate scores at event time `t` from causal `G(t−)` → Brake maps score + family + rules to an action → LoopGovernor may retrain only if independent holdouts do not get worse.

This is a **research lab prototype** for Mastercard Innovation Challenge @ GFF 2026. Not live UPI. Not India prevalence. Not production AuthGate.

---

## 0. What you must not mix

| Forbidden mix | Why |
|---------------|-----|
| Seed **43** museum metrics with seed **48** photography | Different populations; `v1-train-46__gtest` is byte-identical to `v1-gtest-48`, not an extra holdout |
| Default `detect_thr` ~0.000546 (~8% genuine FPR) with frozen op 0.9152 | Default is training-time; headline is FPR-constrained |
| Internal 98.7% recall with SAML-D 1.96% TPR | Different feature spaces; SAML-D stubs app/device/stamps |
| `genuine_fp` with `genuine_fp_over_eval` | First is FP / n_normal; second is predicted-positive rate over all eval rows |
| Family **AP** with family **recall @ threshold** | ATO eval-fold AP 0.056 vs recall 88.7% at frozen op — different questions |
| Pareto envelope (threshold swept on G-test) with protocol freeze (threshold from inner_val only) | Both internal; only freeze is “threshold not chosen on test” |
| Cost sketch with Indian ₹ loss | Unit is `lab_not_india` |
| Technique IDs `T01`…`T24` as model labels | Train target is `label_family` only |
| `packages/config/scale.py` seeds 42/43/44/45 as v1 photography | Those are museum scale constants; v1 uses **46/47/48/49** |

---

## 1. The world (what exists at payment time)

### 1.1 What the world is

A **deterministic, event-driven, Poisson** synthetic UPI-like ledger. Quiet life is generated first. Fraud is a **constrained perturbation** of that baseline, not a separate dataset glued on.

Code: `packages/sim/world.py` → injectors in `packages/sim/inject/` → causal features in `packages/sim/features.py` → train export in `packages/sim/export.py`.

```
data/priors.json
    → generate_quiet_world(seed, n_customers, n_merchants, sim_days)
    → apply_mix (four injector families, lab oversample)
    → verifier / fidelity (PSI, anti-stub, fraud-rate band)
    → export train.parquet + split.parquet + sidecar.json
```

LLM never writes rupees or mule edges. Amounts and graph edges come from **code**.

### 1.2 Frozen v1 population scale

| Knob | Value | Notes |
|------|------:|-------|
| Customers | **2400** | `VID-SIM-C-NNNNNN` |
| Merchants | **120** + **3 hubs** | Merchants `VID-SIM-M-*`; hubs `VID-SIM-HUB-001/002/003` |
| Calendar | **90 days** | `t0 = 2024-01-01T00:00:00+00:00` |
| Rail on every row | `upi_like` | IMPS hop exists only as mule injector rail-switch, not a second product |
| Currency | `INR` | Amounts stored as integer **paise** |
| Schema | `gff.txn.v1` | Thin envelope; GSTIN+3DS+VPA+chat embedding on every row is forbidden |

Canary (not the v1 photography world): one 180-day chain, seed historically 42, stages T09→T11→T13→T02 on shared `VID-SIM-CHAIN-*`. Knobs **pinned** (no ±50% jitter). Seasoning 150 days honored. Do not silently truncate to 76 days.

### 1.3 Frozen v1 worlds / seeds

| Run ID | Seed | Role | Touch? |
|--------|-----:|------|--------|
| `v1-train-46` | 46 | Train world + Loop M extras appended | Fit only |
| `v1-gdev-47` | 47 | Promote / reject gate | Loop M, Loop T mine/gate, ECE, permutation |
| `v1-gtest-48` | 48 | **Photography holdout** | **Never promote, never retune, never regenerate** |
| `v1-gtest-49` | 49 | One-shot confirmatory after a loop ends | Once |
| Museum `world_seed=42/43/44` | 42/43/44 | Old VALIDATION.md names (G-train/G-test/G-dev) | Do not mix into v1 claims |

`RESERVED_WORLD_SEEDS = {43, 46, 47, 48, 49}` in `packages/eval/fit.py`. Loop M extra rows must not be generated onto those seeds as a G-test.

**Do not regenerate seed 48.** Rescore frozen models only.

### 1.4 Party ID namespaces

| Prefix | Meaning |
|--------|---------|
| `VID-SIM-C-` | Customer (payer / P2P payee) |
| `VID-SIM-M-` | Merchant |
| `VID-SIM-HUB-` | Legitimate high-fan-in hub (payroll / marketplace / bill-pay). **Hard negative for mule.** Brake skips `mule-fan-in-burst` on these payees |
| `VID-SIM-U-` | Mule payee (entity holdout prefix) |
| `VID-SIM-APP-` | APP-related synthetic party (entity holdout prefix) |
| `VID-SIM-CHAIN-` | Canary shared accounts |
| `evt-NNNNNNNNNN` | Quiet/injected event IDs |
| `evt-lm-*` | Loop M extra event IDs (train only) |

Never real PAN / VPA / Aadhaar.

### 1.5 Personas (quiet life)

Four personas. Weights and Poisson rates from `data/priors.json`:

| Persona | Weight | Txn / day (λ) | Spend buckets | KYC |
|---------|-------:|--------------:|---------------|-----|
| `salaried` | 0.35 | 1.1 | grocery, utilities, telecom, p2p, fuel | tier2 |
| `kirana_shopper` | 0.30 | 2.0 | grocery×2, utilities, p2p | tier2 |
| `small_biz` | 0.15 | 3.2 | fuel, telecom, utilities, p2p, grocery | tier2 |
| `young_urban` | 0.20 | 1.7 | fast_food, telecom, p2p, grocery | **tier1** |

Each customer gets a known-payee list: merchants from their buckets + 2–4 friend customers + with p=0.45 one hub. ~4% of customers get a **device upgrade** mid-run (`is_new_device` can fire on genuine traffic).

P2M share = **0.62**. Hour-of-day is a **stated assumption** (bimodal peaks 10–12 and 19–22), not a cited NPCI hourly table.

### 1.6 Amounts and caps (units)

**Unit of money in the ledger: `amount_minor` = integer paise.** ₹1 = 100 paise.

| Cap / prior | Value | Human |
|-------------|------:|-------|
| `txn_min_minor` | 100 | ₹1 |
| `txn_max_minor` | 10_000_000 | ₹1,00,000 |
| `day_max_minor` | 10_000_000 | ₹1,00,000 / day / payer |
| Lognormal σ | 0.55 | Mean-matched to category mean, then rounded to integer rupees via paise |
| Customer opening float | uniform 15e6–40e6 paise | ₹1.5L–₹4L |
| Merchant opening | 80e6 paise | ₹8L |
| Hub opening | 500e6 paise | ₹50L |

Category **means** (public aggregate `value/volume`, **not** medians, **not** live UPI rows):

| Category | Mean ₹ | Provenance |
|----------|-------:|------------|
| grocery | 214 | NPCI-style P2M illustration |
| fast_food | 113 | same |
| utilities | 1,345 | same |
| fuel | 620 | same |
| telecom | 399 | same |
| p2p | 850 | same |
| salary | 28,000 | **assumption** |
| rent | 12,000 | **assumption** |

Wallet: amount ≤ 0 rejected; use-before-create rejected; insufficient float = skip that payment (no Western overdraft). Daily cap: skip if `spent_today + amount > day_max`. Mule out-same-tick is deferred.

**Forbidden claim:** “amounts match live UPI.” Allowed: “lognormal mean-matched to approved public aggregates; PSI vs our own priors is sampler QA.”

### 1.7 Clock and causality

- Events are **not** “every agent every 15 minutes.” 15 min is a **velocity bin**, not an actor tick.
- Feature at payment `t` uses **only** edges with `timestamp < t` (`G(t−)`). The current payment is snapshotted **before** it is applied to running state, then applied.
- Running state is O(n) per-account deques (1h / 24h / 7d / 30d windows), not O(n²) full-ledger scans.
- `hours_since_prev_txn` default if never paid: **168.0** (one week).
- `hours_since_payee` default if never paid that payee: **720.0** (30 days).
- `amount_vs_p30` / `amount_vs_7d_mean` default if no history: **1.0**.

Leakage test: full-graph vs `G(t−)` must **diverge** on easy data. If they match, features are leaking.

### 1.8 Label families (train targets)

Exactly six. **Never** `T01`…`T24`.

| `label_family` | How it gets on a row | Economic class (sidecar / Brake, **not** in X) |
|----------------|----------------------|-----------------------------------------------|
| `normal` | Quiet Poisson world | — |
| `mule` | graph_mule injectors T01–T05 | mule |
| `identity_burst` | identity_trajectory T11 after seasoning | identity farming |
| `ato` | identity_trajectory T12 device-hash shift | stolen credential |
| `app_fraud` | app_session T13+ (victim authorized) | APP / scam |
| `invoice_fraud` | doc_beneficiary T24 (checksum **passes**, wrong account) | BEC / invoice |

T12 must be `ato`, not `identity_burst` — otherwise Brake cannot decline ATO while holding APP.

### 1.9 Fraud mix (lab oversample, not India)

Target fraud **rate of rows**: ~**2%** (clamped 1–3%; fidelity gate **0.5%–3.5%**). India UPI fraud prevalence is sub-0.01%; write-up must say lab oversample.

Of fraud rows (allocation, not a promise of exact counts after verifier rejects):

| Family | Share of fraud rows |
|--------|--------------------:|
| mule | 40% |
| identity_burst | 25% |
| ato | 5% |
| app_fraud | 20% |
| invoice_fraud | 10% |

Mule sub-variants (same engine, different shapes): `funnel_fast` (majority, `fan_in_1h` median must be > 5), `funnel_slow`, `smurf` (amounts × `smurf_cap_ratio`≈0.85 under cap), `hop` (UPI-like → IMPS-like), `dust` (many tiny outbound), then `cashout` TTL fan-out to a sink.

Population jitter: catalog knobs ±50%, clamped. Canary: **pin**, no jitter.

### 1.10 Injector knob centers (never copied into train X)

These YAML/JSON numbers are **range centers**. Train columns are **computed** windows. Anti-stub gate: `fan_in_1h` on the ledger must not equal the knob on every mule row.

| Injector | Knob | Center |
|----------|------|-------:|
| graph_mule | `fan_in_1h` | 18 |
| graph_mule | `fan_out_ttl_hours` | 4.0 |
| graph_mule | `smurf_cap_ratio` | 0.85 |
| graph_mule | `mule_account_age_days` | 3 |
| identity_burst | `seasoning_days` | 150 (clamped to `sim_days−14` on 90d worlds; metadata `seasoning_clamped`) |
| identity_burst | `seasoning_txn_count` | 45 (actual Poisson count recorded; fail if burst never happens, not if count ≠ 45) |
| ato | `device_hash_shift` | true |
| app_session | `call_active_flag` | true |
| app_session | `copy_paste_payee_flag` | true |
| app_session | `pause_ms` | 1800 |
| app_session | `urgency_pressure` | 0.85 |
| app_session | `new_payee` | true |

APP inject: many victims after day 12 (90d world), same device, new payee, amount large vs **that victim’s** p30. Session flags **only on those rows**.

Invoice: GSTIN checksum **passes in code**; `beneficiary_changed=True`; amateur checksum-fail is **excluded** (not the interesting case).

### 1.11 Genuine-world noise (hard negatives baked into quiet life)

These exist so the model cannot treat every stamp as fraud:

| Noise | Rate | Effect |
|-------|-----:|--------|
| Weak APP-shaped flags on normals | 2% | call p=0.15, paste p=0.25, `pause_ms` 0–800, `urgency_pressure` U(0,0.35) |
| Paste-only on normals | 0.4% | paste true, pause 200–1200, no call, urgency 0 |
| Invoice-shaped payload on `small_biz` normals | 0.6% | `beneficiary_changed=True`, checksum ok, lookalike false |
| Device upgrade | ~4% of customers | genuine `is_new_device` |
| Hub fan-in | structural | legitimate `fan_in_1h` can exceed mule rule threshold 6 |

H4 tried **extra** 2% APP stamp noise on a new seed and died on `inner_val.ato=0`. Preflight now blocks empty family floors. Do not re-run H4.

### 1.12 Fidelity gates (Generate correctness)

| Gate | Pass |
|------|------|
| Amount PSI vs `priors.json` buckets (normal rows) | PSI < 0.1 |
| Hour-of-day PSI vs bimodal prior | PSI < 0.15 |
| Fraud rate | 0.5%–3.5% |
| Median mule inbound `fan_in_1h` (computed) | > 5 |
| Anti-stub | computed `fan_in_1h` ≠ knob copy; variance > 0 |
| Causal clock fixture | features at t ignore future edges |
| APP flags | false/null on non-APP rows (except the explicit genuine noise above) |
| `liveness_score` / `doc_consistency` | NULL on post-onboarding payments |
| 50k-row smoke | < ~5 min laptop (`slow` marker) |

PSI vs own priors ≠ PSI vs live UPI. KS p-value is rejected as a gate (n too large).

---

## 2. Units, columns, and what the model sees

### 2.1 Feature snapshot (causal, computed before the current edge is applied)

From `FeatureComputer.snapshot_and_apply`:

| Column | Type / unit | Definition |
|--------|-------------|------------|
| `account_age_days` | int days | `floor((t − payer.created_ts).days)`, ≥ 0 |
| `payee_history_count` | int | Prior payments this payer → this payee (**before** current) |
| `is_new_payee` | bool | `payee_history_count == 0` |
| `is_new_device` | bool | current `device_hash` ≠ payer’s stored hash; then hash updates |
| `amount_vs_p30` | float ratio | `amount_minor / mean(payer amounts in last 30d)`; 1.0 if empty |
| `amount_vs_7d_mean` | float ratio | same over 7d |
| `fan_in_1h` | int count | inbound edges to **payee** with ts in `[t−1h, t)` |
| `fan_in_unique_payers_1h` | int | unique payer ids in that window |
| `fan_out_1h` | int | outbound edges from **payer** in 1h |
| `fan_in_24h` / `fan_out_24h` | int | 24h analogues |
| `fan_in_unique_payers_24h` | int | unique inbound payers 24h |
| `txn_velocity_24h` | int | payer outbound count 24h |
| `burst_velocity` | float | unique outbound payees in 1h (stored float) |
| `hours_since_prev_txn` | hours | since payer’s last txn; default 168 |
| `hours_since_payee` | hours | since last pay to this payee; default 720 |
| `unique_payees_7d` | float | unique outbound counterparties 7d |
| `payee_fan_out_1h` | int | **payee’s** outbound in 1h (cash-out shape) |
| `in_out_asymmetry_24h` | float | `fan_in_24h − payee_out_24h` |
| `kyc_tier` | `{tier1,tier2}` categorical | from account, not from this payment |
| `rail` | `upi_like` (constant in v1 sim) | |
| `call_active_flag` | bool | APP session; default false |
| `copy_paste_payee_flag` | bool | APP session |
| `pause_ms` | int milliseconds | typing pause; default 0 |
| `urgency_pressure` | float ~[0,1] | APP pressure; default 0.0 |
| `beneficiary_changed` | bool | invoice payload; default false |
| `gstin_checksum_ok` | bool | invoice payload |
| `lookalike_domain_flag` | bool | invoice payload |
| `liveness_score` | float [0,1] or NULL | onboarding only |
| `doc_consistency` | float [0,1] or NULL | onboarding only |

`device_hash` is used to compute `is_new_device` then dropped from train X.

### 2.2 Train Parquet allowlist / denylist

**Allowlist (export):** the columns in §2.1 that are listed in `TRAIN_ALLOWLIST` plus `label_family`. That is 28 feature columns + label.

**Denylist (CI fail if present in train parquet / model X):**  
`vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed`, `transcripts`, `is_authorized_push`, `economic_class`, `label_class`, `gstin`, `payload`.

Also never in X: `event_id`, `event_ts`, `payer`, `payee`, `amount_minor`, `campaign_id` (those live in `split.parquet` for folds only).

### 2.3 Rule-hit bits (features, not the action)

After export, fit attaches one binary column per live rule: `rule__<id>`. v0 has **9 rules** → **9 bits**. Champion `raw_columns` count = **37** = 28 allowlist features + 9 rule bits.

Rules evaluate **row values**, not key presence. Forbidden as rule predicates: injector knobs (`smurf_cap_ratio`, `seasoning_days`, …), denylist fields, `is_authorized_push`.

Live v0 rules (`data/rules/v0_rules.yaml`):

| id | kind | applies_to | when | min_score |
|----|------|------------|------|----------:|
| `call-and-paste-new-payee` | hard_flag | APP | call ∧ paste ∧ new payee | 0.72 |
| `new-payee-large-new-device` | hard_flag | ATO | new payee ∧ new device ∧ amount_vs_p30 ≥ 2 | 0.68 |
| `mule-fan-in-burst` | hard_flag | mule | fan_in_1h ≥ 6 | 0.65 |
| `invoice-beneficiary-swap` | hard_flag | BEC | beneficiary_changed ∧ gstin_checksum_ok | 0.70 |
| `smurf-under-cap` | nudge | mule | fan_in_1h ≥ 4 ∧ amount_vs_p30 ≤ 1 | 0.45 |
| `rail-hop-burst` | nudge | mule | fan_out_1h ≥ 4 | 0.40 |
| `seasoning-burst` | nudge | ATO | burst_velocity ≥ 4 ∧ account_age_days ≥ 7 | 0.50 |
| `pause-paste-session` | nudge | APP | pause_ms ≥ 1500 ∧ paste | 0.40 |
| `calm-down-known-usual-device` | calm_down | genuine | known payee ∧ same device ∧ 0.4 ≤ amount_vs_p30 ≤ 2.5 | −0.2 |

Three kinds:

- **hard_flag** — can force a serious Brake action (subject to `score >= min_score`).
- **nudge** — never declines by itself; bits still enter the GBDT.
- **calm_down** — if a calm-down hits and **no** hard_flag, Brake **allows** (kirana / rent).

Hub exemption: if payee starts with `VID-SIM-HUB-`, `mule-fan-in-burst` is stripped **before** Brake. Model scores unchanged.

### 2.4 Score definition (the number everything else hangs on)

Estimator: sklearn `HistGradientBoostingClassifier`, **multiclass** over  
`{normal, app_fraud, ato, identity_burst, invoice_fraud, mule}`.

```
fraud_score = 1 − P(normal)
pred_family  = argmax_c P(c)
detect       = fraud_score >= detect_thr
```

Optional **per-class isotonic** calibration on an inner A/B split (`calibration.stage1_binary=true`). Isolation Forest may bump “looks new” → extra confirmation (`isolation_forest.enabled_default=true` in recipe) on stamp-free numeric columns; abort if genuine notify rate > 5%.

Stage 1 recipe (`models/features.json`): `max_depth=3`, `max_iter=80`, `learning_rate=0.08`, `class_weight=balanced_from_this_run`, `random_state=42`, `early_stopping=false`. Categorical: `rail`, `kyc_tier` via `OrdinalEncoder(unknown=-1)`.

**Two thresholds:**

| Name | Typical value | Meaning |
|------|--------------:|---------|
| `detect_thr` | **0.9152 frozen** / 0.000546 legacy default | Score ≥ this → predicted positive for metrics / Brake elevation |
| `act_thr` | 0.5 | Brake family-hit floor (`DEFAULT_ACT_THR`) |

Do **not** headline the legacy default (~8% genuine FPR, ~100% recall).

### 2.5 Brake actions (the product)

Code: `packages/eval/brake.py`. Inputs: `pred_label_family`, `score`, rule hits, payee.

Priority order:

1. Mule family @ `act_thr` **or** mule hard_flag → `mule_credit_restrict` (restrict **incoming** on payee).
2. Calm-down and no hard_flag → `allow`.
3. APP → `hold` if hard or score ≥ 0.65 else `notify`. **Never silent decline** (APP is victim-authorized). If a decline would fire, rewrite to `hold`.
4. Invoice → `hold` if hard or score ≥ 0.5 else `case`.
5. ATO → `decline` if hard or score ≥ 0.5 else `step_up`.
6. `identity_burst` → `step_up` if score ≥ 0.5 else `notify`.
7. Else score ≥ 0.65 → `notify`.
8. Else `allow`.

Enum: `allow | notify | step_up | hold | decline | mule_credit_restrict | case`.

### 2.6 Cost sketch units

Not rupees. Relative lab cost per scored row:

```
expected_cost = 10 × FN_rate + (1×n_notify + 3×n_hold + 8×n_decline) / n_total
```

`FN_rate = n_fn / n_fraud`. Unit field: `lab_not_india`. Missing Brake actions in the FP histogram contribute 0 and log `cost_sketch_action_missing:*`.

### 2.7 Metric units (lead with these)

| Metric | Unit | Definition |
|--------|------|------------|
| **PR-AUC / AP** | [0,1] | `average_precision_score`; family AP uses `P(family)` vs one-vs-rest, **independent of `detect_thr`** |
| **Binary AP** | [0,1] | AP of `fraud_score` vs `y != normal` |
| **Genuine FPR** | fraction | `FP / n_normal` where FP = predicted pos among `label_family==normal` |
| **Recall / TPR** | fraction | TP / n_fraud (all non-normal as positives unless family-restricted) |
| **Precision** | fraction | TP / predicted pos |
| **TPR @ FPR x%** | fraction | max recall s.t. genuine FPR ≤ x; threshold from **inner_val** for claims, or swept on eval for diagnostic Pareto |
| **Entity mule recall** | fraction | mule **payee accounts** with ≥1 inbound flagged (not edge-level) |
| **ECE** | [0,1] | calibration; <0.05 well-calibrated |
| **Latency** | ms/row | in-process `predict` on 1k batch; p50 < 5 ms, p99 < 50 ms **inference only** |
| **PSI** | dimensionless | distribution shift vs priors |
| **n_pos_not_comparable_below** | 30 | family AP with fewer positives is not comparable |

**Never lead with:** accuracy, balanced accuracy on 50/50 mix, ROC-AUC as headline, “we beat production.”

Why PR-AUC: lab fraud ~1–3%; majority classifier gets high ROC-AUC while missing fraud.

---

## 3. Current champion (use this model only)

| Field | Value |
|-------|-------|
| `model_run_id` | **`v1-train-46__loopm-train`** |
| Status | Provisional v1 champion |
| `model_freeze_id` | `e2f6cf866ddc8f053218e2d9bd460431c69a1d7e140effb1f88ddcd6dd55d009` |
| Estimator | `HistGradientBoostingClassifier` |
| Features | 37 raw columns (28 + 9 `rule__*`) |
| Train | `v1-train-46` + Loop M family extras |
| Promote gate | `v1-gdev-47` |
| Photography | `v1-gtest-48` (frozen) |
| Confirmatory | `v1-gtest-49` (one shot) |
| Frozen `detect_thr` | **0.9151932016993464** (report **0.9152**) |

**Rejected — do not deploy or headline:**

| `model_run_id` | Why |
|----------------|-----|
| `v1-train-46__hn-train` | Generic hard negatives: identity_burst AP 0.958→0.364, cost ~40× |
| `v1-train-46__fpr-v2` | FPR-only Optuna: identity AP −8%, cost ~300× |
| `v1-train-46-stage2` | AP Optuna worse than Stage 1 on G-test |

Load: `load_champion("v1-train-46__loopm-train")`. If `features.json` hash ≠ freeze id, scoring must refuse (`RecipeHashMismatchError`).

### 3.1 Two internal numbers (do not collapse)

**A. Protocol freeze (defensible operating point)**  
Threshold: max recall on **inner_val of train-46** (42,399 rows, 818 fraud) s.t. genuine FPR ≤ 0.1%. Evaluated **once** on the **time-cut eval fold** of gtest-48.

| Metric | Frozen op | Legacy default |
|--------|-----------|----------------|
| `detect_thr` | **0.9152** | 0.000546 |
| Genuine FPR | **0.0318%** (57 / 179,049) | 4.00% |
| Recall | **98.52%** (3,917 / 3,976) | 99.97% |
| Precision | **98.57%** | 35.69% |
| Binary AP | 0.9985 | 0.9985 |

Confusion: TN 178,992 · FP 57 · FN 59 · TP 3,917.

Family recall @ 0.9152 (eval fold):

| Family | n | AP (ranking) | Recall @ op |
|--------|--:|-------------:|------------:|
| app_fraud | 726 | 0.990 | 98.48% |
| ato | 150 | **0.056** | **88.67%** |
| identity_burst | 1,018 | 0.984 | 98.53% |
| invoice_fraud | 326 | 1.000 | 100% |
| mule | 1,756 | 0.994 | 99.09% |

ATO AP on 150 eval positives is a ranking metric; do not quote it as “ATO fails.” Full-world ATO AP is 0.533.

Actions @ frozen op (eval fold): allow 177,906 · notify 1,782 · mule_credit_restrict 2,505 · hold 761 · step_up 64 · decline 7. Cost sketch **0.149**.

**B. Pareto envelope (slide / frontier — threshold swept on G-test scores)**  
Full `v1-gtest-48`. Headline: **98.7% recall @ 0.1% genuine FPR**, **99.8% @ 1%**.

H5 5-point (`pareto_gtest48.json`):

| Genuine FPR cap | Stage 1 recall | Loop M recall | Loop M realized FPR |
|----------------:|---------------:|--------------:|--------------------:|
| 5% | 96.25% | **99.95%** | 4.99% |
| 2% | 94.77% | **99.89%** | 1.99% |
| 1% | 87.95% | **99.81%** | 0.99% |
| 0.5% | 84.69% | **99.66%** | 0.49% |
| 0.1% | 83.15% | **98.68%** | 0.100% |

H5b confirmatory (`pareto_genuine_fpr.json`): 99.57% / 99.47% / **98.67%** recall at 1% / 0.5% / 0.1%; identity_burst recall 98.90% and mule 99.11% at 0.1%.

### 3.2 Full-world photography (`v1-gtest-48`, all rows)

Ranking (AP) does not use `detect_thr`. Default-op FPR ~8% must **not** be the slide FPR.

| Metric | Loop M | Stage 1 |
|--------|--------|---------|
| Binary AP | **0.996** | 0.879 |
| identity_burst AP | **0.967** | 0.337 |
| mule AP | **0.995** | 0.996 |
| invoice_fraud AP | 1.000 | 1.000 |
| app_fraud AP | 0.983 | — |
| ato AP | 0.533 | 0.546 |
| Genuine FPR @ default op | 8.07% | 8.79% |
| Recall @ default op | 99.99% | 95.20% |
| Cost @ default op | **0.011** | 0.486 |
| Without stamps AP | **0.844** | 0.717 |
| Without app flags AP (identity proxy) | 0.242 | — |

Full-world positives: app 1,572 · ato 395 · identity_burst 1,542 · invoice 747 · mule 3,162 · normal 387,536. Total events ~394,954.

Default-op actions: allow 383,922 · mule_credit_restrict 4,468 · notify 4,104 · hold 1,980 · decline 381 · step_up 99.

Hubs after exemption: hub `mule_credit_restrict` = **0** on gtest-48 and gtest-49 (was 31 before H2).

### 3.3 Ablation (frozen champion, zero columns at score time, no retrain)

H9 on gtest-48, Δ binary AP vs 0.996:

| Group zeroed | Δ AP | Columns (conceptually) |
|--------------|-----:|------------------------|
| temporal | **−0.313** | hours_since_*, account_age_days |
| graph | **−0.308** | unique fan-in, in_out_asymmetry |
| app/session flags | −0.117 | call, paste, pause, urgency |
| velocity | −0.068 | burst, fan in/out windows |
| merchant/amount | −0.060 | amount_vs_p30/7d |
| stamps | −0.040 | beneficiary / GSTIN / lookalike |

Obsolete **0.579 identical-across-models** figure was a toy-retrain bug. Never cite it. Per-model without-stamps: Stage 1 0.717 / Stage 2 0.549 / Loop M **0.844**.

APP without session flags is expected to collapse. That is an honest SDK-dependency finding, not a hidden failure.

### 3.4 SAML-D external (separate evaluation — not 98.7%)

Replay via `FeatureComputer` on last 1/3 calendar (~3.14M rows). App/device/stamp features **forced false**. Families **never mapped:** `app_fraud`, `ato`, `identity_burst`. Rail constant `upi_like`. Amount CSV × 100 → paise.

| FPR cap | TPR |
|--------:|----:|
| 0.1% | **1.96%** |
| 0.5% | 3.05% |
| 1.0% | 3.91% |

Diagnosis **Case A:** 98.2% of SAML-D positives score below internal 0.915; median pos ≈ 0.0004 ≈ median neg. Not a threshold bug. Do not retrain on SAML-D labels. Mapped eval positives: mule 3,084 · unmapped 369 · invoice 22 · normal 3,141,065.

---

## 4. Validation methods (how a number is allowed to exist)

### 4.1 Seven hard gates (G1–G7)

Any result that fails a gate is **exploratory**, not a claim.

| Gate | Rule | How tested |
|------|------|------------|
| **G1 No future** | Features at t from `timestamp < t` only; no generator ids, no post-payment disputes | Causal vs full-graph leakage test |
| **G2 Split** | Time cut (first 2/3 calendar) **plus** entity holdout; **no** `train_test_split(shuffle=True)` | `split.parquet` has `event_ts`; mule payees `VID-SIM-U-*` disjoint |
| **G3 LLM extractor** | LLM not on live path; if used, freeze prompt and ablate missing/abstain | Live score is HGB + rules only |
| **G4 Delayed labels** | Approval ≠ genuine; store `label_source`, `label_ts`, `label_lag_hours`; sim labels marked | Sidecar |
| **G5 Baseline** | Candidate vs current champion at **same alert budget**: AP, recall, genuine FPR, volume, friction-by-action, latency, family stability | Promote JSON |
| **G6 Rollback** | Previous artifact kept; canary regression restores prior | `model_freeze_id` |
| **G7 Honest coverage** | Each of 24 techniques is exactly one of `built / case_only / offline_loop / named_gap` | Coverage table §6 |

### 4.2 Split protocol (code)

`packages/eval/split.py`:

- **Outer eval** if event is in last 1/3 of configured `sim_days` horizon **or** payer/payee in holdout set.
- Mule holdout frac **0.30** of mule payee ids; customer holdout frac **0.15**.
- **Inner_val** = last **20%** of **train** calendar (never shuffled). Optuna + `op_threshold` live here only.
- Inner_val further split A/B: calibrators fit A, scores/threshold evaluate B.
- Fold floor: `INNER_FOLD_FLOOR = 15` positives; E2 preflight blocks `inner_val.ato=0`.
- Family with `n_pos < 30` is `not_comparable`.

**Headline metrics:** G-test seed 48. **G-eval** (same-run outer holdout) is diagnostic only after Ticket 3 — do not set `detect_thr` from it. **G-dev 47** is the only promote/reject world.

### 4.3 Operating-point protocol

```
inner_val (train-46) → max recall s.t. genuine_fp ≤ cap → freeze detect_thr
        ↓
evaluate once on gtest-48 eval fold (protocol freeze)
        ↓
optional: sweep scores on full gtest-48 (Pareto envelope, diagnostic)
```

`max_recall_at_genuine_fpr` sorts scores descending and walks until `FP_normals / n_normal` would exceed the cap.

Recipe also lists `operating_point_fpr: 0.01` and `tpr_at_fpr: [0.001, 0.005, 0.01]` — 1% is the recipe default cap; **0.1% is the frozen deployment reference**.

### 4.4 Loop M (what actually produced the champion)

Class-conditional training-set augmentation with a hard gate. Not GAN. Not generic oversampling.

```
Score champion on G-dev
  → pick weakest family with n_pos ≥ floor (round-1 diagnostic: ATO AP 0.54)
  → run same simulator, extras of that family only
  → append to train (cap extra_row_cap_frac = 0.15 of train; timestamps jittered into train calendar; new evt-lm-* ids)
  → refit same HGB class
  → accept on G-dev iff:
        family AP ≥ prior − 0.05
        other families relative drop ≤ 5%
        genuine FPR ≤ prior + 0.02   (loop_m.genuine_fpr_eps; NOT the 0.002 Loop T number)
        cost / canary not collapsed
```

Mine/harvest **never** from G-test seed 43 or 48. Recursive H7: max 3 rounds, each judged on gdev-47, gtest-49 once at end. Round 2 was **not** run before freeze. Do not start it against gtest-48.

Loop M extras → **train only**. G-test frozen. Evasion mix cap 15%. Trust tags: `human_gold` / `synth_verified` / `loop_evasion`.

### 4.5 Loop T (rules from trees)

Mine + tree fit on G-dev 47 `gdev_mine` only. FPR/incremental recall on disjoint `gdev_gate`. `rule_promote_genuine_fpr_eps = 0.002`. HITL approve required. Drafts stay out of `load_v0_rules()` until approve. LLM may title a form; **cannot change `when`**.

### 4.6 Optuna

TPE, inner_fit/inner_val **only**. Never G-dev, G-test, or SAML-D. Search: `learning_rate`, `max_iter`, `min_samples_leaf`, `l2_regularization`, `max_bins`, and **either** `max_leaf_nodes` or `max_depth`. `n_trials` 40 (10 in CI). **Optuna generates candidates; gates select the champion.** Stage 2 and H5c both lost those gates.

### 4.7 What failed (keep in the ledger)

| ID | Intervention | Result | Lesson |
|----|--------------|--------|--------|
| H6 | Top-500 high-score normals → retrain | FPR down, identity AP collapse, cost ~40× | 91% of “hard” normals were `is_new_payee`; identity_burst is fan-in/burst (`fan_in_1h`≈58) |
| H5c | FPR-constrained Optuna | Tiny default FPR, worse Pareto, identity −8%, cost ~300× | FPR-only objective repeats H6 |
| H4 | Extra stamp noise on normals | Could not fit (`inner_val.ato=0`) | Preflight fold floors |

Promote rule: FPR-constrained recall → mule ranking → frozen ablation → cost → regression gates. Winning FPR while losing identity-burst or cost = **reject**.

### 4.8 Evaluation defects already fixed (do not reintroduce)

| ID | Defect | Status |
|----|--------|--------|
| B1/B2 | Ablation refit a toy model (fake 0.579) | Fixed: zero columns on frozen champion |
| B3 | Seed-43 cache ignored `gtest_run_id` | Fixed |
| B4 | `__gtest` alias = gtest-48 | Documented |
| B5 | `genuine_fp` vs `genuine_fp_over_eval` | Documented |
| B10 | Hub fan-in treated as mule | Measured then exempted |
| E2 | Empty inner_val family | Preflight |

### 4.9 `solved` in the Atlas

A technique is `solved` only if: ≥2 Cat-4 rounds on that family, G-test PR-AUC stable (<5% relative drop), genuine FPR not worse, typology credit exact (mule fix ≠ APP win), no Cat-4 rows in G-test. **Current demo: 0 techniques `solved`.** One Loop M ≠ nine production loops.

---

## 5. Defense architecture (live path)

### 5.1 Two-speed design

| Path | Latency budget | What it uses | LLM? |
|------|----------------|--------------|------|
| **AuthGate** (live) | tens–hundreds of ms story; measured p50 < 5 ms inference | causal compact table + rules + HGB + Brake | **No** |
| **CaseScore** (after / beside) | seconds | chats, invoices, windowed graph, identity seasoning | Yes, structured JSON only |

Live order:

```
Incoming payment
  → numbers allowed at that moment (G(t−) windows, session flags already on the envelope)
  → if-then rules (hard / nudge / calm)
  → HGB sees allowlist columns + rule__ bits
  → optional IsolationForest “unknown”
  → score = 1−P(normal); action = Brake(...)
```

Do **not** put MiniLM/BERT, PageRank on the finished graph, or a GNN on the live path. Stale batch mule prestige is allowed as a **precomputed** node attribute, not computed at t on the full sim.

### 5.2 LLM contract (if used at all)

Two modes, neither can change the immediate decision:

| Mode | When | Can change live decision? |
|------|------|---------------------------|
| Offline enrichment | sim / train / eval | No |
| Case enrichment | analyst tab | No |

Extractor must emit versioned JSON (`case_signals.v1`), keep `abstained`, never overwrite amount/payee/ts, treat input as hostile. AutoML must be tested structured-only / +frozen LLM / missing LLM. If it collapses without LLM, those signals stay off the live path.

**We are not using an LM to score live payments.**

### 5.3 Closed loop catalog (names vs v1 tickets)

Identify/Generate name nine loops. **v1 Defend tickets actually run: Loop M + Loop T.** Others are named, one-shot, or UI.

| Id | Job | v1 status |
|----|-----|-----------|
| I | Catalog card → draft rule form | Named / coverage map |
| R | Flags/misses → better rules | One scripted example |
| T | Trees → readable rules | Implemented, HITL |
| M | Miss family → extra train rows | **Champion came from this** |
| A | Red vs blue (Cat 4 evasion) | Offline; no public `/attack` API |
| F | Lab vs public tables | SAML-D forensics done; transfer weak |
| C | Identify hunts empty cells | Coverage map |
| H | Analyst overrides | Named; no RLHF on trees |
| G | Fix simulator if F says so | Named |

Cat 4 attacker may patch only `X_adv` (amount, which owned mule, device rotate). `X_env` (bank-computed) and `X_forbidden` (generator ids, future edges) are not fair game. Query cap; no SHAP/weights to attacker.

### 5.4 Code map

| Stage | Path |
|-------|------|
| World | `packages/sim/world.py` |
| Inject mix | `packages/sim/inject/mix.py` |
| Causal features | `packages/sim/features.py` |
| Export | `packages/sim/export.py` |
| Rules | `packages/policy/rules.py`, `data/rules/v0_rules.yaml` |
| Fit / score | `packages/eval/fit.py` |
| Split | `packages/eval/split.py` |
| Brake | `packages/eval/brake.py` |
| Loop M | `packages/eval/loop_m.py`, `recursive_loop_m.py` |
| FPR envelope | `packages/eval/fpr_pareto.py` |
| 0.1% freeze | `packages/eval/internal_fpr_freeze.py` |
| SAML-D | `packages/eval/saml_d.py`, `saml_d_forensics.py` |
| Recipe | `models/features.json` |
| Scale constants (museum) | `packages/config/scale.py` |
| Score API | `apps/api/routes/defend.py` |

Reproduce freeze (does not retrain):

```bash
PYTHONPATH=. .venv/bin/python -c \
  "from packages.eval.internal_fpr_freeze import freeze_internal_01pct_fpr; freeze_internal_01pct_fpr()"
```

---

## 6. Coverage of 24 techniques (Gate G7)

Zero `Missing`. A generic fraud score does **not** count as `built` for a type.

### Cat 1 Network — 5 built / 2 named

| ID | Name | Mode | Live signal |
|----|------|------|-------------|
| T01 | Mule fan-in | Built | `fan_in_1h` on G(t−); catch **account** |
| T02 | Mule cash-out / fan-out | Built | TTL then sink; `fan_out_1h` |
| T03 | Smurfing under cap | Built | amounts × smurf ratio; computed windows |
| T04 | Chain-hop UPI→IMPS | Built | rail switch + burst |
| T05 | Dust / layering | Built | many tiny outbound |
| T06 | Merchant collusion | **Named gap** | no merchant-node cycle engine |
| T07 | Card / BIN testing | **Named gap** | Generate stays UPI-shaped |

### Cat 2 Identity

| ID | Name | Mode |
|----|------|------|
| T08 | Synthetic KYC | Built (onboarding liveness / doc_consistency) |
| T09 | Deepfake VKYC | Case + Named (no images) |
| T10 | Forged KYC docs | Case (fields only) |
| T11 | Long-horizon farming | Built → `identity_burst` |
| T12 | ATO device shift | Built → `ato` |
| T13 | ATO via synthetic social / APP | Built partial (session flags) |
| T14 | KYC-vendor LLM supply-chain | Named gap |

### Cat 3 Social / APP — live path is **session flags**, not chat AUC

| ID | Name | Mode |
|----|------|------|
| T15 | Vishing | Built (call + paste + new payee) |
| T16 | Push-payment scam | Built |
| T17 | Live MFA-relay **class** | Built as class; kit not published |
| T18 | Romance / long-con | Built weak + Case |
| T19 | Polymorphic phishing | Named / Case (no kits) |
| T20 | Invoice-timed impersonation | Built (session **and** Cat 5 beneficiary change) |
| T21 | Voice-clone BEC | Case / Named (no audio) |

### Cat 4 Attacking the detector — the loop, not model #5

| ID | Mode |
|----|------|
| T22 Evasion | Offline Loop A |
| T23 Poisoning | Named loop (trust tiers, 15% cap, canary veto) |
| T23b Fingerprinting | Named (query cap, no weights) |
| T23c Merchant/support bot | Named (not in public prototype) |
| T23d Agentic payment | Named / Built if `agent_initiated` on envelope |

### Cat 5 Documents

| ID | Mode |
|----|------|
| T24 Fake invoice / beneficiary swap | Built (`beneficiary_changed` ∧ checksum pass) |
| T24b Fabricated dispute pack | Case |
| T24c Amateur checksum-fail | **Excluded** |

Rough counts: ~14 built · ~5 case/offline · ~5 named gap · **0 missing**.

---

## 7. Claims we can and cannot make

### Can

- Loop M ~**98.7% recall at ≤0.1% genuine FPR** on **internal G-test seed 48** (Pareto envelope).
- Protocol freeze: **98.52% recall @ 0.032% genuine FPR** with threshold from inner_val only.
- Binary AP **0.996**, mule AP **0.995**, identity-burst AP **0.967** on that world.
- Loop M dominates Stage 1 across the measured internal FPR curve.
- Actions are family-aware (APP hold/notify, ATO decline, mule credit-restrict).
- Failed FPR-only and generic hard-negative retrains were **rejected**.
- Hubs can be exempted in Brake without retraining.

### Cannot

- “98.7% in the real world / India / production.”
- “SAML-D confirms 98.7%.” (it shows ~2% TPR @ 0.1% FPR)
- “99.8% accuracy.”
- “Zero false positives.”
- “PSI proves we match live UPI.”
- “We detect all 24 attacks.”
- “Optuna found the optimal model.”
- “Loop M is globally optimal.”
- “High-volume merchants can never be fraudulent.”
- “Cat 4 public evasion API.”
- “Beats Mastercard production.”

### Honest limits

- Simulator may not capture all real fraud; lab rate ≠ India rate.
- APP detection without issuer SDK call/paste/pause is genuinely hard (ablation).
- ATO is the weakest family (ranking).
- Invoice AP is partly **stamp skill** (payload booleans set by injector).
- Laptop HGB ≠ issuer 50 ms stack (no network, no feature store).
- Cost sketch is relative, not ₹ loss.
- HoldoutVault / BAF not a v1 scored success; SAML-D transfer is feature starvation.

---

## 8. What not to do next

1. Do not retrain against `v1-gtest-48` or pick thresholds on G-test / SAML-D.
2. Do not regenerate seed 48.
3. Do not promote a model that wins FPR but loses identity-burst AP or cost.
4. Do not re-run H6-style generic hard-negative mining (`is_new_payee` dominated).
5. Do not swap the estimator class in a last-minute pass.
6. Do not put technique ids, `is_authorized_push`, or future graph in X.
7. Do not claim internal recall as external performance.
8. If you change the SAML-D adapter: regression test, **rescore frozen champion**, compare internal 0.1% recall + family AP **before** any retrain.
9. Loop M harvest: G-dev 47 or inner-val — never photography holdout.
10. Loop T FPR ε is **0.002**; Loop M FPR ε is **0.02**. Do not swap them.

---

## 9. Artifact index

| Artifact | What it is |
|----------|------------|
| `data/validation/v1/internal_01pct_fpr_freeze.json` | Canonical 0.1% FPR operating point |
| `data/validation/v1/photography_day.json` | Full-world seed-48 headlines |
| `data/validation/v1/pareto_gtest48.json` | H5 5-point curve |
| `data/validation/v1/pareto_genuine_fpr.json` | H5b tight sweep |
| `data/validation/v1/pareto_operational_v1.json` | H5d operational Pareto |
| `data/validation/v1/h9_ablation_audit.json` | Feature group ablation |
| `data/validation/v1/h7_round1_diagnosis.json` | Weakest family = ATO |
| `data/validation/v1/h6_diagnosis.json` | Hard-negative forensics |
| `data/validation/v1/h5c_fpr_v2_eval.json` | Rejected FPR-v2 |
| `data/validation/v1/saml_d_forensics.json` | Transfer audit B1–B7 |
| `data/validation/v1/stage4_saml_d_loopm.json` | Full SAML-D scored eval |
| `data/validation/v1/champion_registry.json` | Machine-readable champion |
| `data/priors.json` | World amount/hour/persona priors |
| `data/rules/v0_rules.yaml` | Live rule set |
| `models/features.json` | Frozen recipe |

---

## 10. One-minute speech

We score causal event-time features with a multiclass histogram GBDT, then Brake maps family + score + rules to allow / notify / step-up / hold / decline / mule-credit-restrict. APP never silent-declines; mules get payee credit restrict; hubs are exempted from the fan-in hard flag. We raised identity-burst ranking by appending extra simulated events of the weak family and **refusing** later models that cut false positives but destroyed that family or cost. On frozen seed 48: about **98.7% recall at 0.1% genuine FPR** internally; the honest threshold (chosen on train inner_val only) is **0.9152**, giving **98.52% recall at 0.032% FPR** on the G-test eval fold. SAML-D transfer is ~**2% TPR** because the session and stamp features this model uses do not exist there. That is feature mismatch, not a hidden 98% on public AML data.

---

*Compiled 2026-08-30 from frozen v1 artifacts and the files listed in the header. If a later `model_freeze_id` exists, this pack is stale.*
