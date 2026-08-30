# AegisLoop — Comprehensive Validation Framework

**Prepared by:** Senior ML / Algo Science review  
**System:** AegisLoop — Identify → Generate → Defend closed-loop red/blue lab  
**Challenge:** Mastercard Innovation Challenge @ GFF 2026  
**Scope:** Every measurable claim in the three-pillar system, honest coverage gaps, and research-grade evaluation standards

> **Reading contract.** This document is the **lab validation spec** (metric definitions, G1–G7, honest gaps). It is **not** the Defend ticket list and **not** a GitHub/judge submission artifact. Coding agents implement from [`Docs/plans/defend-execution-ssot.md`](Docs/plans/defend-execution-ssot.md) **§13** (wins conflicts) + [`Docs/plans/README-defend.md`](Docs/plans/README-defend.md) + [`Docs/plans/defend-test-tracker.md`](Docs/plans/defend-test-tracker.md). Do not mine or pick Loop M miss family from G-test seed 43. `op_threshold` is inner-val, not G-eval. Loop M genuine-FPR slack is **0.02** (`loop_m.genuine_fpr_eps`); **0.002** is Loop T rule-promote only. The “nine loops” table below is a catalog of names — v1 Defend tickets are Loop M + Loop T per SSOT, not all nine.

---

## 0. Validation Principles

These principles govern every claim in this document. Violating any one makes the entire metric suspect.

### 0.1 The Seven Hard Gates (non-negotiable)

These gates are defined in `defense_architecture.md §12` and serve as preconditions for **any** result reporting.

| Gate | What it enforces | How it is tested |
|------|-----------------|-----------------|
| **G1 — No future information** | Every feature at time `t` uses only events with `timestamp < t`; no post-payment labels, refunds, disputes, future graph edges, generator metadata, or test-set markers | Recompute features on causal `G(t−)` vs full graph; AUC must diverge if training used leakage |
| **G2 — Temporal + entity split** | No random `train_test_split` as the published holdout; split by time (first 2/3 calendar) + entity holdout (mule payee ids disjoint across train/test) | CI schema test: `split.parquet` has `event_ts`; shuffle flag absent from fit code |
| **G3 — Validate the LLM extractor** | LLM signals are a model, not ground truth; tested in three conditions: structured-only, structured+LLM, missing/abstained LLM | Ablation: APP PR-AUC with vs without `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure` |
| **G4 — Delayed labels** | An approval is not proof of genuine; a decline is not proof of fraud | `label_source` + `label_ts` + `label_lag_hours` stored on every row; simulated labels clearly marked |
| **G5 — Candidate has a baseline** | Every proposed rule or model compared to currently promoted version at same alert budget | Precision, recall, genuine-FPR, alert volume, friction-by-action, latency, rail/class stability all in report |
| **G6 — Rollback is part of promotion** | Previous rule set and model artifact kept; any canary regression restores prior version | Promotion record has version + data version + feature version + approval record |
| **G7 — Honest coverage** | Each locked technique is exactly one of: `built`, `case_only`, `offline_loop`, `named_gap` | Coverage table §4.4 below; never count a generic fraud score as proof of per-technique detection |

**If any gate fails, that result is labeled `exploratory` in the UI and write-up.** The prototype is not ready to claim results until all seven have passed.

### 0.2 Metric Hierarchy

```
Primary (lead with these)           Secondary (support)           Never lead with
────────────────────────────        ───────────────────          ──────────────────
PR-AUC / AP by typology             ROC-AUC                      Accuracy
TPR at FPR 0.1% / 0.5% / 1%        F1 at operating point        Balanced accuracy on toy mix
Entity-level mule recall            Precision@review-capacity    "We beat production"
Genuine FPR                         ECE (calibration)            "This is live UPI"
Latency p50/p99 ms                  Cost sketch (₹)              "Lab fraud rate = India rate"
```

### 0.3 Terminology

| Term | Definition |
|------|-----------|
| **G-eval** | Outer eval fold of the training world (last 1/3 + entity holdout). **Diagnostic only** after Ticket 3. Not for `op_threshold`. |
| **inner-val** | Last 20% of **train** calendar. Optuna + `op_threshold`. |
| **G-dev** | Separate world `world_seed=44`. Loop T mine/gate, FN harvest, ECE, permutation. |
| **G-test** | Second population, `world_seed=43`, same engine + parameters; **reported transfer metrics only** |
| **G-train** | First 2/3 of training run calendar; model fits here |
| **Canary Vault** | Single-seed 180-day chain ledger (T09→T11→T13→T02); never written to by the feedback loop |
| **Loop-M row** | Evasion / miss added to G-train only; never to G-test or Canary Vault |
| **PR-AUC** | Average Precision (area under the Precision-Recall curve); unaffected by true-negative count; appropriate for low fraud rates |
| **FPR** | False Positive Rate on **genuine** rows (label\_family == `normal`); not the same as 1 − Precision |
| **genuine_fp** | **Lead FPR metric:** `FP / n_normal` on the scored population |
| **genuine_fp_over_eval** | Legacy name: `(TP+FP) / n_eval` — **predicted-positive rate** over all eval rows, not genuine FPR. Fit-time Stage 1 (~4.84%) is seed-46 **eval fold**; G-test seed 48 (~8.79%) is a different population. Always pair with `genuine_fp` when reporting. |

---

## 1. Identify Pillar Validation

### 1.1 What "Identify" Claims

The Identify pipeline (`packages/agents/identify_graph.py`) performs:
- Scout: domain-allowlisted search (Tavily + RSS, `packages/osint/allowlist.py`)
- Extractor: structured `AttackSpec` JSON from article bodies (LLM + Pydantic)
- Grounder: reject non-payment, buzzword-only, exploit-pattern, cosine > 0.92 duplicate
- TierScorer: `source_tier` from allowlist tier of `source_urls`; `confidence_level`
- Corroborator: `vector_class`, `corroboration_type`, `canary_eligible`
- Librarian: dedup vs catalog embeddings; HITL payload

**Claim:** 24+ distinct, grounded, payment-rail-specific GenAI fraud techniques surfaced.

### 1.2 Identify Metrics and Thresholds

#### 1.2.1 Catalog Diversity Score

Diversity is measured along four axes. Each cell in the matrix that has ≥1 approved technique scores 1 point.

```
Axes:
  Lifecycle stage: kyc | auth | initiation | authorization | settlement | cashout (6)
  Rail:            card_cnp | card_cp | upi_like | imps | onboarding | cross-border (6)
  Economic class:  APP | ATO | CNP | mule | BEC | detector (6)
  GenAI modality:  text | voice | video | document | bot | poisoning | mixed (7)
```

| Threshold | Interpretation |
|-----------|---------------|
| Filled cells ≥ 18 | Baseline diversity (breadth claim substantiated) |
| At least 5 of 5 umbrella categories populated | All categories addressed |
| ≥ 24 techniques with `generate_mode` populated | 24-technique catalog complete |
| ≥ 8 techniques with `confidence_level = confirmed` | Regulator-grade sourcing |
| ≥ 16 techniques with at least 1 citation | Grounded, not hallucinated |

