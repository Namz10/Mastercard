# Plan 02 — Generate, Defend, and the closed loop (locked)

**Status:** LOCKED.

**Depends on:** [`00-correct-planning-defects.md`](00-correct-planning-defects.md), [`01-identify-catalog-lock.md`](01-identify-catalog-lock.md) (`AttackSpec`, T01–T24, `simulatable_signals`).

**SSOT:** MC_PS Generate = high-fidelity simulation at scale; Defend = detect, **flag**, **mitigate**, max precision/recall/F1/AUC, **low FP** on genuine; gaps feed new attacks. HACKATHON_RESEARCH: benign world + perturbation; APP ≠ stolen-card; graph for mules; LLM off authorization; co-evolution (Kurshan).

[`decisions.md`](../decisions.md) Part B Generate/Defend is hereby **locked by this file** (no longer “proposed”).

---

## 1. Design principle

Two layers:

1. **World model (ShadowRail)** — synthetic customers, merchants (if present), devices, accounts, payee graphs, circadian spend. Calibrated to **public synthetic aggregates**, never production rows, never row-copy of Kaggle tables.
2. **Attack programs (injectors)** — discrete, testable, keyed by `simulator.injector_id`. They perturb the world. GenAI modalities appear as **simulated signals** (flags, scores), not real deepfake files.

Pattern (all categories):

```
LLM proposer (structured JSON, optional thickness)
    → deterministic engine (only code may accept a sample)
    → verifier (rail-rules; accept | reject-and-repair, bounded)
```

Realism comes from **domain rules + personas + verifier loops**, not from imitating a ground-truth fraud distribution we do not have.

---

## 2. Ledger envelope `gff.txn.v1`

Every event:

- `event_id`, `event_ts`, `rail`, `party_ids`, `amount_minor`, `currency`
- `label_class` (`economic_class` + fraud/benign), `label_ts`
- Typed payload by rail / category — **thin shared envelope**

**Forbidden on every row:** GSTIN + 3DS + VPA + transcript embedding concatenated. Feature views:

- `features_auth` — causal, production-available at time `t`
- `features_onboarding`
- `features_graph_asof` on `G(t−)`
- `features_dispute` / case

IDs: ULID; `VID-SIM-…` namespace; never real PAN/VPA/Aadhaar. `pan_token = hash(synthetic)` if a card-shaped field is needed for stretch CNP.

Suggested auth columns (synthetic): device_hash, is_new_device, is_new_payee, auth_method, is_customer_authorized, kyc_tier, account_age_days, seasoning_txn_count, windowed fan-in/out, burst_velocity, session flags (`call_active_flag`, `copy_paste_payee_flag`, `pause_ms`), simulated `voice_match_score` / `liveness_score` / `doc_consistency`, `beneficiary_changed`, `policy_action`, `explain_codes`, `attack_id`, `generation`, `label_family`.

Store Parquet partitioned by `run_id` / `generation`. DuckDB views for the API.

---

## 3. World and fidelity

- **Benign first.** Kirana small-ticket, salary calendar, stable payees, circadian hours — not `Uniform(1, 1e5)`.
- **UPI-like primary rail.** Instant credit-push; IMPS-like hops when modeling T04. Card auth plane is `name_only` unless stretch.
- **APP vs stolen.** APP: known device possible, OTP/biometric succeeded, new/mule payee, session coercion flags, `is_authorized_push=true`. ATO/CNP: new device, testing, cardholder did not intend.
- **Mules have TTL.** Fan-out then replacement; not immortal stars.
- **Cat 5 BEC.** Genuine-looking GSTIN/PAN **checksum** + **beneficiary change**. Amateur checksum fails are not the interesting case.

**Calibrators.** Prefer **SAML-D aggregates** for Cat 1 **if** URL, license, and typology codebook are verified (checklist §10). Else Sparkov / PaySim **aggregates** (amount, hour-of-week, fraud-rate band) as in V1, with write-up honesty: those sets **lack GenAI typology labels**. Never row-copy. IEEE-CIS optional/heavy — not v1-blocking.

