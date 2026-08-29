# AegisLoop: A Closed-Loop Red/Blue Laboratory for GenAI-Powered Payment Fraud

**Mastercard Innovation Challenge @ Global Fintech Fest 2026**  
**Track:** AI Defense Lab for Payment Security  
**Product:** AegisLoop  
**Submission artifact:** Solution walkthrough (v1) — convert to `TeamName.docx` before upload

> **Fill before submission.** Team name (Kaggle + GitHub), all members’ full names, and the email IDs used to register on Luma/Kaggle. Kaggle requires the Word file to be named `TeamName.docx` and the public GitHub repository to use the same string. Those strings are not yet frozen in this repository.

---

## Abstract

Generative AI collapsed the cost of *believable* payment fraud—fluent lures, synthetic identities, voice clones, and mule networks that look ordinary one transaction at a time—while instant rails made recovery after the fact the exception, not the rule. Static rules and last year’s confirmed-fraud labels cannot see the two hardest classes of this era: **customer-authorized push-payment (APP) scams**, and **synthetic mule graphs that are individually in-distribution**. Mastercard’s brief is therefore not “train a classifier on a card dataset.” It is to industrialize the arms race: **identify** emerging GenAI payment attacks with breadth and depth, **generate** them at payment fidelity, **defend** with accurate low-false-positive detection *and* mitigation, and close the loop so that defense gaps become the next attack tickets.

**AegisLoop** is one laboratory, not three side projects. A machine-readable KillChain Atlas (24 techniques, T01–T24, grouped into five structural categories) is populated by an allowlisted Identify graph and a **29-row** grounded seed (22 `generate`, 7 `name_only`). ShadowRail first synthesizes a quiet UPI-like world, then injects four families of fraud as constrained perturbations of that world. AuthGate is a **batch** champion: it fits and scores a Generate run’s Parquet on pay-time columns with a compact gradient-boosted model; a v0 rule overlay supplies reason codes; Brake maps predicted family plus rule *kinds* to an action (allow / notify / step-up / hold / decline / mule-credit-restrict)—explicitly **never silently declining an APP victim**. Loop M retrains on a miss family, then reports transfer on a **new world seed** so the loop cannot grade its own homework. Language models are used where the problem is strategic (Identify curation and structured extraction). They are **not** on the scoring path. A per-payment HTTP “authorize this txn” endpoint and a CaseScore LLM path are specified, not shipped in v1.

This walkthrough is written as a research paper for judges: thesis, related work, architecture, comparative analysis against both the market and the modal competitor submission, evaluation protocol with honest gaps, feasibility under live-payment constraints, and a roadmap. Screenshots of the web prototype and architecture diagrams are called out by figure ID so they can be inserted before conversion to Word.

**Keywords:** generative-AI payment fraud; authorized push payment; synthetic identity; mule networks; closed-loop red teaming; causal graph features; policy-aware detection; co-evolutionary AI.

---

## 1. Introduction

### 1.1 The payment that looks genuine

A 43-year-old teacher in Ohio notices a \$12 streaming charge she does not recognize. It is small enough to ignore. Within 72 hours the account is drained through transfers designed to stay under the bank’s velocity thresholds. The rules said everything looked fine. That story, reported by LatentView Analytics (2026) as a composite of a now-common pattern, is the structural problem this challenge exists to address: **the fraud that does not trip yesterday’s rules because it was generated to look like a customer.**

On instant rails the same pattern is worse. The victim often *authorizes* the payment—OTP, biometric, UPI PIN. That is APP / credit-push scam fraud. A detector trained to find stolen PANs and unusual MCCs will score it as legitimate, because the customer did the authentication themselves. India’s National Cybercrime Reporting Portal figures, as cited in our landscape brief, moved from 2.6 lakh complaints in 2021 to 28 lakh in 2025, with reported value from ₹551 crore to ₹22,931 crore. At GFF, that is not background color. It is the room.

### 1.2 What Mastercard asked for

The Mastercard Innovation Challenge 2026 (GFF, Jio World Centre, Mumbai) asks teams to **build the attack, then build the defense**: one end-to-end red/blue system scored on (i) diversity of attacks identified, (ii) fidelity of simulation, (iii) detection efficacy, (iv) novelty, and (v) real-world feasibility in live payments. The problem statement’s winning idea is explicit:

> The attacks you generate become the training and stress-testing ground for the defense you build, and the gaps your defense reveals feed back into new attack ideas.

That is co-evolutionary AI. It is also the thesis of the paper included in the challenge pack—Kurshan, Mehta, Bruss, and Balch, *AI versus AI in Financial Crimes and Detection* (arXiv:2410.09066). Teams that only train a static tree model on IEEE-CIS or PaySim have missed the brief.

### 1.3 Product thesis

**AegisLoop is an AI Defense Lab: a red pipeline catalogs and simulates GenAI payment attacks at rail fidelity; a blue scorer and policy head act on compact causal features; a governor retrains only when an independent holdout still agrees; a console (in progress with teammates) is how an analyst watches the loop.**

The output is not a chatbot. It is a co-evolving red/blue system a network or issuer could sit *beside* Decision Intelligence-class scoring—with humans, holds, and explanations still in the loop.

---

## 2. Related work and the intellectual specification of the challenge

We did not start from a Kaggle card-fraud notebook. We started from the sources Mastercard put in the pack, plus two industry syntheses on GenAI-for-detection, plus a 2026 platform threat report that independently describes the same kill chain we encoded.

### 2.1 Co-evolutionary AI (Kurshan et al., 2024)

Kurshan, Mehta (BlackRock), Bruss (Capital One), and Balch argue that GenAI makes crime more personalized, faster, and more evasive, while bank model-risk-management cycles run in months to years. Criminal organizations adopt AI faster than institutions. Static models rot. The durable path they name is **AI-versus-AI that co-evolves**, plus graph methods over accounts/devices/flows, multi-modal models (language ↔ transactions), risk-aware authentication that *down-weights* biometrics criminals can now fake, synthetic scenarios for coverage of the tail, protection of the detector from poisoning and evasion, and industry data-sharing / federated learning.

They also state, plainly, that trillion-parameter GenAI is a poor bank detector: cost, hallucination, and governance. That sentence is why AegisLoop uses **small strategic LLMs + a strong tabular detector with causal graph *features***, not an LLM on the scoring path.

Estimates they cite (NASDAQ–Verafin 2024; Deloitte CFS) are industry reports, not audited facts. We use them as scale: ~\$485.6B global fraud/scam and bank-scheme losses; ~\$3.1T illicit funds through the financial system; Deloitte’s US GenAI-enabled fraud path of ~\$12.3B (2023) → ~\$40B (2027). We do not claim to have replicated those studies.

### 2.2 How institutions actually fight this (layered, not a silver bullet)

Wipro’s two-layer framing maps onto our architecture: **Layer 1** stop initiation / ATO (identity, device, liveness); **Layer 2** stop the money if Layer 1 fails (transaction monitoring, mule/payee intelligence, real-time hold). Wipro’s extra idea—train on GenAI-created synthetic scenarios for known schemes *before* they dominate production—is our Generate pillar.

Mastercard’s own product language (Decision Intelligence / DI Pro, Scam Protect) is the feasibility bar: score inside a **tens-to-hundreds-of-milliseconds** authorization envelope; use **network graph** intelligence rather than amount+MCC in isolation; treat **false-positive reduction** as a first-class metric; intervene on A2A *before* credit lands. Vendor lift claims (~20% average detection lift, large FP reduction in some portfolios) are **vendor claims**. The *design lesson* is what we took: latency, graph, FP, issuer still decides.

FinCEN Alert FIN-2024-Alert004 is encoded as a **canary campaign**, not as a blog citation: deepfake KYC → seasoning → APP inbound → mule cash-out. That composite is `packages/catalog/campaigns.py` and `packages/sim/inject/canary.py`.

### 2.3 GenAI for detection (LatentView; Master of Code)