**Current state (seed):** 29 rows seeded, T01–T24 all populated. Identify agent proposed 2 additional in Phase 1a. Diversity score computed from `killchain_atlas`.

#### 1.2.2 Grounder Rejection Quality

The Grounder must reject bad specs without destroying good ones.

| Test | Pass condition |
|------|---------------|
| No payment rail in spec | Rejected |
| "GenAI" appears only as buzzword with no mechanism | Rejected |
| Cosine similarity > 0.92 to existing technique in same run | Rejected (dedup) |
| Exploit-pattern text (phishing kit, malware steps) | Rejected |
| Legitimate FinCEN-level technique with valid rail | **Not** rejected |
| False rejection rate on known-good seed specs | < 5% |

#### 1.2.3 Source Tier and Confidence

| Source class | Tier | Minimum confidence |
|-------------|------|-------------------|
| Primary regulator (FinCEN, RBI, FCA, FBI IC3) | 1 | `confirmed` if tier ≤ 2 |
| Secondary regulator / central bank research | 2 | `confirmed` if ≥2 orgs each at tier ≤ 3 |
| Industry research (Feedzai, Wipro, Deloitte) | 3 | `reported-unverified` |
| News / arXiv preprint | 4 | `reported-unverified` |
| Unverified / unknown domain | 5 | Must be rejected by allowlist |

#### 1.2.4 What Identify Does NOT Claim

| Excluded claim | Why |
|---------------|-----|
| Complete coverage of all fraud in the wild | Only allowlisted public corpus |
| Real-time threat intelligence | `IDENTIFY_LIVE_SEARCH=false` in demo; fixtures used |
| Dark-web technique sourcing | Explicitly forbidden by safety policy |
| Criminal operator playbooks | Only typology-level descriptions |

### 1.3 Identify Honest Gaps

| Gap | Honest statement |
|-----|-----------------|
| No India-specific regulator corpus (NPCI/RBI hourly stats) | Stated: sources are FinCEN/FTC-centric; RBI fixture loaded but weaker than FinCEN |
| LLM extractor abstains on weak articles | Correct behavior; `extraction_source=abstain` recorded |
| KYC-vendor LLM supply-chain (T06/T07) | `generate_mode=name_only`; named on threat map, not simulated |
| Live MFA-relay kit by name | Class named; kit not published (safety policy §9.8) |
| Deepfake VKYC as images | No image generation; described as field flags only |

---

## 2. Generate Pillar Validation

### 2.1 What "Generate" Claims

The Generate engine (`packages/sim/`) produces:
- A quiet UPI-like world: Poisson event-driven, 4 personas, calibrated amounts (lognormal mean-matched to `data/priors.json`)
- 4 injectors: `graph_mule` (T01–T05), `identity_trajectory` (T11, T12), `app_session` (T13), `doc_beneficiary` (T24)
- 6 `label_family` values: `normal`, `mule`, `identity_burst`, `ato`, `app_fraud`, `invoice_fraud`
- Causal `features_auth` from running account state (O(n), not O(n²) per row)

**Claim:** High-fidelity simulated payment ledger suitable for training and stress-testing a fraud detector.

### 2.2 Fidelity Metrics and Thresholds

#### 2.2.1 Population Stability Index (PSI)

PSI measures distributional shift between a reference prior and the generated ledger.

```
PSI = Σ (actual_i - expected_i) × ln(actual_i / expected_i)
```

Industry standard thresholds (Basel/risk management convention):

| PSI range | Interpretation | Action |
|-----------|---------------|--------|
| PSI < 0.1 | Minor / negligible shift | Pass; no alert |
| 0.1 ≤ PSI < 0.2 | Moderate shift | Warn; investigate prior update |
| PSI ≥ 0.2 | Major distributional change | **Fail fidelity gate**; fix generator |

**Our gates (frozen in fixture test):**

| Distribution | Gate |
|-------------|------|
| Amount PSI vs `priors.json` buckets (normal rows only) | PSI < 0.1 |
| Hour-of-day PSI vs bimodal prior | PSI < 0.15 |
| Fraud rate band | 0.5% – 3.5% (lab oversample; ≠ India prevalence) |
| Median mule inbound `fan_in_1h` (computed, not copied) | > 5 |

**Why PSI, not KS p-value:** KS p-value conflates effect size with sample size. At 50k rows, trivially small differences produce p < 0.05. PSI is the financial-industry standard for monitoring because it is threshold-interpretable regardless of n.

**Honesty note:** PSI vs `priors.json` is a **sampler quality check** (does the lognormal mean-match work?). It is NOT proof that the ledger matches live UPI. The priors themselves are stated as assumptions with provenance, not verified against real transaction flows.

#### 2.2.2 Anti-Stub Gate (causal feature independence)

This is the most important Generate correctness test. It catches the case where `fan_in_1h` is simply copied from YAML knobs rather than computed from actual edges.

| Test | Method | Pass condition |
|------|--------|---------------|
| `fan_in_1h` independence from catalog knob | Compare computed `fan_in_1h` on fixture ledger vs YAML `fan_in_1h` value | Not all values equal the knob |
| Minimum computed variance | Across mule inbound rows | `max(fan_in_1h) - min(fan_in_1h) > 0` |
| Causal ordering | Feature at row `i` uses only rows with `event_ts < event_ts[i]` | Running state; no future edges |
| Synthetic clock test | Tiny 5-event fixture, manually verify feature snapshots | All values match manual computation |

#### 2.2.3 Label Correctness

| Test | Pass condition |
|------|---------------|
| `label_family` ∉ `{T01, …, T24}` | Technique IDs never appear as train targets |
| T12 (device shift) → `ato`, not `identity_burst` | Brake needs APP ≠ ATO ≠ mule to route correctly |
| `liveness_score` NULL on post-onboarding rows | Feature contract: onboarding-only field |
| `doc_consistency` NULL on post-onboarding rows | Same |
| APP flags (call_active, copy_paste, pause_ms, urgency) = False/null on non-APP rows | No contamination |
| `is_authorized_push` absent from train Parquet | Denylist enforced by CI |
| `economic_class` absent from train Parquet | Sidecar only |

#### 2.2.4 Allowlist / Denylist Schema Test (CI gate, must pass)

```
Train Parquet allowlist (exhaustive):
  rail, kyc_tier, account_age_days, payee_history_count, amount_vs_p30,
  fan_in_1h, fan_out_1h, is_new_payee, is_new_device, burst_velocity,
  call_active_flag*, copy_paste_payee_flag*, pause_ms*, urgency_pressure*,
  label_family
  (* only on app_fraud rows; False/null elsewhere)

Denylist (any of these in train Parquet = CI fail):
  vector_id, injector_id, technique_id, simulatable_signals,
  persona_type, world_seed, is_authorized_push, economic_class,
  label_class, gstin, transcript, embedding
```

#### 2.2.5 Canary Vault Correctness

The canary is a single 180-day world (seed = 42) that runs T09 → T11 → T13 → T02 on **shared** `VID-SIM-CHAIN-*` accounts. It is the only fixture where seasoning = 150 days is honored without clamping.

