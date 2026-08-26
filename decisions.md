# Locked Decision: 5 Fraud Categories (Identify → Generate → Defend)

Full 24-item taxonomy collapses into 5 umbrella categories — nothing dropped, everything mapped. Each category = one generation pipeline + shared AutoML classifier + shared closed loop.

---

## 1. Network / Transaction Structuring Fraud

**Covers:** mule networks, fan-in/fan-out, smurfing under UPI caps, automated chain-hopping/dust laundering, synthetic merchant collusion, card testing / BIN attacks — distributed low-value auth probing across merchants + BIN-space enumeration, evading velocity/CAPTCHA thresholds
**Data shape:** transaction graphs (nodes = accounts, edges = transfers) or auth-attempt graphs — nodes = card-candidate/BIN + merchant endpoint, edges = authorization attempts

## 2. Identity Fraud

**Covers:** synthetic identity creation, forged KYC docs (described only, not built as images), long-horizon identity farming, deepfake/liveness bypass (described only), account takeover **Data shape:** structured identity records + behavioral time-series (maturation pattern)

## 3. Social Engineering / Conversational Fraud

**Covers:** vishing scam agents, voice-clone BEC, push-payment coercion, romance/investment long-cons, phishing (generic + polymorphic in-context), invoice-timed impersonation **Sub-pattern (new):** Balonx-style live MFA relay — attacker sits between victim and real bank in real time (LLM+STT+TTS operator relays live), not just one-way voice clone. Mention by name in taxonomy for novelty. **Data shape:** LLM-generated scam dialogue/scripts, labeled by persuasion technique, linked to a transaction event **Data enrichment (new):** add behavioral-biometric fields to strengthen fidelity — typing speed, pause/hesitation duration, copy-paste-on-payee-field flag, active-call-during-session flag. Cheap: just a few extra synthetic numeric fields, not a new pipeline.

## 4. Model / Pipeline-Targeted Fraud (Adversarial)

**Covers:** detector evasion, training-data poisoning, detector fingerprinting, prompt-injection on merchant/support bots **Sub-pattern (new):** AI supply-chain compromise — attacking the KYC vendor/LLM API itself rather than the end user **Sub-pattern (new):** Agentic payment initiation — a compromised/manipulated AI payment agent initiates the transfer itself. Sits at intersection of Category 3 and 4; 2026-frontier / emerging, worth taxonomy mention. **Data shape:** adversarially perturbed versions of categories 1–3's data **Note:** NOT a separate pipeline — this IS the closed loop mechanism wrapping 1+2+3

## 5. Document / Content Forgery

**Covers:** fake invoices/wire instructions, fabricated dispute/chargeback evidence **Data shape:** structured document-field records (text/fields only, no images) — reuses category 2's generator logic

---

## Build symmetry

- Categories **1, 2, 3** → real generation pipelines, real synthetic data, real labels
- Category **4** → not separate; wraps 1+2+3 via adversarial perturbation + retrain (the loop)
- Category **5** → smallest add-on, cheapest, reuses category 2's logic

## Shared infra

- One dataset schema across all categories
- One AutoML classifier (AutoGluon/FLAML) for Defend
- One closed loop: Defend misses → tagged in Identify's KB (`open`) → Generate oversamples that pattern → retrain → re-check → mark `solved` when stable

## Why this satisfies the PS

- "Diversity of attacks identified" → full 24-item taxonomy mapped into these 5, documented in writeup with honest framing ("24 techniques grouped into 5 structural categories")
- "Fidelity" + "Detection efficacy" → only need depth on 5, not 24 — real generation + real classifier per category
- "Closed loop" requirement → category 4 IS the loop, not extra work

## Detection — Defend features (card-testing/BIN addition only)