**Fidelity gate (fail Generate job if over threshold):** KS or PSI on amount and hour-of-week vs priors; fraud rate in a declared band (e.g. 0.1–2% depending on mix); no future leakage in features. UI badge: `fidelity: pass|fail`.

**RNG:** seeded numpy/pcg64. Reproducible: `--seed 42`.

---

## 4. Injectors and agent thickness

| Order | Injector | Cat | LLM thickness | Engine |
|---|---|---|---|---|
| 1 | `identity_trajectory` | 2 | Strong: persona / `next_prompt` | Daily state `s_t`, ~150d seasoning → burst; structured repair |
| 2 | `graph_mule` | 1 | Thin: typology params only | Topology, balances, caps; **LLM must not emit the edge list** |
| 3 | `app_session` | 3 | Strong optional; v1 may be **templates** | Attach payment + biometric/session flags; victim **resistance policy** is a state machine, not a tool-using helper |
| 4 | `doc_beneficiary` | 5 | Minimal: narrative fields | Reuse Cat 2 validators; PAN/GSTIN/amount in **code** |
| 5 | Cat 4 Loop A | 4 | Strong JSON patch | Apply + feature mask + `query_automl`; **uncompiled until AuthGate exists**; offline |

T06 merchant collusion: only if ShadowRail has merchant nodes; else named gap (Plan 01).

T07 CNP/BIN: not v1 injector. Stretch after closed loop: proxy injection into a synthetic auth log (velocity, decline clustering) — still not ISO-8583.

**Public Cat 3 output:** labeled simulation transcripts + technique tags, **not** operator playbooks. Hinglish templates preferred for demo; LLM generation allowed offline with capability limits.

---

## 5. Two Generate modes (same schema)

| Mode | Trigger | Behavior |
|---|---|---|
| **Population** | Default sim | Sample Atlas rows with `status` in {`open`,`generating`} and `generate_mode=generate`, weighted by rail/family; injector reads `simulatable_signals` |
| **`canary_mode`** | UI or `sim --mode canary --vector-id X` | Pin **all** attack parameters to one `canary_eligible` row or the FinCEN **campaign** (T09 flags → T11 → T13 → T02). Log detection outcome **per lifecycle stage** |

Canary accounts are **synthetic** entities in the same sandbox. This is **not** HoldoutVault.

---

## 6. Defend — two planes, one model family

Authorization is a **latency + feature** problem. Mastercard-shaped story: tens of ms model, ≤300 ms envelope. **Never put an LLM on the hot path.**

| Plane | Budget | Inputs | Output |
|---|---|---|---|
| **AuthGate** | 50–300 ms story | `features_auth`: velocity as-of t, new payee, session flags, windowed degree/fan-in/out, burst, **stale** mule prestige | Score, calibrated p, reason codes |
| **CaseScore** | Seconds–batch | Windowed graph, seasoning, Cat 3 text if any, Cat 5 fields | Case priority, typology, dispute lock |

**Champion recipe (locked):** FLAML (or Optuna) selects **LightGBM / single GBDT**. Objective **PR-AUC** (average precision), not accuracy. Imbalance: `scale_pos_weight` / FLAML resampler — choose one recipe and freeze it in `models/features.json`. Time-based split.

**Optional overnight:** AutoGluon `best_quality` as **challenger** on the same views. If it wins, **distill** to a single model for AuthGate. Never serve a heavy stack on the demo hot path.

**Not v1:** GNN as the live scorer; LLM classifier; AutoGluon on the laptop during the live demo; one model per attack via AutoResearch.

### 6.1 Causal graph features

For payment `i` at time `t`:

- Snapshot `G(t−)` = posted txns with `time < t`.
- Ego window: 1–2 hops, τ ∈ {1h, 24h, 7d}.
- Features: in/out degree, fan-in/out **in window**, burst, local clustering on the **windowed** subgraph.
- Prestige: **batch** personalized PageRank from previously risked mule seeds, read as a **stale** node attribute — never PageRank on the completed simulation.

**Leakage test:** recompute with full graph vs `G(t−)`. If AUC collapses, training cheated. Split by time / component, not random rows on a graph.

### 6.2 Cat 3 task split