| Check | Pass condition |
|-------|---------------|
| Four lifecycle stages in time order | `lifecycle_stages_logged` contains all four |
| Shared party ids across stages | Same `VID-SIM-CHAIN-*` appear in multiple stage events |
| Knobs pinned (no ±50% jitter) | Canary `pin=True`; sidecar `knobs_pinned` matches catalog |
| `sim_days = 180` | UI displays 180; no silent truncation to 76 days |
| Seasoning honored: 150-day window intact | `seasoning_clamped = False` on canary chain |

#### 2.2.6 Scalability Gate

| Test | Pass threshold |
|------|---------------|
| 50k rows (full population `n_customers=2400`) | < 5 minutes on a laptop (marked `slow`) |
| O(n) running state — not O(n²) | 1k-row micro-bench uses account state cache, not full ledger scan |
| APP inject does not iterate `world.events` | `test_app_inject_does_not_scan_ledger` CI gate |

### 2.3 Generate Honest Gaps

| Gap | Honest statement |
|-----|-----------------|
| Amounts calibrated from public NPCI aggregate stats, not raw transaction flows | `ticket_stat: "mean_from_value_over_volume"` in priors; stated assumption |
| Hour-of-day is bimodal assumption | No cited public hourly distribution; filed as `assumption` in priors provenance |
| T06 (merchant collusion) not simulated | No merchant-node cycle engine built; named gap on coverage map |
| T07 (CNP/card testing) not simulated | Generate stays UPI-shaped; named on threat map; card features named only |
| T20–T23 (Cat 4 adversarial) | Offline Loop A only; not in population runs |
| PSI vs own priors ≠ PSI vs live UPI | Sampler QA, not ground-truth calibration |
| Lab fraud rate (0.5–3.5%) ≠ India UPI fraud rate | Write-up must state: "lab oversample for training; India prevalence is sub-0.01%" |
| Synthetic call/paste flags ≠ real SDK behavioral biometrics | Simulated boolean fields; not extracted from real sessions |

---

## 3. Defend Pillar Validation

### 3.1 What "Defend" Claims

The Defend pipeline produces:
- A GBDT champion (`HistGradientBoostingClassifier` or LightGBM) trained on Plan 08 train allowlist
- Rules: hard flags, nudges, calm-downs evaluated on row values
- Brake: maps predicted family + rule hits → `policy_action` enum
- Loop M: one demonstrated retrain from misses with G-test comparison

**Claim:** Accurate detection (PR-AUC by typology, TPR at low FPR) + policy-differentiated mitigation + honest feasibility story.

### 3.2 Model Metrics and Thresholds

#### 3.2.1 Primary Metrics (lead in write-up and dashboard)

**Headline (walkthrough / judges):** G-test only (`world_seed=43`, `score_run(all_rows=True)`). **G-eval** (same-run outer holdout) is **diagnostic** after Ticket 3 — store it, do not lead with it, do not set `op_threshold` from it. TPR@FPR uses the frozen **inner-val** threshold:

| Metric | Computation | Threshold to claim "working" | Threshold to claim "strong" |
|--------|-------------|-----------------------------|-----------------------------|
| **PR-AUC (AP) — app_fraud** | `average_precision_score` on binary `is_app_fraud` vs model score | > 0.50 | > 0.75 |
| **PR-AUC — mule** | `average_precision_score` on binary `is_mule` | > 0.60 | > 0.80 |
| **PR-AUC — ato** | Binary `is_ato` | > 0.50 | > 0.70 |
| **PR-AUC — invoice_fraud** | Binary `is_invoice_fraud` | > 0.55 | > 0.75 |
| **PR-AUC — identity_burst** | Binary `is_identity_burst` | > 0.55 | > 0.75 |
| **TPR @ FPR 0.1%** | On binary fraud vs normal, frozen threshold from **inner-val** | > 30% | > 55% |
| **TPR @ FPR 0.5%** | Same | > 50% | > 70% |
| **TPR @ FPR 1.0%** | Same | > 65% | > 80% |
| **Genuine FPR** | FP rate on `label_family == normal` rows | < 2% | < 0.5% |
| **Entity mule recall** | Fraction of gold mule payee accounts with ≥1 inbound flagged; **headline on G-test**, G-eval diagnostic | > 50% | > 75% |

**Why PR-AUC, not ROC-AUC:** At 0.5–3.5% fraud rate, the True Negative count dominates ROC-AUC. A naive majority classifier achieves ROC-AUC > 0.90 while missing all fraud. PR-AUC focuses on the precision-recall trade-off where the class imbalance actually matters. This is consistent with industry practice (Feedzai, Stripe, Mastercard DI all report operating-point metrics, not ROC-AUC as headline).

**G-test transfer:** Lead with G-test AP. Keep G-eval AP under `diagnostic_*`. A drop of > 25% relative (e.g., 0.80 → 0.60) indicates the model memorized entities or time-specific patterns rather than learning generalizable signal. Document this drop; do not hide it.

#### 3.2.2 APP Ablation (mandatory, not optional)

The APP (Authorized Push Payment) category is the hardest because the victim intentionally authorizes the payment. Synthetic session flags (`call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`) are the primary signal. This ablation tests whether the detection is real or cheating on synthetic markers.

| Condition | Reported metric | Interpretation |
|-----------|----------------|----------------|
| APP with all four session flags | PR-AUC (baseline) | Upper bound; requires SDK-grade signals |
| APP without any session flags | PR-AUC (ablation) | Realistic scenario; must be documented |
| APP without pause_ms only | PR-AUC | Flag importance |
| APP without call_active_flag only | PR-AUC | Flag importance |

**Honest expected result:** APP PR-AUC without session flags may drop to < 0.3. This is **correct** to report, not a failure. It correctly states that real APP detection without behavioral biometric signals is genuinely hard. A system that hides this drop is lying to judges.

**Document in write-up:** "Without real-time behavioral biometric signals from an issuer SDK (call detection, paste event), APP detection degrades substantially. This is a fundamental limitation of payment-time features, not a model failure."

#### 3.2.3 Calibration (ECE)

If a 0–1000 risk score is displayed in the UI, calibration must be tested.

```
ECE = Σ_b (|b| / n) × |accuracy(b) - confidence(b)|
```

| ECE threshold | Interpretation |
|---------------|---------------|
| ECE < 0.05 | Well-calibrated; score means what it says |
| 0.05 ≤ ECE < 0.10 | Moderate miscalibration; acceptable with disclaimer |
| ECE ≥ 0.10 | Poorly calibrated; do not present as a probability |

For fraud at 1% base rate, even a perfect classifier will show calibration challenges. Use isotonic regression or Platt scaling post-GBDT. Report ECE before and after calibration.

#### 3.2.4 AuthGate Latency Benchmark

| Metric | Measurement | Gate |
|--------|-------------|------|
| p50 ms/row | In-process `predict()` on 1k-row batch (no network) | < 5 ms (GBDT champion, CPU) |
| p99 ms/row | Same | < 50 ms |
| Hang guard | Scoring 1k rows | < 60 seconds total; fail test if minutes |

**Honesty disclaimer:** "AuthGate latency measured in-process on a development laptop. This is not a production-grade Mastercard DI 50 ms story, which includes network, auth, feature fetch, and policy layers. Our latency claim is for the model inference component only."

### 3.3 Rules Validation

#### 3.3.1 Rule Coverage Matrix