- Per-BIN attempt velocity (attempts/min against a single BIN prefix)
- Decline-rate clustering by session/device fingerprint (many declines, one device signature)
- CVV-guess entropy (low entropy = systematic enumeration, not human typos)
- IP/device-rotation entropy (rotating identity per attempt, human shoppers don't)

---

## Validation / Holdout Datasets Per Category

**Core principle:** train on synthetic data, evaluate on something independent — never validate against the same generator that produced training data (circularity trap). Only Category 1 has a clean real labeled holdout; the rest need different validation shapes entirely.

> ⚠️ Some datasets below (2026-dated: TransXion, SAML-D, MoMTSim, VISHGUARD, Composite Scam Transcript, TabAttackBench) are unfamiliar/unverified — confirm they actually exist and links resolve before citing in repo/writeup.

### 1. Network / Transaction Structuring Fraud

Real labeled holdouts exist — best category for clean validation.


| Dataset               | Size / Fraud Rate                     | Notes                                                                                                          |
| --------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **SAML-D** (Kaggle)   | 9.5M txns, 0.10% fraud                | 17 labeled suspicious typologies incl. smurfing/layering — best pick, most granular                            |
| **TransXion** (2026)  | ~3M rows, 0.15% fraud                 | Graph-shaped but tabular-usable; map to UPI, drop FX fields                                                    |
| **MoMTSim V2**        | 4.22M rows, 52.84% fraud (artificial) | Structurally closest to UPI (agent cash-out, instant settlement) — recalibrate metrics for inflated fraud rate |
| ~~IEEE-CIS / PaySim~~ | —                                     | Legacy, weak — PCA-obfuscated features, no semantic depth. Avoid as primary.                                   |

**[Card testing / BIN attacks]** None of the datasets above cover auth-attempt-level data (SAML-D/TransXion/MoMTSim are all transfer-graph, not card-auth-graph) — this sub-pattern has no real holdout. Fallback: **proxy injection**, same technique already used for Category 2's ATO gap — inject distributed low-value probing patterns (rotating IP/device, BIN-clustered attempts) into a legit auth-log baseline, evaluate TPR on the injected anomalies.

### 2. Identity Fraud

Half-real, half-injection.

- **BAF (Bank Account Fraud, NeurIPS 2022, Feedzai)** — solid tabular, temporal column included, but **no India Stack (Aadhaar/PAN) relevance**
- **ATO / sleeper-farming: no real dataset exists.** Fallback = **proxy injection**: inject known ATO patterns (IP shift + device-hash change + high-velocity UPI transfers) into a legit baseline stream → evaluate True Positive Rate on the injected anomalies

### 3. Social Engineering / Conversational Fraud

Text corpora exist but **not India-relevant** — language/cultural gap is the blocker.

- Composite Scam Transcript (47k samples), VISHGUARD (3k, annotated) — usable NLP-wise, but Western/East-Asian/Arabic only. Zero Hinglish, no KYC-update scripts, no "digital arrest" coercion, no UPI-specific narratives.
- **Fallback:** generate own Hinglish/Indian scam scripts → validate via **LLM-as-judge + blinded native-speaker review** instead of a labeled dataset. Only real option for India-relevant fidelity here.

### 4. Model / Pipeline-Targeted Fraud (Adversarial)

No static dataset applies by definition — evasion is relative to *your* model, not a fixed set.

- **TabAttackBench** — run FGSM/PGD/DeepFool/C&W attacks against your actual trained classifier. Metric = evasion rate over rounds, not accuracy against a fixed holdout.
- **Constraint:** apply **feature-masking** — perturbations must only touch fields a real fraudster could actually control (timing, device metadata, structuring amounts), never bank IDs or protocol-breaking fields.
- (Optional) **TabFSBench** for feature-shift/distribution-drift robustness testing.

### 5. Document / Content Forgery

**No public dataset exists at all.** Two-part fallback:

1. **Distributional sanity-check** — compare synthetic invoice/forgery distributions against real **DGGI/GST fraud statistics** (India-specific, genuinely useful, freely published)
2. **Expert red-teaming** — domain experts craft realistic forgeries, inject into real public filings (MCA registry), evaluate classifier TPR against those human-crafted anomalies — only way to avoid circularity here

### Summary


| Category               | Real labeled holdout?     | Validation method                        |
| ---------------------- | ------------------------- | ---------------------------------------- |
| 1. Network/Transaction | ✅ Yes                     | SAML-D / TransXion / MoMTSim             |
| 2. Identity            | ⚠️ Partial                | BAF (creation) + proxy injection (ATO)   |
| 3. Social Engineering  | ❌ No (not India-relevant) | LLM-as-judge + blinded human review      |
| 4. Adversarial         | ❌ N/A by design           | TabAttackBench evasion rate              |
| 5. Document Forgery    | ❌ No                      | GST stats sanity-check + expert red-team |