LatentView (August 2026) and Master of Code (accessed 2026) describe the same dual use we built around: GenAI as **attacker simulator** (synthetic scenarios, deepfakes, novel patterns) and as **defender** (unstructured case narrative, analyst copilot, data augmentation). Both warn about explainability, adversarial robustness, privacy, and model drift. Both document that putting an ungoverned LLM on the decision path is how you harm genuine customers.

Where we diverge from the modal vendor blog: we **do not** claim GenAI “reasons about every payment in real time.” Scoring is a compact GBDT plus rules. GenAI is Identify (and, in the architecture, a future case tab). Numerical claims in those blogs (bank adoption percentages, “96% accuracy,” single-vendor savings) are **insufficiently sourced for headlines**; we use the articles for vocabulary and failure modes, not as audited benchmarks.

### 2.4 Meta H2 2026 Adversarial Threat Report (August 2026)

The PDF in this repository is Meta’s *Second Half Adversarial Threat Report* (August 2026; Google Docs renderer; 56 pages). We extracted the text with a PDF parser. The title says H2; the investigations described are primarily from the **first half of 2026**—we do not treat it as a complete H2 retrospective. Findings that drove product decisions:

1. **AI is both accelerant and countermeasure.** Scammers mass-produce profiles, fabricate imagery, and localize lures. Defenders who share the signals AI surfaces across the ecosystem keep the durable advantage. That is Loop I / Loop C in our lab: catalog coverage is a *shared object*, not a slide.
2. **The Fraud Attack Chain** (Build Infrastructure → Prepare Digital Assets → Engage → Execute → Clean Up) is the same lifecycle we encoded as Atlas `lifecycle_stage` plus a FinCEN *composite* canary, not 24 disconnected demos. Meta is explicit: **no single defender sees the whole scam**; banks, platforms, and telcos must map interventions to stages. AegisLoop’s KillChain Atlas is that map in machine-readable form. Meta also notes that, despite tactical AI advances, **AI has not fully automated the fraud enterprise**—human, technical, and organizational bottlenecks remain (opening convincing financial entities, moving money while preserving trust, laundering). That is why we keep HITL on taxonomy promote, why Generate is a deterministic engine rather than an unbounded crime agent, and why we do not claim the chain is “fully agentic.”
3. **Dormant inventory beats activity-only classifiers.** Meta reports disabling more than 575,000 predominantly dormant accounts assessed as pre-aged scam inventory. That is why Cat 2 seasoning trajectories exist, and why identity detection is not only “weird spend after login.” Account counts are **assets, not unique fraudsters**—we do not equate 575,000 rows with 575,000 crimes.

### 2.5 What this literature forbids us from building

- An LLM that *is* the detector.
- A GNN scored on the *finished* simulation graph (leakage).
- Training and reporting on the same generator seed.
- Dark-web Identify, live phishing, or criminal-model tooling.
- Accuracy on a balanced toy mix as the headline metric.

Those prohibitions are implemented as code, not as slide bullets.

---

## 3. Design thesis: deliberate decisions versus the modal competitor

Most teams will: prompt an LLM to write fake emails → dump `amount ~ Uniform(1, 10000)` “fraud” → train XGBoost → report 99% accuracy. That submission fails four of five scoring axes: thin diversity, cartoon fidelity, no FPR story, no loop, no live-payments latency/APP narrative.

We designed against that failure mode. Table 1 is the decision log judges should read before the architecture diagram.

**Table 1. Deliberate decisions (what we built, what we refused, why).**

| Decision | We built | We refused | Why it is better than the market default |
| --- | --- | --- | --- |
| Catalog vs pipelines | 24 techniques in 5 categories; 4 injectors | 24 generation pipelines | Diversity is a *coverage matrix*, not 24 half-finished scripts |
| Honesty of generation | `generate` vs `name_only` | Fake rules for deepfake video / BIN testing | Named gaps score diversity without lying about the sim |
| World first | Quiet UPI-like personas, circadian hours, amount mixtures | Fraud-only ledgers | Fraud is a perturbation of a believable baseline |
| LLM placement | Identify graph (curator/extractor); no LLM in `fit`/`score` | LLM on scoring | Measured ms/row; hallucination cannot decline rent |
| Features | Causal `G(t−)` running counts (fan-in/out, velocity, new payee/device) | PageRank on the finished graph; 384-d embeddings at auth | No leakage; scoring stays compact |
| Labels | `label_family` (normal / mule / app_fraud / ato / identity_burst / invoice_fraud) | Binary `is_fraud` | APP ≠ stolen-card; Brake can be honest |
| Mitigation | Brake enum, APP never silent-decline | Class label only | PS asks to detect, flag, *and* mitigate |
| Loop science | Loop M extra ≤15% on train copy; G-test = new `world_seed`; `solved` never auto-set | 80/20 shuffle as “holdout”; auto-solved from ROC lift | *The loop cannot grade its own homework* |
| Rules | Hard flags + nudges + **calm-downs** from the genuine world | Fraud-only rules | Calm-downs are how you do not block kirana and rent |
| Champion | sklearn `HistGradientBoostingClassifier` on a Generate run (batch) | AutoGluon/FLAML as the demo scorer; novel net; per-payment public API | Reproducible recipe; laptop p50/p99 measured; no ensemble on the demo path |

**Deck one-liners (locked in planning):**

- Generate: *One verification architecture, variable agent thickness — matched to what each fraud type requires for fidelity.*
- Defend: *One GBDT family, causal pay-time features, a policy head — matched to what each rail exposes at payment time. A slower case plane is specified, not shipped.*
- Loop: *The loop cannot grade its own homework.*

---

## 4. System overview

### 4.1 Named components

AegisLoop is the product. The control-plane names below appear in the UI and in this paper.

| Component | Pillar | Job |
| --- | --- | --- |
| **KillChain Atlas** | Identify | Postgres catalog of `AttackSpec` rows: rail, lifecycle, GenAI modality, economic class, `generate` vs `name_only`, dual-use rating, `features_expected`, status enum |
| **Identify graph** | Identify | LangGraph: Scout → Curator → Extractor → Grounder → TierScorer → Corroborator → Librarian → HITL |
| **ShadowRail** | Generate | Quiet world + four injectors + verifier + PSI/fidelity gate; synthetic IDs only (`VID-SIM-…`) |
| **PulseFeatures** | Defend | One-pass causal features; `features_auth` is the live view |
| **AuthGate** | Defend | Batch HGB champion on a Generate `run_id` + rule-hit bits; laptop ms/row (not an issuer SLA; **not** a per-txn HTTP auth API in v1) |
| **Brake** | Mitigate | Family + hits + score → policy action |
| **LoopGovernor (v1 = Loop M)** | Loop | Miss-family oversample on train only → challenger vs frozen G-test |
| **Holdout protocol** | Eval | Time cut 2/3 + entity holdout; G-test is a **new seed**, never the oversampled batch |
| **RedBlue Console** | UI | Planned judge UI (teammates). API already has threat-map, coverage, fit/score/loop-m |

**[FIG-AI-01 — System architecture.]** One diagram: Atlas → ShadowRail → PulseFeatures → AuthGate → Brake → Loop M, with dashed tickets back to Atlas. Annotate “LLM off this path” on AuthGate. Place after this subsection.

### 4.2 Scoring order (intended live path; v1 is batch)

The *product* order for one payment is:

```
Incoming synthetic payment
  → PulseFeatures as-of t  (past rows only; already on the Generate row)
  → v0 rules  (hard_flag / nudge / calm_down + reason codes)
  → AuthGate HGB  (allowlist columns + rule__* bits)
  → Brake  (policy_action)
```

v1 implements that order **inside** `fit_champion` / `score_run` over a Parquet fold (`POST /defend/fit`, `POST /defend/score`). There is no `POST /authorize` that scores a single payload. A case-tab LLM is architecture, not code. FIG-AI-02 should still draw the intended sequence; caption it as *lab batch today, issuer-shaped order tomorrow*.