Every locked technique must have exactly one status entry:

| Coverage status | Definition |
|----------------|-----------|
| `built` | Simulated + live rule fires on computed row values |
| `case_only` | Simulated but no live rule; detected in case tab or post-payment review |
| `offline_loop` | Cat 4 loop only; no live rule |
| `named_gap` | Technique cataloged; cannot be detected on available rail signals |

A generic fraud score does not count as `built` for a specific technique.

#### 3.3.2 Rule Correctness Tests

| Rule | Test | Pass condition |
|------|------|---------------|
| Mule hard flag (`fan_in_1h >= 6`) | Fire on fixture mule row with `fan_in_1h = 8` | `hard_flag` in hits |
| Mule hard flag | Do NOT fire on normal row with `fan_in_1h = 0` (key present but zero) | Empty hits |
| Call + paste + new payee hard flag | Fire on `call_active_flag=True, copy_paste_payee_flag=True, is_new_payee=True` | `hard_flag` in hits |
| Calm-down | Known payee + usual amount + old device → `allow` even with weak model score | `policy_action == allow` |
| Beneficiary-changed hard flag | Fire on `beneficiary_changed=True` with checksum pass | `hard_flag` in hits |

#### 3.3.3 Brake Policy Tests

| Input condition | Required `policy_action` | Forbidden action |
|----------------|--------------------------|-----------------|
| Predicted `app_fraud`, elevated | `notify` or `hold` | `decline` (victim intentionally paid) |
| Predicted `ato`, high score | `decline` | `notify` (credential stolen) |
| Mule payee inbound | `mule_credit_restrict` | Only scoring the sender |
| Low score + calm-down wins | `allow` | Random decline of genuine kirana |
| New payee + high amount, no model | `step_up` | `allow` silently |

### 3.4 Split Protocol Validation

```python
# Correct (what we do)
train_idx = time_cut(events, frac=2/3) AND entity_holdout(mule_payees)
test_idx  = remainder (no mule payees from train, later time)

# Wrong (what we forbid)
train, test = train_test_split(events, shuffle=True)  # DATA LEAK
```

| Test | Pass condition |
|------|---------------|
| `event_ts` in split.parquet | True |
| No party ids in model matrix `X` | Schema check |
| Entity holdout: mule payee ids disjoint | `VID-SIM-U-*` in train ∩ test = ∅ |
| G-test uses different `world_seed` | `world_seed = 43` (vs train `42`) |
| G-test AP reported separately | Headline G-test AP + diagnostic G-eval AP in metrics JSON |

### 3.5 Defend Honest Gaps

| Gap | Honest statement |
|-----|-----------------|
| No verified real-data holdout (SAML-D, BAF) | Write-up §: "HoldoutVault protocol named but not yet validated in v1; SAML-D/BAF link verification pending" |
| Laptop GBDT ≠ issuer AuthGate production | Latency claim is inference-only; full payment stack adds network + feature-fetch overhead |
| Lab fraud rate ≠ India UPI prevalence | scale_pos_weight set from lab rate (~1%); real issuer would use empirical base rate |
| Cat 3 live AUC not reported as headline | Behavioral biometric flags at auth; chat text is case-only |
| Cat 4 is a named loop, not a working API | Offline Loop A; evasion chart present but no public red API |
| One retrain ≠ nine production loops | Loop M demonstrated once; H, G, T, R not all exercised in demo |
| No real cardholder preference data | No RLHF on trees; LightGBM does not learn from dispute overrides in 4 days |

---

## 4. Coverage Map (24 Techniques × 5 Categories)

This is the honest coverage table required by `defense_architecture.md §9` (Gate G7).

### 4.1 Category 1 — Network / Transaction Structuring

| Technique ID | Name | Mode | Live check | Holdout |
|-------------|------|------|------------|---------|
| T01 | Mule fan-in / funnel | **Built** | `fan_in_1h` neighborhood on `G(t−)`; catch account not just last edge | SAML-D typology map |
| T02 | Mule cash-out / fan-out | **Built** | TTL then sink MCC; `fan_out_1h` | SAML-D |
| T03 | Smurfing under UPI cap | **Built** | `smurf_cap_ratio` computed; amounts just below `priors.caps.txn_max_minor` | SAML-D |
| T04 | Chain-hopping UPI→IMPS | **Built** | Rail switch + burst velocity | SAML-D / TransXion |
| T05 | Dust / layering | **Built** | Many tiny outbound edges; high out-degree in window | SAML-D |
| T06 | Synthetic merchant collusion | **Named gap** | No merchant-node cycle engine; merchant graph not in sim | State: "requires merchant settlement rail not in scope v1" |
| T07 | Card / BIN testing | **Named gap** | Generate stays UPI-shaped; no card-auth event type | State: "BIN attack pattern named; card auth rail not simulated" |

**Cat 1 honest headline:** 5 of 7 built; 2 named with explicit rail-availability gap.

### 4.2 Category 2 — Identity

| Technique ID | Name | Mode | Live check |
|-------------|------|------|------------|
| T08 | Synthetic KYC onboarding | **Built** | `liveness_score` / `doc_consistency` on onboarding row; `kyc_tier` |
| T09 | Deepfake VKYC liveness bypass | **Case + Named** | Channel switch + refused extra factor as field flags; no image gen |
| T10 | Forged KYC document fields | **Case** | Form inconsistency flags; no image forgery pipeline |
| T11 | Long-horizon identity farming | **Built** | Seasoning 150d → burst velocity; `identity_burst` label |
| T12 | Account takeover (device shift) | **Built** | New device + new payee + velocity spike → `ato` label |
| T13 | ATO via synthetic social (UPI APP) | **Built (partial)** | Session flags at auth; full scam script in case tab |
| T14 | KYC-vendor / LLM supply-chain | **Named gap** | Onboarding-API compromise; no KYC vendor simulation |

### 4.3 Category 3 — Social Engineering / APP

| Technique ID | Name | Mode | Live check |
|-------------|------|------|------------|
| T15 | Vishing coercion | **Built** | `call_active_flag + copy_paste_payee_flag + is_new_payee` |
| T16 | Push-payment scam (UPI impersonation) | **Built** | Same; `urgency_pressure`; APP session flags |
| T17 | Live MFA-relay (Balonx class) | **Built (class)** | Call + OTP-timing fields + payee change as session flags; kit not named |
| T18 | Romance / investment long-con | **Built (weak)** + Case | Slow-burn then burst + new payee; scripts in case tab |
| T19 | Polymorphic phishing | **Named / Case** | Landing-to-pay session flags if available; no phishing kit |
| T20 | Invoice-timed impersonation | **Built** | Cat 3 session AND Cat 5 beneficiary change (both required) |
| T21 | Voice-clone BEC | **Case / Named** | No audio generation; described as commercial-payer beneficiary change |

### 4.4 Category 4 — Adversarial / Model-Targeted