- **Auth label:** coerced / APP-risk payment **in progress**. Features: call-in-progress, paste-on-payee, pause, new payee, amount vs history.
- **Generate / investigation:** full script + persuasion labels. Report two numbers; do not mix. Do **not** lead Cat 3 with AUC if the only text holdout is Western corpora.

Sentence-transformer embeddings are **not** concatenated into AuthGate. Optional handful of probe scores; full dialogue is CaseScore.

### 6.3 LLM case extractor (not live-path)

Schema `case_signals.v1`: `coercion_likely`, `beneficiary_change_claimed`, `urgency_pressure`, `impersonation_claimed`, `evidence_spans`, `abstained`. Validate types; version prompt+model with the row; never overwrite trusted txn fields; treat input as hostile. AutoML must be tested with signals present, missing, and abstained. If live decision collapses without them, they stay case-only.

### 6.4 Brake (mitigation — the product)

| Band | Action | Must not |
|---|---|---|
| Low | `allow` | Experiment on genuine kirana/rent |
| APP elevated | `notify` + optional Yes/timeout; `step_up` on new VPA | Silent hard decline of known payee |
| High victim-side APP | `hold` / lagged credit analog | Treat UPI as card chargeback |
| High ATO / CNP | `decline` / session kill | Mix labels with APP |
| Mule payee | Restrict **credit**: cap, freeze fan-in | Only score the sender |

Actions enum: `allow | notify | step_up | hold | decline | mule_credit_restrict | case`.

SHAP TreeExplainer → deterministic reason codes; LLM may polish analyst text **grounded in codes only**.

### 6.5 v0 rules (before any training)

Source: [`feedback-loop.md`](../feedback-loop.md) §2 (~12–15 rows). Must include **hard flags, nudges, and calm-downs**. Calm-downs come from the **genuine** world (known payee, usual amount, old device), not from the fraud catalog.

No fake live rule for deepfake **video**, live crypto cash-out, or network-scale BIN testing — those stay catalog `name_only` / case. Merchant-pair collusion is a hard flag **or** a named gap if the sim has no merchant nodes.

Live order: **rules → AuthGate (sees rule-hit bits) → Brake**. LLM is case tab / drafts only.

Rule form: conditions + kind + reason + `technique_id` + `economic_class`. Not Python. Promotion uses §8 gate.

---

## 7. Cat 4 / Loop A (red team, not a fifth detector)

Partition columns:

- `X_adv` — attacker-mutable under budget (amount jitter, mule among owned accounts, device rotate).
- `X_env` — bank-computed, frozen (account age, batch PPR, historical velocity).
- `X_forbidden` — generator IDs, full-graph stats, future edges, post-auth transcripts.

Patches apply **only** to `X_adv`, then **rail-rules**. Report evasion only on verifier-accepted rows.

Use constrained tabular attacks (TabAttackBench-style, projected onto valid domain) as a lower bound **and** LLM JSON patches as the narrative. **Oracle Guard:** query cap; quantized/demo scores; never return SHAP/trees to the attacker.

**Public prototype:** do not expose Cat 4 as an unauthenticated API. Replay a recorded arms-race chart is enough on stage.

Poisoning (T21): verifier admission; trust tiers `human_gold | synth_verified | loop_evasion`; HoldoutVault veto if real-proxy / genuine FPR jumps; near-dup caps; Identify tickets need citation + rail constraint.

---

## 8. LoopGovernor, splits, and `solved`

```
Atlas → ShadowRail family A → G-train → fit champion M*
     → family A new seeds → G-dev → Cat 4 search, thresholds
     → family B / frozen engine → G-test     }  reported metrics
     → optional verified public tables        }  HoldoutVault
     → LoopGovernor: verified evasions into G-train only (mix cap ≤15%)
     → challenger M' vs M* on HoldoutVault
     → promote or reject; mark solved only on G-test stability
```

**Forbidden:** same generator + random 80/20 as holdout; adding Cat 4 wins to G-test; training on `generator_id` / `persona_id` / `patch_round`; auto-`solved` from ROC lift on G-dev.

**`solved` means:** ≥2 Cat 4 rounds with stable G-test; no genuine/real-proxy FPR degradation; typology transfer (a Cat 1 patch is not credited as a Cat 3 win).

