# Decisions Log — Mastercard GFF 2026

**Pipeline:** Identify → Generate → Defend  
Full 24-item taxonomy → 5 umbrella categories. Each category = one generation pipeline + shared AutoML classifier + shared closed loop.

---

# PART A — LOCKED

---

## A1. Five Fraud Categories (taxonomy)

### Cat 1 — Network / Transaction Structuring

| | |
|---|---|
| **Covers** | Mule networks, fan-in/fan-out, smurfing under UPI caps, automated chain-hopping/dust laundering, synthetic merchant collusion |
| **Data shape** | Transaction graphs (nodes = accounts, edges = transfers) |

### Cat 2 — Identity

| | |
|---|---|
| **Covers** | Synthetic identity creation, forged KYC docs (described only, not built as images), long-horizon identity farming, deepfake/liveness bypass (described only), account takeover |
| **Data shape** | Structured identity records + behavioral time-series (maturation pattern) |

### Cat 3 — Social Engineering / Conversational

| | |
|---|---|
| **Covers** | Vishing scam agents, voice-clone BEC, push-payment coercion, romance/investment long-cons, phishing (generic + polymorphic in-context), invoice-timed impersonation |
| **Sub-pattern** | Balonx-style live MFA relay — attacker sits between victim and real bank in real time (LLM+STT+TTS operator relays live), not just one-way voice clone. Mention by name in taxonomy for novelty. |
| **Data shape** | LLM-generated scam dialogue/scripts, labeled by persuasion technique, linked to a transaction event |
| **Data enrichment** | Behavioral-biometric fields — typing speed, pause/hesitation duration, copy-paste-on-payee-field flag, active-call-during-session flag. Cheap: a few extra synthetic numeric fields, not a new pipeline. |

### Cat 4 — Model / Pipeline-Targeted (Adversarial)

| | |
|---|---|
| **Covers** | Detector evasion, training-data poisoning, detector fingerprinting, prompt-injection on merchant/support bots |
| **Sub-pattern** | AI supply-chain compromise — attacking the KYC vendor/LLM API itself rather than the end user |
| **Sub-pattern** | Agentic payment initiation — compromised/manipulated AI payment agent initiates the transfer. Intersection of Cat 3 and 4; 2026-frontier / emerging. |
| **Data shape** | Adversarially perturbed versions of categories 1–3's data |
| **Note** | **NOT a separate pipeline** — this IS the closed-loop mechanism wrapping 1+2+3 |

### Cat 5 — Document / Content Forgery

| | |
|---|---|
| **Covers** | Fake invoices/wire instructions, fabricated dispute/chargeback evidence |
| **Data shape** | Structured document-field records (text/fields only, no images) — reuses category 2's generator logic |

---

## A2. Build symmetry

| Category | Role |
| -------- | ---- |
| **1, 2, 3** | Real generation pipelines, real synthetic data, real labels |
| **4** | Not separate — wraps 1+2+3 via adversarial perturbation + retrain (the loop) |
| **5** | Smallest add-on, cheapest, reuses category 2's logic |

---

## A3. Shared infrastructure

- One dataset schema across all categories
- One AutoML classifier (AutoGluon/FLAML) for Defend
- One closed loop: Defend misses → tagged in Identify's KB (`open`) → Generate oversamples that pattern → retrain → re-check → mark `solved` when stable

---

## A4. Why this satisfies the PS

| PS criterion | How we meet it |
| ------------ | -------------- |
| Diversity of attacks | Full 24-item taxonomy mapped into 5 — writeup frames as "24 techniques grouped into 5 structural categories" |
| Fidelity + detection efficacy | Depth on 5, not 24 — real generation + real classifier per category |
| Closed loop | Category 4 IS the loop, not extra work |

---

# PART B — PROPOSED (not fully locked)

---

## B1. Generate (Attack)

> **Status:** Direction agreed. Per-category details and writeup framing still open.

Maps to PS **Generate** pillar. One cross-cutting pattern, **deliberate variation in agentic depth** by category.

### B1.1 Cross-cutting pattern

```
LLM proposer → deterministic engine (rules/schema) → verifier/judge (accept or reject-and-repair)
```

- Validated across PersonaLedger, X-Teaming, OrgForge, TAGAL, etc. — our own stack, not a named third-party framework
- No ground-truth fraud distribution to imitate — realism from **domain rules + personas + verifier loops**

### B1.2 Per category

| Cat | Approach | Agentic depth | Notes |
| --- | -------- | ------------- | ----- |
| **1 — Network** | Deterministic graph engine + LLM picks typology params; calibrated from **SAML-D stats** (aggregate, not row copy) | Thin | Scripted math + reject/repair; balances/topology enforced by engine |
| **2 — Identity** | PersonaLedger-style daily loop; ~150d seasoning → burst | **Strong** | State `s_t`, rule checks, structured `next_prompt` on violation |
| **3 — Social Eng.** | X-Teaming planner / attacker / verifier; Hinglish personas; victim resistance policy | **Strong** | Multi-turn under resistance, not single-shot text |
| **4 — Adversarial** | LLM JSON patch → deterministic apply → query own AutoML → iterate | **Strong** | **Gated** — needs Cat 1–3 classifier first |
| **5 — Document** | Reuses Cat 2 engine; LLM fills narrative fields only | Minimal | Validators on PAN/GSTIN/amounts |

### B1.3 Build order