| Technique ID | Name | Mode | What we do |
|-------------|------|------|------------|
| T22 | Detector evasion | **Offline Loop A** | LLM JSON patch on `X_adv` columns only; verifier-accepted rows only; Oracle Guard |
| T23 | Training-data poisoning | **Loop (named)** | Trust tiers on rows; cap evasion mix ≤15%; canary veto if genuine FPR jumps |
| T23b | Detector fingerprinting | **Named (offline)** | Query cap; no SHAP/tree weights returned to attacker; no public API |
| T23c | Merchant/support bot injection | **Named** | Not in public prototype; safety policy §9.7 |
| T23d | Agentic payment initiation | **Named / Built if envelope has `agent_initiated`** | Cat 3∩4 intersection; catalog + optional flag |

### 4.5 Category 5 — Document / Content Forgery

| Technique ID | Name | Mode | Live check |
|-------------|------|------|------------|
| T24 | Fake invoice / beneficiary swap | **Built** | GSTIN checksum **passes** in code; `beneficiary_changed=True`; wrong account → `invoice_fraud` |
| T24b | Fabricated dispute / chargeback pack | **Case** | Fields disagree with original payment; no fake letterheads |
| T24c | Amateur checksum-fail invoices | **Excluded** | Not the interesting case; real threat is pass-checksum with wrong beneficiary |

### 4.6 Coverage Summary

| Status | Count | Percentage |
|--------|-------|-----------|
| `built` (simulate + live rule) | 14 | 58% |
| `case_only` or `offline_loop` | 5 | 21% |
| `named_gap` (honest) | 5 | 21% |
| **Missing (not allowed)** | 0 | 0% |

**Every technique in the locked taxonomy is accounted for.** Zero missing entries.

---

## 5. Closed Loop Validation

### 5.1 Loop catalog (names) — not a v1 ticket list

Identify/Generate architecture names nine loops. **Do not implement all nine from this table.** Defend v1 tickets (SSOT): Loop **M** and Loop **T**. Loops I/R/A/F/C/H/G are named or one-shot demo status only.

| Loop | Name | Demo status | Validation evidence |
|------|------|-------------|--------------------| 
| **I** | Catalog ↔ defense coverage | Live (one iteration) | Coverage map updated when new catalog card added; Loop I drafts rule form |
| **R** | Flags → better rules | One scripted example | Batch of flags → new draft → genuine-FP smoke test → pass or fail |
| **T** | Trees → readable rules | Live | Short LightGBM paths → if-then rules; quiet-on-genuine check |
| **M** | Misses → more training data | **Must work once** | Extra rows added to G-train only; G-test AP for that family improves or documented equal; genuine FPR not worse |
| **A** | Red vs blue (Cat 4) | Offline chart | Evasion rate vs query budget; post-retrain G-test PR-AUC on frozen set |
| **F** | Lab vs public data | Chart | Our fakes vs SAML-D/BAF map; if lab ≫ public → fix Generate (Loop G), not detector |
| **C** | Identify hunts holes | Live | Coverage map shows empty cells; Identify proposes vectors to fill |
| **H** | Human overrides | Named (post-deployment) | Override log; no RLHF on trees in demo |
| **G** | Generate uses defender feedback | Named / one example | If Loop F shows drift → change injector parameters |

### 5.2 Loop M Validation Protocol

This is the primary closed-loop claim. It must be demonstrated, not just described.

```
Protocol:
1. Identify a miss cluster from **G-dev 44 or diagnostic/inner-val — never G-test seed 43** (e.g., mule with low fan_in_1h slipping through). G-test is for before/after report only.
2. Compute Loop-M quota: ≤ 15% evasion rows of total G-train size; no flooding single trick
3. Add tagged rows (label_source=loop_m) to G-train ONLY
4. Refit champion with same recipe (seed, features, scale_pos_weight)
5. Compare on G-test (seed ≠ train seed):
   - AP for the missed family: must improve or be documented equal
   - AP for other families: must not degrade > 5% relative
   - Genuine FPR: must not exceed prior model's FPR + ε (ε = **0.02**, `loop_m.genuine_fpr_eps`; not the rule-promote 0.002)
6. If any canary vault metric worsens: do not promote; report failure honestly
```

| Metric | Pass condition | Failure action |
|--------|---------------|----------------|
| G-test AP (miss family) after Loop M | ≥ prior AP or documented equal | Do not mark `solved`; continue loop |
| G-test AP (other comparable families) | relative drop ≤ 5% (`loop_m.other_family_rel_drop_eps`) | **Fail `loop_pass`**; do not promote |
| Genuine FPR | ≤ prior + **0.02** (Loop M slack) | Rollback; do not promote |
| Canary Vault AP | ≥ prior − 0.02 (absolute) | Rollback |

### 5.2b Loop T Validation Protocol

- Mine and tree fit: G-dev 44 `gdev_mine` only (never seed 43, never inner-val).
- FPR / incremental recall: G-dev 44 `gdev_gate` only (`rule_promote_genuine_fpr_eps = 0.002`).
- HITL approve required. No auto-promote.
- Drafts must not appear in `load_v0_rules()` until approve.
- YAML stays a list; backups in `data/rules/backups/`.

### 13.3b Loop T checklist

- [ ] Mine does not open seed-43 paths
- [ ] `gdev_mine` and `gdev_gate` event_ids disjoint
- [ ] Draft absent from live YAML until approve
- [ ] LLM cannot change `when`


A technique is marked `solved` in the Atlas ONLY when ALL of the following hold:

1. ≥ 2 red-team rounds (Loop A) on the same technique family
2. G-test PR-AUC stable (< 5% relative drop between rounds)
3. Genuine FPR not worse than before the loop
4. Typology credit is exact: a Cat 1 (mule) evasion fix is NOT credited as a Cat 3 (APP) win
5. No Cat 4 evasion rows in the G-test partition

**Current expected state in demo:** 0 techniques marked `solved` (only one Loop M has been run). The arms-race chart shows evasion rate vs round; `solved` is the aspirational endpoint visible in the UI trajectory.

### 5.4 Poisoning Controls

| Control | Implementation | Test |
|---------|---------------|------|
| Trust tiers | Each row tagged: `human_gold`, `synth_verified`, `loop_evasion` | `label_source` column in sidecar |
| Evasion mix cap | Loop M rows ≤ 15% of G-train | Assert in Loop M code |
| Near-duplicate cap | One evasion → max 3 copies in G-train | Dedup check in export |
| Canary veto | If real-proxy FPR jumps → rollback | Canary Vault comparison |
| Generator-id exclusion | `generator_id` / `persona_id` / `patch_round` never in model `X` | Denylist CI test |

---

## 6. External Holdout Validation (HoldoutVault)

> **Superseded for Stage 4 sequencing** by [Master validation protocol](.cursor/plans/external_holdout_validation_64f9d54e.plan.md) and [`Docs/plans/eval-child-external-dataset.md`](Docs/plans/eval-child-external-dataset.md). Do not score lab-champion AP on SAML-D without a FeatureComputer replay adapter; use `blocked_no_adapter` in the write-up. Do not copy “vault” terminology into the .docx.

This section documents the external datasets used for transfer validation. Per `decisions.md Part C`, some links are unverified and **must be confirmed before citing in the .docx**. TalkingData AdTracking, BitcoinHeist, and FinCEN Files are **not** scored holdouts — see §6.6.

### 6.1 Category 1 — Network (transfer datasets)