**[FIG-AI-02 — One-payment sequence.]** Rules → HGB → Brake. Caption: *v1 runs this over a Generate run, not as a public per-txn API.*

### 4.3 Repository map (reproducibility)

| Path | Role |
| --- | --- |
| `data/catalog/seed.yaml` | 29 Atlas rows covering all T01–T24 (22 generate, 7 name_only) |
| `data/rules/v0_rules.yaml` | Nine live rules (7 fraud + 2 calm-down) |
| `packages/agents/identify_graph.py` | Identify LangGraph |
| `packages/sim/world.py`, `inject/`, `runner.py` | ShadowRail |
| `packages/eval/fit.py`, `brake.py`, `loop_m.py`, `split.py` | AuthGate, Brake, Loop M, splits |
| `apps/api/routes/{identify,generate,defend,catalog}.py` | FastAPI lab API |
| `models/features.json` | Frozen champion recipe |

Entry point: `./run.sh` (Postgres + pgvector, seed, gates, API on `:8000`). Offline CI: `make validate-all`. Live product check: `./run.sh --check` (Tavily + OmniRoute required).

---

## 5. Identify — exhaustive catalog, not a blog post

### 5.1 Job

Identify’s output is **machine-readable attack cards the generator can execute**, not a slide of “cool GenAI toys.” Diversity is scored as coverage of **lifecycle × rail × economic class**. Mastercard and GFF still *name* card / 3DS / network vectors even when Generate stays UPI-structured. That is `generate_mode: name_only`.

Each Atlas row (`packages/catalog/models.py`) carries: `technique_id` T01–T24, umbrella category 1–5, `lifecycle_stage`, `rail`, `genai_modality`, `control_bypassed`, `economic_class` (APP / ATO / CNP / mule / BEC / detector), `generate` vs `name_only`, `dual_use_rating`, citations, `simulatable_signals` (validated per injector), `features_expected` (the auth-plane contract for Defend).

Status machine: `proposed` → HITL approve → `open` → `generating` / `defending` → `solved`. A Defend miss **keeps `open`**. Dual-use fail → `rejected_unsafe`. Identify never calls AuthGate.

**[FIG-AI-03 — Identify LangGraph.]** Seven nodes in order, HITL interrupt after Librarian, allowlist cylinder (FinCEN, RBI, FTC, arXiv, …), pgvector nearest-neighbor for merge.

### 5.2 Pipeline (what actually runs)

1. **Scout.** Multi-collector: Tavily (budgeted), RSS, GNews, arXiv; airplane mode uses in-repo fixtures. Queries are validated against a **forbidden term** list (`dark-web`, `exploit payload`, `jailbreak-as-a-service`, …). A fixed search pack includes FinCEN deepfake KYC, RBI UPI APP, mule funnel, and arXiv `cs.CR` payment-fraud queries. Coverage gaps from Loop C can inject Scout topics.
2. **Curator.** LLM rank (optional; tier fallback if unconfigured) so we do not extract every URL.
3. **Extractor.** Structured `AttackSpec` JSON; Pydantic is the schema gate.
4. **Grounder.** Reject: no payment rail; buzzword-only (“GenAI fraud” with no control failed); exploit/unsafe patterns; within-run cosine > 0.92 clones.
5. **TierScorer.** `source_tier` from allowlist domain (FinCEN/RBI/FTC/Treasury/NPCI = 1; arXiv/DHS = 2; Feedzai/Wipro/Deloitte/BNY = 3; Reuters/BBC = 4). Unknown allowlisted host defaults to 4 until a human edits the table.
6. **Corroborator.** `vector_class`, `corroboration_type`, `canary_eligible` (confirmed + tier ≤ 2 + valid generate signals).
7. **Librarian.** Stage `proposed` rows in Postgres; merge only into an existing *proposed* row—never demote an `open` card. HITL payload includes nearest catalog neighbor via pgvector.

**[FIG-UI-01 — HITL queue.]** Screenshot: proposed card, citations, nearest neighbor, Approve / Reject / Reject unsafe / Edit.

### 5.3 The 24 × 5 taxonomy

**Table 2. Twenty-four techniques in five structural categories.** (Seed names from `data/catalog/seed.yaml`.)

| Cat | Structural shape | Techniques (seed names) | Generate? |
| --- | --- | --- | --- |
| **1 Network** | Graph: fan-in/out, smurfing, hops, dust | T01 Mule fan-in funnel; T02 Mule fan-out cash-out; T03 UPI-cap smurfing; T04 Rail hop UPI–IMPS–wallet; T05 Dust and layering; T06 Synthetic merchant collusion; T07 Card testing / BIN enumeration | T01–T05 generate (`graph_mule`). T06–T07 **name_only** (merchant nodes / card-auth graph not in v1 world) |
| **2 Identity** | Structured ID + seasoning time-series | T08 Synthetic identity mix; T09 Deepfake VKYC liveness bypass; T10 KYC document field forgery; T11 Identity farming seasoning; T12 ATO device session shift | Generate as **fields and trajectories**, not images or live liveness attacks |
| **3 Social / APP** | Session flags + linked payment | T13 UPI impersonation APP (India); T14 Family-emergency voice-clone APP; T15 Romance/investment long-con; T16 Voice-clone BEC CFO; T17 Polymorphic phishing/smishing; T18 Invoice-timed impersonation; T19 Live MFA-relay **class** (name_only) + MFA-relay **session signal** (generate) | Public output is flags + labels, **not** operator playbooks |
| **4 Detector** | The loop, not a fifth pipeline | T20 Detector evasion probing; T21 Training-data poisoning; T22 Detector fingerprinting; T23 KYC LLM supply-chain injection | **name_only** on the public API. Cat 4 is Loop M / offline adversarial, not a public “attack the scorer” endpoint |
| **5 Document** | Fields, checksums, beneficiary | T24 Beneficiary invoice rewrite | Generate: **checksum passes, account wrong** (the case that matters). No letterhead images |

The 29-row seed includes variants (RBI-scale UPI APP, rapid mule cash-out, seasoned bust-out, invoice rewrite linked BEC) that deepen coverage without inventing a second taxonomy. Seven cards are `name_only` (T06 merchant collusion, T07 BIN testing, T19 live MFA-relay *class*, T20–T23 detector/supply-chain). That is coverage honesty, not a missing pillar.

**[FIG-AI-04 — Threat map / taxonomy board.]** Five columns, T01–T24 chips, color by `open / generating / defending / solved / name_only`. This is also **[FIG-UI-02]** if the console already renders it.

### 5.4 Comparative analysis — Identify

| Approach | Typical hackathon | Vendor OSINT chatbot | AegisLoop |
| --- | --- | --- | --- |
| Output | Paragraphs | Unstructured “insights” | `AttackSpec` with injector contract |
| Safety | Open-web scrape | Often unscoped | Allowlist + forbidden queries + `rejected_unsafe` |
| Honesty | Everything “novel” | Everything “AI” | `confirmed` vs `reported-unverified`; `generate` vs `name_only` |
| Grounding | None | RAG without schema | Grounder + tier + pgvector dedup + HITL |
| Handoff | Copy-paste | Ticket in Slack | `features_expected` that Defend coverage-maps against |

---

## 6. Generate — ShadowRail: fidelity before spectacle

### 6.1 Pattern

```
LLM / catalog proposer (structured JSON, typology params)
        → deterministic engine (world + injector)
        → verifier (code first)
        → accept | reject-and-repair (bounded)
```

Realism comes from **domain rules + personas + verifier loops**, not from copying production rows. We never row-copy SAML-D or any live ledger. Calibration, when used, is **aggregates-only**.

**[FIG-AI-05 — Propose → enforce → verify.]** Three boxes with a reject-and-repair loop. Caption: *Variable LLM thickness; the engine is always the source of truth.*

### 6.2 Benign world first