1. Verifier library (shared UPI/schema/balance rules)
2. Cat 2 (identity trajectory — feeds Cat 5)
3. Cat 1 (graph engine)
4. Cat 3 (dialogue agents)
5. Defend pass (AutoML on Cats 1–3)
6. Cat 4 last (adversarial patch loop)

### B1.4 Writeup framing *(open)*

| Risk | Response |
| ---- | -------- |
| Varying agentic depth reads as inconsistent | State explicitly: agentic where problem is behavioral/strategic (Cat 2, 3, 4); scripted where mathematical/structural (Cat 1, 5) |
| Same pattern everywhere | **Propose → enforce → verify** — only LLM thickness changes |

**Deck one-liner:** *"One verification architecture, variable agent thickness — matched to what each fraud type requires for fidelity."*

---

## B2. Defend

> **Status:** AutoML choice locked. Per-category feature engineering and Cat 3 embedding strategy still open.

Maps to PS **Defend** pillar. **No novel architecture** (locked from day one).

### B2.1 Core

- **One shared AutoML classifier** (AutoGluon / FLAML) on a unified feature schema
- Categories differ in **featurization**, not model architecture
- Cat 4: same classifier stress-tested by perturbation loop → retrained on evasions

### B2.2 Per category — feature handling

| Cat | Input | Features → AutoGluon | Notes |
| --- | ----- | -------------------- | ----- |
| **1 — Network** | Transaction graph | Degree, PageRank, clustering coefficient, burst-velocity, fan-out ratio | Real FE work — not a GNN |
| **2 — Identity** | Records + time-series | Velocity, device/IP shift, maturation-phase (seasoning → burst) | ATO / synthetic-identity signals |
| **3 — Social Eng.** | Dialogue + payment event | Sentence-transformer embeddings + behavioral flags (call-during-session, copy-paste-on-payee, typing speed/pause) | Detects **coercion pattern at payment time** — not raw fraud text; no call audio needed |
| **4 — Adversarial** | Perturbed Cat 1–3 rows | Same model — evasion rate + post-retrain recall | Not a fifth model |
| **5 — Document** | Field records | GSTIN checksum, sequence/continuity, cross-field arithmetic, Benford's Law | Standard invoice toolkit — deliberately thin |

### B2.3 Writeup framing *(open)*

| Risk | Response |
| ---- | -------- |
| "No GNN" reads as under-engineering | **One model, many featurizers** — pipelines match what each rail exposes at payment time |
| Cat 3 looks like NLP classification | Label is coerced payment in progress; embeddings are inputs only |
| Cat 4 looks like a separate detector | Adversarial retrain IS the defense hardening the PS asks for |

**Deck one-liner:** *"One AutoML classifier, five featurization paths — matched to what each rail exposes at payment time."*

---

# PART C — VALIDATION

---

## C1. Holdout strategy (all categories)

**Core principle:** Train on synthetic → evaluate on something independent. Never validate against the same generator that produced training data.

> ⚠️ Some datasets below (TransXion, SAML-D, MoMTSim, VISHGUARD, Composite Scam Transcript, TabAttackBench) are unverified — confirm links before citing.

---

## C2. Per-category holdouts

### Cat 1 — Network

Real labeled holdouts exist — best category for clean validation.

| Dataset | Size / fraud rate | Notes |
| ------- | ----------------- | ----- |
| **SAML-D** (Kaggle) | 9.5M txns, 0.10% | 17 labeled typologies incl. smurfing/layering — best pick |
| **TransXion** (2026) | ~3M rows, 0.15% | Graph-shaped, tabular-usable; map to UPI, drop FX |
| **MoMTSim V2** | 4.22M rows, 52.84% (artificial) | Closest to UPI structure — recalibrate metrics |
| ~~IEEE-CIS / PaySim~~ | — | Legacy, weak — avoid as primary |

### Cat 2 — Identity

Half-real, half-injection.

- **BAF** (NeurIPS 2022, Feedzai) — solid tabular + temporal; **no India Stack (Aadhaar/PAN)**
- **ATO / sleeper-farming** — no real dataset. Fallback: **proxy injection** (IP shift + device-hash change + high-velocity UPI) into legit baseline → TPR on injected anomalies

### Cat 3 — Social Engineering

Text corpora exist but **not India-relevant**.

- Composite Scam Transcript (47k), VISHGUARD (3k) — Western/East-Asian/Arabic only; no Hinglish, no UPI narratives
- **Fallback:** own Hinglish scripts → **LLM-as-judge + blinded native-speaker review**

### Cat 4 — Adversarial

No static dataset — evasion is relative to *your* model.

- **TabAttackBench** — FGSM/PGD/DeepFool/C&W against your classifier; metric = evasion rate over rounds
- **Constraint:** feature-masking — only fields a real fraudster controls
- (Optional) **TabFSBench** for distribution-drift robustness

### Cat 5 — Document

No public dataset.

1. **Distributional sanity-check** — synthetic vs **DGGI/GST fraud statistics**
2. **Expert red-teaming** — human forgeries into MCA registry filings → TPR

---

## C3. Validation summary

| Category | Real labeled holdout? | Method |
| -------- | --------------------- | ------ |
| 1. Network | ✅ Yes | SAML-D / TransXion / MoMTSim |
| 2. Identity | ⚠️ Partial | BAF + proxy injection (ATO) |
| 3. Social Eng. | ❌ Not India-relevant | LLM-as-judge + human review |
| 4. Adversarial | ❌ N/A by design | TabAttackBench evasion rate |
| 5. Document | ❌ No | GST stats + expert red-team |