| Dataset | Description | Availability | Typologies | Use in validation |
|---------|-------------|-------------|------------|------------------|
| **SAML-D** | Synthetic AML dataset; 9.5M transactions; ~0.10% fraud rate; 17 labeled AML typologies (smurfing, layering, fan-in/out, etc.) | Kaggle (verify link before citing) | Structuring, smurfing, layering, fan-in, fan-out | Map our typologies to SAML-D typology IDs; compute transfer PR-AUC |
| **TransXion** (2026) | Graph-shaped tabular AML dataset; ~3M rows; ~0.15% fraud rate; tabular-usable | Paper / GitHub (verify link) | Graph-shaped; map to UPI rail; drop FX rows | Transfer AUC comparison |
| **MoMTSim V2** | Mobile money simulation; 4.22M rows; 52.84% fraud (artificial ratio) | Published dataset | Closest to UPI P2P structure | Recalibrate metrics for artificial ratio; report "after recalibration" |

**Transfer validation protocol for Cat 1:**
```
1. Train champion on our synthetic G-train (seed 42)
2. Map SAML-D typology labels to our label_family schema
3. Compute AP and TPR@FPR on SAML-D eval split
4. Report: (a) lab AP (G-test), (b) SAML-D AP, (c) typology-level mapping table
5. If SAML-D AP < lab AP / 2: investigate Generate fidelity (Loop F)
6. Never claim "we achieve X% on SAML-D" without the mapping table
```

**Honest expected gap:** Lab PR-AUC will be higher than SAML-D transfer because (a) our features are engineered for our simulator's schema and (b) SAML-D has different amount distributions and graph topology. **Document this gap; do not hide it.**

### 6.2 Category 2 — Identity (transfer datasets)

| Dataset | Description | Notes |
|---------|-------------|-------|
| **BAF (Bank Account Fraud)** | NeurIPS 2022, Feedzai; solid tabular + temporal fraud dataset | **No India Stack (Aadhaar/PAN)**; does not have UPI VPA structure |
| **ATO proxy injection** | Inject known device-shift + velocity-spike patterns into BAF baseline | TPR on injected anomalies; not a standalone dataset |

**BAF validation protocol:**
```
1. Map BAF features to our feature schema (account_age_days → BAF tenure; etc.)
2. Train on BAF, test on our G-eval OR train on ours, test on BAF (cross-train-test)
3. Report both directions; expect significant drop in cross-direction
4. State: "BAF contains no UPI behavioral features; cross-dataset transfer shows feature schema gap"
```

### 6.3 Category 3 — Social / APP (no external holdout)

| Approach | Method | Metric |
|----------|--------|--------|
| Blinded native-speaker annotation | 3 annotators label 50 generated scam transcripts as scam/not-scam + persuasion technique | Inter-rater: Cohen's κ; target κ > 0.6 (substantial) |
| LLM-as-judge | GPT-4 class model scores persuasion labels vs ground truth | Precision/recall on persuasion technique labels |

**Cohen's κ interpretation:**
| κ range | Agreement level | Claim |
|---------|----------------|-------|
| κ < 0.2 | Slight | Do not report; revise annotation scheme |
| 0.2 – 0.4 | Fair | Report with caveat |
| 0.4 – 0.6 | Moderate | Acceptable for pilot |
| 0.6 – 0.8 | Substantial | **Target for write-up** |
| 0.8 – 1.0 | Near-perfect | Exceeds expectations |

**Honest statement:** "No India-relevant Hinglish scam corpus with UPI payment linkage exists publicly. Our evaluation uses native-speaker annotation of our own generated scripts, which cannot claim generalization to live call-center data."

### 6.4 Category 4 — Adversarial (no static holdout)

Adversarial validation is inherently relative to the current champion.

| Metric | Measurement | Threshold |
|--------|-------------|-----------|
| Evasion rate (round 1) | % of verifier-accepted patches that lower score below threshold | Typically 20–60% on tabular classifiers |
| Evasion rate (after retrain) | Same on frozen G-test | Should be < round 1 evasion rate |
| Query budget | Queries used by attacker to find evasion | Report per successful evasion |
| G-test stability | Post-retrain G-test PR-AUC vs prior | ≥ prior − 0.02 absolute |

**Constraint (critical):** Evasion is only counted on `X_adv` columns (attacker-mutable: amount, mule payee among owned accounts, device rotate). Columns in `X_env` (bank-computed, frozen) and `X_forbidden` (generator IDs, future edges) are excluded from patches. Evasion claimed on `X_env` columns is cheating.

### 6.5 Category 5 — Document (expert validation)

| Method | Description | Metric |
|--------|-------------|--------|
| Expert red-team | Human manually crafts beneficiary-swap invoices; inject into our detector | TPR on expert-crafted attacks |
| GST distributional sanity | Compare our synthetic GSTIN patterns to publicly available GST filing aggregate statistics | Field-level PSI |
| Checksum gate | Verify `gstin_checksum_ok()` is correct via known-valid GSTINs | 100% pass on known-valid; 0% pass on known-invalid |

### 6.6 Named-gap appendix — not scored external-dataset

These tables are **not** HoldoutVault scored holdouts. Do not quote AP / TPR / transfer AUC on them.

| Dataset | Include in scored external-dataset? | Named gap |
|---------|--------------------------------------|-----------|
| TalkingData AdTracking | **No** | No `amount` — click/ad events, not payment-time transfers. |
| BitcoinHeist | **No** | Pre-aggregated address/window features, not authorization-time ledger rows. |
| FinCEN Files | **No** | SAR-level filings, not payment-rail events our AuthGate schema can score. |

---

## 7. Novelty Validation

### 7.1 What "Novelty" Claims

The PS evaluates novelty. Our novelty claims:

1. **Agents + synthetic flywheel:** Closed-loop LangGraph system where Identify feeds Generate feeds Defend
2. **Graph features + GBDT (not GNN) at payment time:** Tree-based models with causal windowed features achieve competitive fraud detection in milliseconds, without GNN latency
3. **APP ≠ ATO ≠ mule in the Brake policy:** Different economic classes require different interventions (hold vs decline vs credit restrict)
4. **Co-evolutionary arms race:** Cat 4 loop as the feedback mechanism, not a fifth model

### 7.2 Novelty vs Existing Work

| Claim | Comparison baseline | Our differentiation |
|-------|--------------------|--------------------|
| LangGraph closed loop | CrewAI, AutoGen (no durable state, no HITL) | Postgres checkpointer; HITL interrupts; typed LabState |
| GBDT + graph features | GNN (PyG/DGL) for fraud | GNN: 100s ms, GPU; GBDT: < 5 ms CPU; competitive quality per Tide (2026), IEEE-CIS DGL papers |
| Synthetic world simulation | PaySim, MoMTSim (no GenAI typology labels) | Our simulator emits labeled GenAI attack types that PaySim cannot |
| Brake policy (APP/ATO/mule) | Binary fraud/not-fraud classifiers | Policy-differentiated; APP gets hold/notify, not decline; mule payee gets credit restrict |
| Identify pipeline | Manual threat intel | Allowlisted search + structured extraction + grounder rules + HITL |

### 7.3 Literature Context

Key references that contextualize our design choices:

| Reference | Relevance |
|-----------|-----------|
| Kurshan, Mehta, Bruss, Balch — "AI versus AI in Financial Crimes and Detection" (arXiv:2410.09066) | Co-evolutionary AI framing; red/blue loop precedent |
| FinCEN FIN-2024-Alert004 | Deepfake payment fraud red flags → our feature flags |
| Feedzai BAF (NeurIPS 2022) | Standard tabular fraud benchmark |
| Tide: Temporal and Interpretation-Driven Evasion (2026) | GFP + LightGBM competitive with GNN on AML graphs |
| IEEE-CIS SageMaker DGL paper | Trees with graph features match GNN on fraud graphs |
| SAML-D typology paper | AML typology taxonomy baseline |

---

## 8. Real-World Feasibility Validation

This is an explicit PS evaluation criterion and where many hackathon submissions fail by making unrealistic claims.

### 8.1 Latency Architecture

| Path | Our claim | Evidence | Honest limitation |
|------|-----------|----------|-------------------|
| Model inference | < 5 ms p50, < 50 ms p99 | Measured in-process on laptop, 1k-row batch | Not a production Mastercard DI story; no network, no feature-fetch, no auth layer included |
| LLM off authorization path | LLM never on hot path | Code inspection: `/defend/score` calls `predict()`, no LLM | LLM used for case tab / rule drafts only |
| Rules (pre-model) | < 1 ms/row | O(1) if-then on pre-computed features | Rules must be precomputed before payment decision point |

### 8.2 APP Feasibility Story

| Aspect | Our approach | Feasibility score |
|--------|-------------|------------------|
| Detection without decline | Hold / notify / step-up for APP (not hard decline of authorized payments) | ✅ Matches RBI cooling period analog |
| Behavioral biometric dependency | Ablation shows AP drop without session flags; documented | ✅ Honest; requires SDK integration in production |
| Call-in-progress detection | Simulated boolean field; not real audio detection | ✅ Named: requires issuer telephony integration |
| Mule payee credit restrict | `mule_credit_restrict` action targets receiving side | ✅ Correct; matches mule network disruption approach |

### 8.3 Graph Feasibility Story

| Aspect | Our approach | Why this is correct |
|--------|-------------|---------------------|
| PageRank at payment time | Batch PPR computed offline, served as stale node attribute | Real-time PageRank on a complete graph at 50ms is impossible; stale batch is the production approach |
| Full graph vs `G(t−)` | All features use only `events with timestamp < t` | Causal; non-leaking; matches issuer data availability at auth time |
| GNN on live path | **Not built** | GNN inference latency (100ms–seconds with GPU) exceeds realistic payment budget |

### 8.4 Governance Feasibility Story

| Aspect | Demo | Production analog |
|--------|------|------------------|
| Auto-retrain | LoopGovernor with canary + human gate | Production: full model risk + champion-challenger process |
| HITL promote | Human clicks promote in demo | Production: model risk committee, extensive testing |
| Oracle Guard | Score query cap; no weights returned | Production: model as a service with strict API access control |
| Rollback | Previous model artifact kept | Production: blue/green deployment |

**State explicitly in write-up:** "The lab demonstrates the governance loop. Production deployment would require full model risk management, regulator notification, and live data integration that are outside hackathon scope."

---

## 9. Safety Validation

### 9.1 Safety Invariants (non-negotiable)

| Invariant | Test |
|-----------|------|
| No live rails or real PAN/VPA/Aadhaar | CI grep for real ID-shaped strings in generated output |
| No images, audio, APKs | No image generation pipeline; no audio files in repo |
| ShadowRail: allowlisted model endpoints only | `packages/osint/allowlist.py` enforced; no dark-web domains |
| LLM keys server-side | No API keys in browser; `.env.example` with no committed keys |
| All generator inputs treated as untrusted | Output = schema; verifier is code; prompt injection isolation |
| Cat 4 offline only | No public `/attack` or `/red-team` API endpoint |
| Loop cannot promote without canary + human | Promotion requires `canary_pass=True` AND `human_approved=True` |
| Public repo: no live URLs, no ID-shaped strings | CI grep gate |

### 9.2 Dual-Use Rating

Each Atlas technique has a `dual_use_rating` field (low/medium/high). High-rated techniques are:
- Logged with extra scrutiny
- Only described at typology level; no operator playbook
- Not available via public web prototype endpoints

### 9.3 SECURITY.md Requirements

The public repo must include a `SECURITY.md` with:
- Capability card: what the system can and cannot do
- Clear statement: "This system generates labeled synthetic fraud scenarios for defensive research. It does not generate real phishing content, real identity documents, or real payment credentials."
- Contact for security disclosures

---

## 10. Validation Anti-Patterns (What We Do NOT Do)

This section documents common pitfalls that would invalidate results. Every item below is **forbidden** by our architecture.

| Anti-pattern | Why it's wrong | Our mitigation |
|-------------|---------------|---------------|
| Random `train_test_split` as holdout | Related transactions split across train/test; mule network memorized | Time + entity disjoint split |
| `label_family` = `T13` (technique id as label) | Model learns technique metadata, not fraud pattern | Label allowlist: only `{normal, mule, ato, app_fraud, identity_burst, invoice_fraud}` |
| `fan_in_1h` copied from YAML knob | Model reads the simulation parameter, not a computed feature | Anti-stub gate: independent recompute from edges |
| `is_authorized_push` in model `X` | Direct label leakage for APP | Denylist CI test |
| PageRank on finished simulation graph | Future edges included; impossible at auth time | Batch PPR on `G(t−)` only |
| Same generator + 80/20 split as "holdout" | No distribution shift; inflated metrics | G-test uses different `world_seed` |
| Cat 4 wins added to G-test | Test contamination | Loop M rows → G-train only; G-test frozen |
| Auto-`solved` from ROC lift on G-dev | Wrong metric + wrong data partition | `solved` requires ≥2 Cat-4 rounds + G-test stability |
| `99.9% accuracy` claim | Imbalanced class trivial baseline; no FPR story | Lead with PR-AUC + genuine FPR |
| GNN at 50 ms claim | GNN inference requires GPU + graph sampling; not feasible at payment time | GBDT + windowed features; latency measured |
| "Beats Mastercard production" claim | We have no access to production data | "Research lab prototype" framing throughout |
| `world_seed` as a feature | Encoding the run identifier as model input | Denylist CI test |
| LLM scores the live payment | LLM latency 500ms–5s; no payment budget | LLM is case tab + rule drafts only |

---

## 11. Metrics Dashboard Requirements

The RedBlue Console must display these metrics to satisfy the PS and be demo-ready for judges.

### 11.1 Threat Map Panel

| Element | Required |
|---------|---------|
| All 24 techniques in 5 category columns | Yes |
| Status chips: `open / generating / defending / solved` | Yes |
| Named gaps clearly marked (not blank) | Yes |
| Catalog entry with at least 1 citation per technique | Yes |

### 11.2 Simulation Console Panel

| Element | Required |
|---------|---------|
| Synthetic ledger: schema-valid rows with `VID-SIM-*` IDs | Yes |
| Mule graph visualization (NetworkX export) | Yes |
| Fidelity badge: PSI pass/fail | Yes |
| Row counts by `label_family` | Yes |
| `sim_days` displayed (not silently truncated) | Yes |