`packages/sim/world.py` builds an event-driven quiet UPI-like world:

- Personas: salaried, kirana shopper, small business, young urban.
- Merchant categories: grocery, fast food, utilities, fuel, telecom.
- Amounts sampled from category priors and product caps—not `Uniform(1, 1e5)`.
- Hours sampled with circadian peaks.
- Party IDs reserved: `VID-SIM-C-*` customers, `VID-SIM-U-*` mules, `VID-SIM-APP-*`, `VID-SIM-CHAIN-*`, `VID-SIM-F-*` farmed identities.

Fraud is mixed at a **lab rate of 1–3%** of rows (`packages/sim/inject/mix.py`), with a default family budget: mule 40%, identity_burst 25%, APP 20%, invoice 10%, ATO 5%. That is an oversample for learning, **not** a claim that India runs at 2% fraud.

**[FIG-AI-06 — Quiet world then injectors.]** Left: circadian heatmap and amount mixture. Right: four injector glyphs landing as perturbations. Optional **[FIG-UI-03 — Simulation console]** showing ledger + counts by `label_family`.

### 6.3 Four injectors, not twenty-four pipelines

| Injector | Families | What the engine enforces |
| --- | --- | --- |
| `graph_mule` | mule (T01–T05) | Fan-in computed from **edges**, never copied from YAML; smurf under caps; hops; dust; cash-out to a sink MCC |
| `identity_trajectory` | identity_burst (T11), ato (T12) | Seasoning clamped to `sim_days`; device-hash shift for ATO; liveness/doc scores as **fields** |
| `app_session` | app_fraud (T13–T18, T19-signals) | Session flags **only on APP rows**; victim device unchanged (the APP tell); new mule payee; amount vs P30 elevated |
| `doc_beneficiary` | invoice_fraud (T24) | Valid GSTIN checksum **and** `beneficiary_changed=true` |

Cat 3 public simulation is **flags**, not a vishing toolkit: `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`. Those flags are lab instruments. They are **not** an issuer SDK. Defend’s APP ablation is required to say so (Section 8).

### 6.4 Causal features (PulseFeatures)

`packages/sim/features.py` is O(n): one pass over time-ordered events. For transaction *i* at time *t*, counts use only events with timestamp `< t`. Snapshot columns include `account_age_days`, `payee_history_count`, `amount_vs_p30`, `fan_in_1h`, `fan_out_1h`, `is_new_payee`, `is_new_device`, `burst_velocity`, plus APP flags when the row is APP.

Leakage test (architecture lock): recompute with the full graph vs `G(t−)`. If AUC collapses, training cheated. Splits are by **time and entity**, not `sklearn.train_test_split` on shuffled rows.

**[FIG-AI-07 — Causal G(t−).]** Ego window at payment time vs illegal “finished graph” PageRank. Mark the illegal edge in red.

### 6.5 Fidelity contract and canary

A population run is not accepted on `event_count > 1`. `packages/sim/fidelity.py` gates:

- PSI on log-amount histogram vs this run’s priors (max 0.25).
- PSI on hour-of-day vs circadian weights (max 0.35).
- Fraud rate in [0.5%, 3.5%].
- Mule fan-in median at least 5 (anti-stub).
- Verifier: non-positive amounts and use-before-create; reject-rate flood if >20% of rows fail.

**Canary mode** pins FinCEN FIN-2024-Alert004 as one chain on a shared `VID-SIM-CHAIN` account: T09 onboarding → T11 farming → T13 APP inbound → T02 cash-out. That is the “novel” the brief asked for: **a combination of GenAI + a real rail weakness**, not science fiction.

**[FIG-AI-08 — FinCEN canary chain.]** Four stages on one synthetic account, mapped to Atlas vector IDs. Optional **[FIG-UI-04 — Canary inspector]**.

### 6.6 Train artifacts (what Defend is allowed to see)

Per `run_id` under `data/runs/<id>/` (gitignored):

| File | Contents | Who reads |
| --- | --- | --- |
| `train.parquet` | Allowlist only (rail, KYC tier, causal features, APP flags, `label_family`) | Model X / y |
| `split.parquet` | `event_id`, `event_ts`, payer, payee, amount, `label_family` | Time cut, entity holdout, mule-account recall. **Never concatenated into X** |
| `sidecar.json` | knobs, technique ids, fidelity, seeds | Humans and Loop M. **Not** model features |

Denylist (must never enter X or public JSON): `vector_id`, `injector_id`, `technique_id`, `simulatable_signals`, `persona_type`, `world_seed` as a feature, transcripts, `is_authorized_push`, `economic_class`, GSTIN strings, payloads.

### 6.7 Comparative analysis — Generate

| Generator | Fidelity | Leakage risk | Dual-use | Judge tell |
| --- | --- | --- | --- | --- |
| LLM writes transactions | Low | High (model memorizes prompt ids) | High | Uniform amounts, no circadian |
| GAN/CTGAN on a public card set | Medium tabular | Train/test from same GAN | Medium | No APP, no UPI, no graph |
| PaySim / MoMTSim as-is | Toy structure | N/A | Low | 50%+ artificial fraud rate if used raw |
| **ShadowRail** | World + typed injectors + PSI | Split artifact separate from X | Capability-limited | Fidelity JSON on the API |

---

## 7. Defend — score, flag, mitigate

### 7.1 What “defend” means here

When a payment happens we need (1) a **risk score**, (2) a **short reason** a human can read, (3) an **action**. APP needs a different action than ATO. We do not output only `fraud / not fraud`.

v1 scoring finishes in **milliseconds per row on the demo laptop** as in-process `predict_proba` over a batch (`authgate_ms` in the fit JSON). Language models do not sit between rules and the table model. Loop I drafts rules from catalog cards; it does not execute Python.

### 7.2 v0 rules (the rule file is not empty on day 0)

Rules are translations of catalog *shapes* onto fields we can compute at payment time. Attacks we cannot see at auth (deepfake video pixels, live crypto off-ramp, BIN testing) get **named gaps**, not fake rules.

Nine live rules in `data/rules/v0_rules.yaml`:

| ID | Kind | Applies | Shape |
| --- | --- | --- | --- |
| `call-and-paste-new-payee` | hard_flag | APP | Call + paste + new payee |
| `new-payee-large-new-device` | hard_flag | ATO | New payee + new device + amount vs P30 |
| `mule-fan-in-burst` | hard_flag | mule | `fan_in_1h ≥ 6` |
| `smurf-under-cap` | nudge | mule | Repeated inbound, small vs usual |
| `rail-hop-burst` | nudge | mule | Rapid outbound |
| `seasoning-burst` | nudge | ATO | Burst on a seasoned account |
| `invoice-beneficiary-swap` | hard_flag | BEC | Beneficiary changed **and** GSTIN checksum OK |
| `pause-paste-session` | nudge | APP | Long pause + paste |
| `calm-down-known-usual-device` | calm_down | genuine | Known payee, usual amount, same device |

Loop I drafts a v0-style rule (or a named gap) from a catalog card. Loop C publishes a 24-technique coverage map: `live_rule | draft_rule | named_gap | case_only | empty`. Empty cells become Scout topics. **Auto-draft yes. Auto-promote no.** YAML `min_score` is stored and returned by the API; **Brake does not consume it**—actions use predicted family, rule *kinds*, and two frozen thresholds (`ATO_DECLINE_SCORE = 0.5`, `APP_HOLD_SCORE = 0.65`). We state that so judges do not think unused fields are a second scorer.

Invoice predicates (`beneficiary_changed`, `gstin_checksum_ok`) fire through the **rule engine’s payload flatten**. They are **not** on the HGB train allowlist. Cat 5 detection in v1 is therefore rule-path plus family score, not a learned GSTIN column. That is a named limitation, not a hidden one.

**[FIG-AI-09 — Coverage map.]** 24 cells colored by coverage status. **[FIG-UI-05]** if the console renders `/defend/coverage-map`.