**Promotion gate (rules and models):** genuine holdout FPR; frozen fake test (family B); human click (demo may auto-click once); version artifacts; rollback on HoldoutVault regression. Compare at the same alert budget. More alerts alone ≠ improvement.

---

## 9. Nine loops → LangGraph (locked mapping)

| Loop | Name | Graph placement | Demo bar ([`feedback-loop.md`](../feedback-loop.md) §8) |
|---|---|---|---|
| I | Catalog ↔ defense coverage | Identify Librarian + rule-draft tool | One card → one draft rule (scripted OK) |
| R | Analyser flags → rules | Post-score node; not hot path | One batch → one draft → pass/fail genuine test |
| T | Trees → readable rules | After train | A few paths; no `generator_id` conditions |
| M | Misses → more train | Defend/evolve | **Must work once** (miss → retrain → better catch) |
| A | Red vs blue Cat 4 | Subgraph uncompiled until champion | Offline; recorded chart OK on public site |
| F | Lab vs public vs friction | Eval node | Chart lab vs public-ish vs genuine action mix |
| C | Identify hunts holes | Coverage map + Scout topic | Map visible; don’t spawn CNP clones |
| H | Human overrides | Write-up / optional log table | Not production-scale |
| G | Generate uses defender feedback | Injector param search (nevergrad-class) | Proposer LLM optional; **code** builds |

Loop G numeric core: seasoning days, mule count, amount quantile, new-device rate — maximize miss rate **subject to fidelity constraints**.

---

## 10. Holdout verification checklist (before citing in `.docx`)

Until ticked, report **synthetic G-test family B** + proxy-injection protocol only.

| Dataset | Verify URL | License | Fit | Cite as scored holdout? |
|---|---|---|---|---|
| SAML-D | Kaggle page live | TOS OK | Transfer-graph typologies | Only after verify; entity-disjoint split |
| TransXion | Paper/GitHub 2026 | TOS OK | Map; drop FX if needed | Only after verify |
| MoMTSim V2 | — | — | Recalibrate; 52% fraud is a **toy prior** | Never lead with accuracy |
| BAF (NeurIPS 2022) | Feedzai | — | Identity tabular; **no India Stack** | State the gap |
| PaySim / Sparkov | Kaggle | — | **Priors only**, not product | Do not claim GenAI labels |
| Composite Scam Transcript / VISHGUARD | — | — | Language ablation only; not India APP AUC | Cat 3: κ + blinded review |

**Proxy injection (locked protocol):** ATO = IP/device shift + high-velocity UPI into legit baseline → TPR on injected anomalies. Card testing = distributed low-value probes, rotating device, BIN-clustered attempts into a synthetic auth log if stretch injector exists.

---

## 11. Metrics (order in dashboard and `.docx`)

1. PR-AUC / average precision **by typology** (APP, mule, ATO, CNP if any, BEC).
2. TPR at FPR 0.1% / 0.5% / 1%; precision at a review-capacity point.
3. Rupee cost sketch: missed fraud vs false friction (step-up cheaper than decline).
4. Calibration (ECE) if a 0–1000 score is shown.
5. AuthGate p50/p99 (champion, not AutoGluon stack).
6. Cat 4: verifier-accepted evasion vs query budget; post-retrain PR-AUC on frozen G-test.
7. Cat 3: Cohen’s κ vs blinded native speakers if available; LLM-as-judge secondary.
8. Entity-level mule recall (account/component, not only last edge).

Never lead with accuracy or F1 on a balanced toy mix.

---

## 12. Labels

Do not collapse the world into a single `is_fraud` without `economic_class` + `rail` + `label_ts`. Delayed labels: an AuthGate `allow` is not a genuine gold label. Store label source and time.

---

## 13. Generate/Defend success criteria

- Population sim produces schema-valid Parquet with APP and mule labels.
- `canary_mode` FinCEN chain logged per lifecycle stage.
- AuthGate + Brake visible in UI; APP hold vs ATO decline distinguishable.
- One Loop M retrain with HoldoutVault not worse on genuine FPR.
- Arms-race chart uses **HoldoutVault / G-test**, not G-dev self-score.