### 11.3 Decisioning Panel

| Element | Required |
|---------|---------|
| Score stream with reason codes | Yes |
| Brake action (not binary only) | Yes |
| APP vs ATO differentiated actions | Yes |
| Mule payee `mule_credit_restrict` action | Yes |
| Latency measurement visible | Yes |

### 11.4 Arms Race Panel

| Element | Required |
|---------|---------|
| PR-AUC vs generation number | Yes |
| Evasion rate vs round | Yes |
| G-test baseline (different seed) vs G-eval | Yes |
| "Loop M" retrain event visible on timeline | Yes |

### 11.5 Coverage Map + Loop Panel

| Element | Required |
|---------|---------|
| `built / case_only / offline_loop / named_gap` for all 24 | Yes |
| Loop I: new catalog card → draft rule visible | Yes |
| Loop M: before/after metrics | Yes |
| HITL queue: approve / reject / edit | Yes |

---

## 12. Write-Up (`.docx`) Validation Checklist

This checklist ensures the submitted document satisfies PS requirements without overclaiming.

### 12.1 Required Sections

- [ ] **Novel fraud attacks identified:** Table of all 24 techniques; 5-category structure; citations per technique; honest `generate_mode` column
- [ ] **System generates and simulates those attacks:** Architecture diagram; label schema; fidelity gate results (PSI values, fraud rate band); anti-stub evidence (fan_in_1h independence test)
- [ ] **Detection and mitigation model with efficacy results:** PR-AUC by family (**headline G-test**; G-eval diagnostic); TPR at FPR 0.1%/0.5%/1% at inner-val `op_threshold`; genuine FPR; APP ablation; latency p50/p99; Loop M before/after
- [ ] **Real-world feasibility in live payments:** Latency disclaimer; APP vs ATO Brake policy; graph feature causality; governance loop with HITL; honest limits

### 12.2 Forbidden Phrases in Write-Up

| Phrase | Replace with |
|--------|-------------|
| "99.9% accuracy" | PR-AUC and TPR@FPR |
| "Beats production fraud detection" | "Research lab prototype demonstrates the loop" |
| "This is live UPI data" | "Synthetic calibrated world; priors from public aggregates" |
| "AUC of 0.99" | "PR-AUC of X.XX at Y% fraud rate on G-test" |
| "We detect all 24 attacks" | Coverage table with build/named/gap status |
| "PSI proves we match real UPI" | "PSI confirms sampler quality vs our own priors" |
| "Cat 4 evasion API" | "Offline loop; no public red-team API" |

---

## 13. Pre-Submission Validation Checklist

Run this checklist before finalizing the submission.

### 13.1 Code Repository

- [ ] `pytest -m "not live_llm and not live_identify"` passes (do not treat an old “65 passed” count as a gate)
- [ ] Train Parquet denylist test passes (no `vector_id`, `technique_id`, `is_authorized_push`, etc.)
- [ ] `label_family` not in `{T01, …, T24}` test passes
- [ ] Anti-stub: `fan_in_1h` independence recompute test passes
- [ ] APP flags only on APP rows test passes
- [ ] Liveness NULL after onboarding test passes
- [ ] Canary 4-stage shared-ids test passes
- [ ] 50k-row smoke completes (marked `slow`)
- [ ] No live URLs or ID-shaped strings in committed files (CI grep)
- [ ] `SECURITY.md` present with capability card
- [ ] `.env.example` has no committed secrets
- [ ] `make demo` runs end-to-end from seed to score

### 13.2 Detection Metrics (Defend done-gate)

- [ ] PR-AUC by family computed and recorded in `metrics.json`
- [ ] TPR at FPR 0.1% / 0.5% / 1% recorded
- [ ] Genuine FPR recorded (not confused with 1−Precision)
- [ ] APP ablation: with vs without session flags recorded
- [ ] G-test (seed ≠ train seed) PR-AUC is the **headline**; G-eval recorded as diagnostic only
- [ ] Entity mule recall (account-level, not edge-level) recorded
- [ ] AuthGate p50/p99 ms logged

### 13.3 Loop M (one demonstrated iteration)

- [ ] Miss family identified from **G-dev 44 or diagnostic/inner_val, never G-test 43**
- [ ] Loop-M rows added to G-train only (not G-test)
- [ ] Champion retrained with identical recipe (seed, features, class weight)
- [ ] G-test AP comparison: before and after Loop M
- [ ] Genuine FPR comparison: before and after Loop M
- [ ] Result documented: improvement / equal / documented failure

### 13.4 Coverage and Honesty

- [ ] Coverage table (§4) accounts for all 24 techniques
- [ ] Zero `Missing` entries
- [ ] Named gaps have explicit "requires X rail/signal not available" statement
- [ ] Lab fraud rate stated as oversample (≠ India prevalence)
- [ ] HoldoutVault dataset links verified before citing in .docx
- [ ] No "beats production" claim in write-up or UI

---

## 14. Summary Score Card

This is the honest assessment of where the system stands as of Phase 1a / Plan 08 implementation, as a senior ML scientist reviewing the system.

| Criterion | Current state | Honest score | Path to improvement |
|-----------|--------------|--------------|---------------------|
| **Diversity of attacks** | 29 seed rows; T01–T24 all mapped; 5 categories; citations on most | ★★★★☆ | Verify external holdout links; add 2–3 more Identify agent runs |
| **Fidelity of simulation** | PSI gates defined; canary chain correct; anti-stub tests pass; amounts lognormal | ★★★★☆ | Merchant collusion (T06) remains named gap; hour prior is assumption |
| **Detection efficacy** | Defend framework locked; metrics defined; honesty gates clear | ★★★☆☆ | Defend not yet executed; metrics pending; APP ablation critical |
| **Novelty** | Closed-loop LangGraph; Brake policy differentiation; graph features; canary governance | ★★★★☆ | Cat 4 arms-race chart needs actual rounds; Loop M needs live run |
| **Real-world feasibility** | Latency story correct; LLM off hot path; APP≠ATO documented; HITL | ★★★★★ | Cleanest claim in the system; well-architected |
| **Safety** | No live rails; allowlisted; Oracle Guard; no criminal tooling | ★★★★★ | SECURITY.md needs to be written |

**Overall honest assessment:** This is a research-grade system architecture with rigorous non-negotiable gates. The Identify and Generate pillars are well-validated at the simulation level. The Defend pillar has a strong specification but needs metrics from actual training runs. The key weakness for the demo is that APP detection without behavioral biometric signals is genuinely hard, and the ablation will show this — which should be framed as an honest finding, not a failure.

**The system's strongest story:** *The closed loop is real — misses from the defender retrain the generator's next attack generation, and the loop cannot grade its own homework (G-test is a different seed). That architecture is sound.*

---

*Last updated: 2026-08-28. Sources: `ARCHITECTURE.md`, `defense_architecture.md`, `feedback-loop.md`, `decisions.md`, `Docs/plans/08-generate-world-build.md`, `Docs/plans/02-defend-build.md`, `packages/sim/world.py`, `packages/sim/runner.py`, `tests/test_sim_inject.py`, `Docs/identify_built.md`, `Docs/reports/phase-1a-evidence.md`, `MC_PS.md`.*