### 7.3 AuthGate champion

Recipe (`models/features.json`): `HistGradientBoostingClassifier`, `max_depth=3`, `max_iter=80`, `learning_rate=0.08`, class weights from **this run’s** base rate, objective `average_precision`, y = `label_family` (multiclass). Rule hits are attached as `rule__<id>` bits so the model can learn the overlay rather than fighting it.

Operating point: TPR at FPR **0.1% / 0.5% / 1%**; default threshold from **1% FPR** on the eval fold after a **time cut (first 2/3 calendar) plus entity holdout** (mule payees and a fraction of customers held out even if they fall in the first 2/3). `op_threshold` is not mined from G-test.

Latency is **measured** as in-process `predict_proba` p50/p99 ms/row on the laptop, with a hang guard (120s per 1k rows). The JSON note is explicit: *“Laptop in-process predict. Not a Mastercard issuer SLA.”*

Explainability in v1 is **rule ids + predicted family + Brake action**, plus a correlation top-5 in the fit JSON—not SHAP. Architecture mentions SHAP-to-reason-codes; that is not implemented. We do not return trees or SHAP to any attacker surface.

### 7.4 Brake (the product, not the class label)

`packages/eval/brake.py` maps predicted family + rule kinds + score:

| Situation | Action | Why |
| --- | --- | --- |
| Mule (model or rule) | `mule_credit_restrict` | Stop the *credit* side, not only the victim |
| Calm-down and no hard flag | `allow` | Do not block kirana/rent because the model is noisy |
| APP | `hold` if hard/high score else `notify` | Customer-authorized: friction, not silent decline |
| Invoice / BEC | `hold` or `case` | Dual-control analog |
| ATO | `decline` or `step_up` | Stolen session is not APP |
| APP path that would decline | Forced to `hold` (`app_no_decline`) | Product disaster otherwise |

**[FIG-AI-11 — Brake policy table.]** Same table as a visual. **[FIG-UI-06 — Decisioning stream]** with score, reason codes, and Brake chip.

### 7.5 APP ablation (honesty as a feature)

Synthetic session flags are powerful and **not available as a production SDK** unless the issuer instruments the app. Fit therefore reports average precision **with** and **without** `call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`. If APP detection dies without flags, that is documented, not hidden. Headline APP claims must be read next to that ablation.

### 7.6 Comparative analysis — Defend

| Stack | Latency story | Explainability | APP | FP control |
| --- | --- | --- | --- | --- |
| Rules only | Excellent | Excellent | Misses fluent scams | Loud |
| LLM classifier | Poor / unbounded | Weak | Theatrical | Hallucinated declines |
| Deep net / GNN at auth | Often misses the envelope | Weak | Maybe | Leakage if non-causal |
| AutoGluon `best_quality` live | Heavy ensemble | Opaque | Unspecified | High ceiling, wrong plane |
| **AuthGate + rules + Brake** | Compact GBDT, measured ms/row | Rule ids + family + action | Hold/notify, ablation reported | Calm-downs + genuine FPR metric |

We align with Mastercard DI *vocabulary* (score, reason codes, graph-adjacent features, FP) without claiming network-scale production.

---

## 8. The closed loop — science, not a self-licking ice cream

### 8.1 Loop M (the v1 arms race)

```
Atlas card open
  → ShadowRail population (seed 42) → fit champion M*
  → miss family extra mix (new seed, cap ≤ 15% of train rows)
      appended to a TRAIN COPY only
  → G-test population (seed 43, same n_customers / n_merchants / sim_days)
  → score M* vs M' on G-test
  → pass if family AP improved or equal (ε = 0.05) AND genuine FPR not worse (ε = 0.02)
  → catalog_solved remains False
```

Extra event IDs are asserted **not** to appear on G-test. `solved` is a human/stability concept after repeated non-degrading rounds—not a ROC tick. That is the sentence Kurshan et al. would recognize as co-evolution **with governance**.

**[FIG-AI-12 — Arms race / Loop M.]** Two bars: AP_before vs AP_after on G-test; genuine FPR beside them. **[FIG-UI-07 — Arms-race chart]** from the console.

### 8.2 Loops named vs loops shipped in v1

The architecture names nine loops (I, R, T, M, A, F, C, H, G). **v1 ships I, C, and M**, plus the miss path that keeps Atlas `open`. Analyser (R), tree extraction (T), and Cat 4 query-capped evasion sit in the roadmap. We would rather show **one honest loop** than nine empty boxes.

### 8.3 Comparative analysis — loops

| Claim | Typical team | AegisLoop v1 |
| --- | --- | --- |
| “We retrained on misses” | Same CSV, shuffled | New world seed; extra cap; denylist |
| “Solved” | Accuracy went up | Never auto-set |
| “Adversarial ML” | FGSM on all columns | Cat 4 is **named_gap** in v1; Loop M oversamples miss *families*, it does not patch attacker-mutable fields |
| “Closed loop” | One generation | Miss → oversample → G-test comparison object |

---

## 9. Safety, dual-use, and ethics

MUST (implemented):

1. No live rails, real customers, real VPA/PAN/Aadhaar payloads.
2. No images, audio, APKs, or outbound phishing.
3. LLM keys server-side; Identify queries allowlisted; exploit-pattern Grounder reject.
4. Generator inputs treated as untrusted; output is schema; verifier is code.
5. Cat 4 (detector probing / poisoning / fingerprinting / supply-chain) is **taxonomy + offline**, not a public attack endpoint.
6. Loop cannot mark `solved` without the G-test protocol; v1 does not auto-promote.
7. Synthetic namespace only.

This is the opposite of “we used FraudGPT.” Criminal-market LLMs are named in the literature as a *phenomenon*. They are not a dependency.

---

## 10. Working prototype (web)

The submission requires a presentable UI that **shows the loop**, not a notebook. Teammates are iterating defense UX and the console in parallel with this document. The screens the architecture lock requires—and that judges should see in the demo—are:

| Screen | Judge should see | Figure |
| --- | --- | --- |
| Threat map | T01–T24, status chips, evidence spans | **FIG-UI-02** |
| Simulation console | Launch population/canary; ledger; mule graph; `fidelity.pass` | **FIG-UI-03**, **FIG-UI-04** |
| Decisioning | Score stream, reason codes, Brake action | **FIG-UI-06** |
| Arms race | Static blue vs Loop M on G-test | **FIG-UI-07** |
| HITL | Promote taxonomy / reject unsafe | **FIG-UI-01** |
| Analyst copilot | Case summary; LLM is **not** the detector | **FIG-UI-08** (planned; not in API today) |

**[FIG-AI-13 — Console information architecture.]** Six panes as a wireframe if screenshots are not yet final; replace with UI photos when ready.

Six-click demo script (rehearse with fallbacks): seed Atlas → Identify HITL approve → Generate population → Defend fit → inspect `score_run` action histogram + Brake on eval rows → Loop M once. API surface already exists: `POST /identify/run`, `POST /generate/population`, `POST /generate/canary`, `POST /defend/fit`, `POST /defend/score`, `POST /defend/loop-m`, `GET /defend/coverage-map`, `GET /catalog/threat-map`. Until the console lands, OpenAPI at `:8000/docs` is the runnable prototype surface—not a substitute for the PS web UI, which teammates are building.

---

## 11. Evaluation protocol and results

### 11.1 Metric hierarchy (lead with these)

| Lead | Support | Never lead with |
| --- | --- | --- |
| PR-AUC / AP **by family** | ROC-AUC | Accuracy |
| TPR at FPR 0.1% / 0.5% / 1% | F1 at the operating point | Balanced accuracy on a toy mix |
| Genuine FPR | ECE if we show a 0–1000 score | “This is live UPI” |
| Mule **entity** recall | Cost sketch (₹ missed vs friction) | “We beat production DI” |
| AuthGate p50/p99 ms/row | APP ablation with vs without flags | 99.9% with no FPR |

### 11.2 Lab diagnostics (pinned `run_id`: `defend-cd-http`)

These numbers are from an on-disk champion at `models/defend-cd-http/metrics.json` (and the Loop M train copy `models/defend-cd-http__loopm-train/metrics.json`). They are **demo-scale**: 913 train / 855 eval rows after time cut + entity holdout. Class weights on the first fit include `normal`, `mule`, and `invoice_fraud` only—APP/ATO/identity were too scarce in that mix for the model to have a dedicated weight. That is why APP AP on the first fold is ~0.008: **not** “APP is undetectable,” but “this population did not contain enough APP to learn.” We publish that rather than a vanity overall accuracy.

This is **not** a G-test (seed 43) transfer table. Loop M’s official comparison object lives on the `/defend/loop-m` response (`ap_before` / `ap_after` on a new population). The second column below is the **augmented champion’s own eval fold** after extra APP rows were appended to a train copy (cap ≤ 15%). Treat it as evidence that miss-family oversample *moves* APP AP, not as frozen G-test.

**Table 3. Champion diagnostics — `defend-cd-http` (lab, small-n).**

| Metric | Base champion (eval fold) | After APP extra on train copy | How to read it |
| --- | --- | --- | --- |
| n_train / n_eval | 913 / 855 | 919 / 855 | Demo world, not 50k-row scale |
| AP mule | 0.293 | 0.260 | Slight mule regression is expected when the extra family is APP |
| AP app_fraud | 0.008 | 0.444 | Mix-starved → oversampled; still eval-fold, not G-test |
| AP ato | 0.002 | 0.002 | Rare class in this world; do not headline |
| AP identity_burst | 0.011 | 0.011 | Same |
| AP invoice_fraud | 0.50 | 0.50 | Rule-path + family; GSTIN columns not in HGB X |
| TPR @ 0.1% / 0.5% / 1% FPR | 0.093 / 0.209 / 0.209 | 0.093 / 0.233 / 0.279 | Lead with low-FPR TPR, not accuracy |
| Genuine FPR at op (1% target) | 0.0082 | 0.0094 | Within Loop M ε = 0.02 if this were G-test |
| F1 at op | 0.305 | 0.381 | Secondary |
| Mule entity recall | 0.50 | 0.50 | Catch the mule account, not only the last edge |
| AuthGate p50 / p99 ms/row | 4.6 / 10.2 | 6.0 / 19.4 | Laptop in-process; **not** an issuer SLA |
| APP ablation AP (with / without flags) | null / null | 0.669 / 0.669 | Null on base = no APP mass; equal after extra ⇒ this fold is not a flags-only trick |

**Table 4. Loop M protocol (what the API returns; fill G-test cells from the next `/defend/loop-m` JSON).**

| | AP family | Genuine FPR | Verdict |
| --- | --- | --- | --- |
| Before (M* on **G-test seed 43**) | _paste `comparison.ap_before`_ | _paste `genuine_fp_before`_ | |
| After (M' on **same G-test**) | _paste `ap_after`_ | _paste `genuine_fp_after`_ | `ap_verdict`; `genuine_fp_ok`; `catalog_solved` remains false |

Do not substitute Table 3’s eval-fold columns for Table 4. That would be the loop grading a related homework set.

**[FIG-AI-14 — Metrics dashboard mock / actual.]** If the UI plots these, use **FIG-UI-09** instead of a generated chart.

### 11.3 What we do not claim

- Transfer to production UPI or Mastercard authorization logs.
- Evaluation on SAML-D / TransXion / BAF until download URLs and licenses are verified (still unset in `LOCKED.md`). Until then, **synthetic frozen G-test + documented proxy-injection protocol**.
- Cat 3 dialogue AUC as a headline (no India holdout corpus; session flags only at auth).
- That synthetic APP flags exist in every issuer app.
- That v1 is a live authorization service. It is a **batch lab** over Generate runs.
- That 24/24 techniques have a live detector. Coverage is mixed `live_rule` / `named_gap` / `case_only`.

---

## 12. Competitive positioning

### 12.1 Versus other hackathon submissions (predicted)

**Table 5. Predicted competitor archetypes vs AegisLoop.**

| Archetype | Identify | Generate | Defend | Loop | Feasibility tell |
| --- | --- | --- | --- | --- | --- |
| **Email-LLM** | 5 phishing variants | Text only | None / keyword | None | Dual-use smell |
| **Kaggle classic** | — | IEEE-CIS / PaySim | XGBoost, accuracy | None | No APP, no India rail |
| **Agent swarm** | Unbounded web | LLM ledger | LLM scores payments | Self-graded | Latency + hallucination |
| **GNN showcase** | Thin | Random graph | GNN | None | Auth-time infeasible; leakage |
| **AutoML blob** | Thin | One table | AutoGluon stack | Retrain on same split | No Brake, no named gaps |
| **AegisLoop** | 24/5 + HITL + allowlist | World + 4 injectors + PSI + FinCEN canary | Rules + HGB + Brake + ablation | Loop M on new seed | LLM off-path; APP hold; measured ms |

### 12.2 Versus the market (not a claim we replace it)

| Market capability | What we took | What we did not pretend to be |
| --- | --- | --- |
| Mastercard DI / Safety Net | Score + reasons + graph-adjacent features + FP as a product metric | 175B-transaction production; sub-100ms network SLA |
| Mastercard Scam Protect | APP is a different action; intervene before irreversible credit | UK A2A production coverage |
| Feedzai-class case AI | Analyst copilot *after* the score | LLM as the detector |
| NayaOne / synthetic data vendors | Privacy-preserving training ground | Certified synthetic-data product |
| Rules engines | v0 overlay + calm-downs | Rules as the only brain |
| Foundation LTM (Mastercard 2026 gen-AI engine, press) | Weak-signal genuine spend (wedding-ring class) is an FP problem | Training a payments foundation model |

AegisLoop is a **lab that sits beside** network decisioning: it produces typology-tagged synthetic stress, an explainable challenger, and a governed retrain loop. That is the talent-and-product-fit audition the prize size implies.

---

## 13. Impacts, benefits, feasibility, viability

### 13.1 Impacts

- **Coverage of the tail.** Institutions cannot wait for novel GenAI typologies to appear in labeled production. High-fidelity simulation is how the tail is seen *before* it dominates losses (Wipro; LatentView synthetic-data use case).
- **APP as a first-class class.** Liability is shifting (UK mandatory APP reimbursement; India discussion of digital-fraud compensation). Detection without hold/notify/trusted-person is incomplete.
- **Mule intelligence on the credit side.** Fan-in that is invisible one edge at a time becomes an entity-level recall problem—the graph lesson from Kurshan’s other body of work, implemented as *causal features*, not a 50 ms GNN.
- **Analyst leverage.** Reason codes + Brake + optional case summary compress investigation time (LatentView; Feedzai analog) without handing the decline to a chatbot.
- **Signal sharing analog.** Atlas cards with citations are a miniature of Meta’s FIRE / Industry Accord point: *no single defender sees the whole scam.* A bank, a network, and a platform can share *typology fingerprints* even when they cannot share raw PII.

### 13.2 Benefits (who gains what)

| Stakeholder | Benefit |
| --- | --- |
| Issuer / PSP | Stress-test before a typology is common; policy actions that match rail economics |
| Network | Lab for reason-code vocabularies and mule-credit interventions |
| Regulator / MRM | Audit trail: recipe JSON, split protocol, ablation, named gaps |
| Genuine customer | Calm-downs and APP-hold instead of false decline |
| Fraud team | Coverage map that shows what is live vs named vs case-only |

### 13.3 Feasibility in live payments (copy this logic onto the judging rubric)

- **Latency.** GenAI is off the authorization path. On-path = compact tabular + precomputed features. We **measure** laptop ms/row and refuse to quote Mastercard’s production envelope as our number.
- **Feature availability.** Session flags are lab-complete; production needs app instrumentation or they stay case-only (ablation).
- **Human in the loop.** High-value APP and commercial payments still need process controls (out-of-band callback). Brake’s `case` / `hold` exist for that.
- **Governance.** Auto-retrain is a **lab** with Loop M. Production would be champion–challenger + model-risk. We say that out loud.
- **Privacy.** Fully synthetic parties; no real PANs; no criminal LLMs.
- **Explainability.** Rule ids + predicted family + policy action. No SHAP export.
- **India / GFF.** UPI-like instant credit-push, APP impersonation, lagged-credit analog as `hold`, mule fan-in under product caps.

### 13.4 Viability (why this is a product, not a weekend toy)

The cash prize is small relative to GFF visibility. Viability is **whether a network or large issuer would keep the lab**. Three properties argue yes: (1) the catalog is the integration contract; (2) the champion is a boring, auditable GBDT; (3) the loop has a promotion gate that looks like MRM rather than a viral demo. Cost of Identify LLMs is budgeted (Tavily call caps, HITL caps). Cost of Generate is CPU. Cost of Defend at demo scale is in-process sklearn.

Risks to viability: uninstrumented APP flags; unverified external holdouts; Cat 4 left offline (correct for dual-use, incomplete as an “evasion rate vs query budget” chart). Those are in Section 15.

---

## 14. Research that drove the architecture (decision trace)

This section is the “related work → design” chain, so a judge can see we did not decorate a classifier with citations.

| Finding | Source | Decision in AegisLoop |
| --- | --- | --- |
| Frozen detection AI loses to co-evolving crime | Kurshan et al. 2024, §4.9 | Loop M + G-test new seed; `solved` not automatic |
| Criminals adopt AI faster; MRM is slow | Kurshan §3.1–3.2 | Lab loop is fast; production story is champion–challenger |
| Graph AI over flows beats single-txn mimicry | Kurshan §4.2 | Causal fan-in/out; mule entity recall; no live GNN |
| Down-weight forgeable biometrics | Kurshan §4.4, §4.7 | Deepfake VKYC is **fields / named**, not a vision model on the auth path |
| LLM cost, hallucination, poisoning | Kurshan §3.6; Amazon payments-security (landscape brief); LatentView challenges | LLM off-path; schema-gated extraction; denylist |
| Two-layer defense + synthetic training | Wipro | Identify/ATO layer vs money-movement layer; ShadowRail |
| APP / Scam Protect | Mastercard product narrative; RBI discussion (landscape brief) | Brake `hold`/`notify`; `app_no_decline` |
| FinCEN deepfake → mule cash-out | FIN-2024-Alert004 | Canary campaign T09→T11→T13→T02 |
| False positives kill issuers | Mastercard DI press; LatentView; Master of Code | Calm-downs; genuine FPR; PR-AUC not accuracy |
| No single defender sees the whole scam; Fraud Attack Chain | Meta H2 2026 ATR | Atlas lifecycle stages; Loop C coverage; HITL |
| AI accelerates scams but does not fully automate the enterprise | Meta H2 2026 ATR | HITL; capability-limited Generate; no unbounded crime agent |
| Elastic/industry bank-AI adoption percentages | LatentView citing surveys — **not independently re-fetched** | Used only as “GenAI is table stakes; placement is the differentiator” |
| Probe-under-threshold then drain | LatentView opening case | Velocity + amount-vs-P30 + mule fan-in, not a single large txn rule |
| Synthetic data without real PII | Master of Code (NayaOne analog); Wipro | ShadowRail synthetic namespace |
| Mid-tier AutoML vs full autoresearch | Internal Defend research (`HACKATHON_RESEARCH.md` AutoML annex) | HGB recipe, not AIDE/SELA rewriting the pipeline overnight |

Mastercard.com product pages and the Recorded Future annual payment-fraud article were **HTTP 403** from this environment (Akamai), matching the access note in `HACKATHON_RESEARCH.md`. We did not fabricate quotes from blocked pages. Secondary reporting (VentureBeat on Greg Ulrich / VB Transform 2026; Mastercard Europe “new gen AI engine” fetch succeeded) was used only for *vocabulary* (sub-100 ms scoring, agentic commerce rewriting bot-blocking rules, foundation-model FP on rare genuine luxury spend).

---

## 15. Limitations (winner-style: say what the numbers do not prove)

A working lab proves a system runs. The harder question is what it is allowed to claim.

1. **Prototype, not production.** No issuer integration, no NPCI/host connection, no certified synthetic-data regime. FastAPI is unauthenticated lab API.
2. **Holdouts.** External datasets named in early planning (SAML-D, TransXion, BAF) are **not** cited as evaluated until URLs/licenses are ticked. Reported transfer protocol is G-test (new seed); Table 3 is a small-n eval fold, not that gate.
3. **APP flags are synthetic.** Ablation is reported; on the pinned small run, APP was mix-starved until Loop M extras.
4. **Cat 3 language.** No blinded native-speaker study in v1; we do not lead with dialogue AUC.
5. **Cat 4.** Taxonomy + named gap. No Loop A, no Oracle Guard, no public score-query attack API.
6. **T06/T07.** Merchant collusion and BIN testing are named for diversity; the world does not yet have merchant-node cycles or card-auth graphs.
7. **Cat 5 vs HGB.** Invoice checksum/beneficiary flags are rule-path, not train-allowlist columns.
8. **UI.** Console is a PS requirement; this document ships the shot list. OpenAPI is not a substitute.
9. **Brake `min_score`.** Present in YAML, unused by `brake()`.
10. **TeamName.** Kaggle/GitHub string still unset.
11. **Explainability.** Correlation top-5, not SHAP.
12. **CaseScore / IsolationForest / AutoGluon.** Documented in older architecture forks; not in the v1 champion.

Adversarial inputs to Identify (poisoned OSINT) are bounded by allowlist and HITL, not solved as a research problem.

---

## 16. Future scope

Ordered by evidence, not by what is technically entertaining:

1. **Pin a scale Generate run** (not the 20-customer HTTP fixture) and paste true G-test Loop M JSON into Table 4.
2. **RedBlue Console** — blocking PS artifact; teammates’ track. Wireframe FIG-AI-13 until screenshots exist.
3. **Per-payment score endpoint** that applies the same allowlist + rules + HGB + Brake without retraining.
4. **Loop T / R.** Promote a single mined rule on genuine-FPR slack 0.002 without mixing APP and ATO in one rule; wire YAML `min_score` if the policy head should honor floors.
5. **Put Cat 5 booleans on a case/view allowlist** or keep them explicitly rule-only in the coverage map.
6. **Verified external holdout** (aggregates-only calibration, then transfer drop reported honestly).
7. **CaseScore plane.** Windowed graph + Cat 3/5 text as *investigation*, still not auth.
8. **Cat 4 offline.** Masked JSON patch vs frozen champion; Oracle Guard query cap; evasion only on verifier-accepted rows.
9. **SECURITY.md** and auth on the demo API before a public GitHub `TeamName`.
10. **Federated typology feed** (simulated consortium of Atlas cards)—Kurshan’s cooperation gap, without sharing customer data.

---

## 17. Conclusion

Generative AI did not invent payment fraud. It collapsed the cost of **believable identity, believable speech, and believable pressure**, while rails went **irreversible**. Static rules and last year’s labels cannot see customer-authorized scams or synthetic mules that look like people. Mastercard already fights this with network-scale, millisecond decisioning and scam-specific A2A intelligence. The challenge asked us to **close the loop they described**.

AegisLoop does that with a catalog that is honest about what it can simulate, a world that is quiet before it is attacked, a detector that scores like an issuer service rather than a chatbot, a policy head that refuses to treat APP as stolen-card, and a retrain protocol that is not allowed to grade its own homework. The output is not a viral agent. It is a **co-evolving red/blue laboratory** a network or bank could sit beside Decision Intelligence—with humans, holds, and explanations still in the loop.

Build the lab. Show the loop. Speak like a network.

---

## Team

| Full name | Luma email | Kaggle email |
| --- | --- | --- |
| _fill_ | _fill_ | _fill_ |

**Kaggle team name:** _fill_  
**Public GitHub:** `https://github.com/…/_TeamName_`

---

## References

1. Mastercard Innovation Challenge 2026 problem statement. This repository, `MC_PS.md`.
2. Kurshan, E., Mehta, D., Bruss, B., & Balch, T. (2024). *AI versus AI in Financial Crimes and Detection: GenAI Crime Waves to Co-Evolutionary AI*. arXiv:2410.09066.
3. FinCEN. (2024). *FIN-2024-Alert004* — fraud schemes involving deepfake media targeting financial institutions.
4. Wipro. *GenAI-driven Fraud: Confronting a New Risk for Financial Institutions.*
5. Feedzai. *What is GenAI fraud?*
6. BNY. *AI and payments fraud: an evolving landscape.*
7. Amazon Payment Services. *The impact of generative AI on security in the payments industry.*
8. LatentView Analytics. (2026, August 18). *Generative AI for Fraud Detection: Real-World Use Cases in Financial Security.* https://www.latentview.com/blog/generative-ai-for-fraud-detection/
9. Master of Code Global. *Generative AI for Fraud Detection: Mechanisms & Real-World Examples.* https://masterofcode.com/blog/generative-ai-for-fraud-detection
10. Meta. (2026, August). *Second Half Adversarial Threat Report* (H2 2026). Local copy: `Docs/H2-2026-Adversarial-threat-report_copy.pdf`.
11. Deloitte Center for Financial Services. Deepfake / GenAI fraud loss path (~\$40B US by 2027)—cited via Kurshan [27] and LatentView; treat as industry estimate.
12. NASDAQ–Verafin. (2024). *Global Financial Crime Report* — cited via Kurshan [43].
13. U.S. Treasury. (2024). *Managing Artificial Intelligence-Specific Risks in the Financial Services Sector.*
14. Mastercard. Decision Intelligence / Scam Protect product narratives — **direct mastercard.com fetch blocked (403)** in this environment; vocabulary from secondary reporting and the challenge brief.
15. VentureBeat. (2026). Coverage of Greg Ulrich (Mastercard) at VB Transform 2026 on rewriting bot-blocking risk rules for agentic commerce.
16. LangChain. LangGraph documentation (workflows, HITL, checkpointers)—implementation reference for Identify.

Attack content in this repository is **taxonomy-level**. No exploit procedures, phishing kits, or live tooling.

---

## Appendix A — Figure shot list (for Word layout, 10–15 pages)

Insert figures at the callouts in the body. Two kinds only.

### A.1 AI-generated (workflow / architecture)

| ID | Title | What to show | Where |
| --- | --- | --- | --- |
| FIG-AI-01 | AegisLoop control plane | Atlas → ShadowRail → Pulse → AuthGate → Brake → Loop M | §4.1 |
| FIG-AI-02 | Scoring sequence | Rules → HGB → Brake (batch today) | §4.2 |
| FIG-AI-03 | Identify graph | Scout…Librarian + HITL + allowlist + pgvector | §5.1 |
| FIG-AI-04 | Taxonomy board | 5 columns × T01–T24, generate vs name_only | §5.3 |
| FIG-AI-05 | PEV pattern | Propose → engine → verifier | §6.1 |
| FIG-AI-06 | World then inject | Quiet world + 4 injectors | §6.2 |
| FIG-AI-07 | Causal G(t−) vs leaked graph | Legal vs illegal feature compute | §6.4 |
| FIG-AI-08 | FinCEN canary | T09→T11→T13→T02 on one account | §6.5 |
| FIG-AI-09 | Coverage map | 24 cells live/draft/gap/case | §7.2 |
| FIG-AI-10 | Allowlist vs denylist | Train columns | §7.3 |
| FIG-AI-11 | Brake policy | APP hold ≠ ATO decline ≠ mule restrict | §7.4 |
| FIG-AI-12 | Loop M protocol | Extra on train; G-test new seed | §8.1 |
| FIG-AI-13 | Console IA | Six panes wireframe | §10 |
| FIG-AI-14 | Metrics | AP by family + TPR@FPR + genuine FPR | §11 |

### A.2 Photographs of *our* UI (your duty)

| ID | Screen | Capture notes |
| --- | --- | --- |
| FIG-UI-01 | HITL queue | One proposed card, citations visible, no API keys |
| FIG-UI-02 | Threat map | All T01–T24; filter by rail/economic class |
| FIG-UI-03 | Simulation console | Population run; `fidelity.pass`; counts by family |
| FIG-UI-04 | Canary inspector | Four-stage chain, synthetic IDs only |
| FIG-UI-05 | Coverage map | Live vs named gap |
| FIG-UI-06 | Decisioning | Score, reasons, Brake chip on an APP row **and** an ATO row (two frames) |
| FIG-UI-07 | Arms race | Before/after Loop M on G-test |
| FIG-UI-08 | Analyst copilot | Summary beside, not instead of, the score |
| FIG-UI-09 | Metrics dashboard | Same numbers as Table 3 |

Aim for **10–12 figures in the 10–15 page Word file** (full-width, 0.3–0.4 page each). Prefer UI photos for §10 and AI diagrams for §4–8. Do not duplicate AI-04 and UI-02 if the console shot is strong—keep one.

---

## Appendix B — Evaluation criteria mapping

| Criterion | Where this paper proves it | Artifact |
| --- | --- | --- |
| Diversity of attacks | §5, Table 2, 29 seed rows, name_only honesty | `data/catalog/seed.yaml` |
| Fidelity of simulation | §6, PSI gates, world-first, APP vs ATO labels | `packages/sim/fidelity.py`, `/generate/population` |
| Detection efficacy | §7–8, §11 Tables 3–4 | `/defend/fit`, `/defend/loop-m` |
| Novelty | Closed loop, Brake, causal features, FinCEN canary, coverage map | Architecture + demo |
| Real-world feasibility | §9, §13.3 | LLM off-path, APP hold, HITL, synthetic-only |

---

## Appendix C — Access log (honesty)

| Source | Status in this v1 |
| --- | --- |
| Kaggle writeup `…/new-writeup-1778618527713` (GEM-4) | Kaggle page cookie-walled. Full write-up recovered from the authors’ GitHub `KaggleArticle.md`. Style used: stakes → two-pillar approach → architecture figures → measured tables → explicit non-claims. |
| Kaggle writeup `…/writeups/trido` | Kaggle page JS-walled. **Full technical write-up not retrieved.** Style inferred from Google’s winner announcement (“deep user empathy and robust offline fallback”) plus Indonesian press (voice-first, offline, built with the teacher). We adopted *fallback on the critical path* and *design for the user who is actually in the loop* (fraud analyst / MRM), not Trido’s classroom content. |
| Kaggle writeup `…/writeups/acuifero4vigia` | **Full page retrieved.** Style used heavily: named pillars with jobs; “deliberate opposite of the cloud default”; walkthrough of one event; auditable reasons; limitations that name what was *not* measured; closing that returns to the opening stakes. |
| LatentView blog | Retrieved (live + local markdown upload). |
| Master of Code blog | Retrieved. |
| arXiv:2410.09066 | PDF retrieved; used in preference to the local Google-Docs PDF whose streams failed prior extraction. |
| `Docs/H2-2026-Adversarial-threat-report_copy.pdf` | Parsed with pypdf (56 pages). Title: *Meta H2 2026 Adversarial Threat Report* (August 2026). Not a Mastercard document. Fraud Attack Chain and “AI as accelerant and countermeasure” used. |
| mastercard.com DI / Recorded Future fraud report pages | **403 / Access Denied.** Not quoted as if read. |

---

*End of submission_write-up_v1. Convert to `TeamName.docx` after figures and Table 3–4 numbers are inserted. List all teammates on the title block per Kaggle rules.*
