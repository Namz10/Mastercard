# GenAI Payment Fraud: Research Brief for Mastercard Innovation Challenge 2026

**Purpose.** Give you a complete, judge-facing understanding of the task, the real-world problem, how institutions actually fight it, and how a winning solution should be shaped. This is a strategy and landscape brief, not an implementation spec.

**Event.** Mastercard Innovation Challenge at Global Fintech Fest (GFF) 2026, Jio World Centre, Mumbai (about 8–11 September 2026). Track: *AI Defense Lab for Payment Security*. Prize listed in the brief: **$4,707**.

---

## 0. Source access notes (read this first)

| Source | Status |
|--------|--------|
| [Wipro — GenAI-driven Fraud](https://www.wipro.com/banking/genai-driven-fraud-confronting-a-new-risk-for-financial-institutions/) | Reached. Full article used. |
| [Amazon Payment Services — GenAI and payments security](https://paymentservices.amazon.com/blog/the-impact-of-generative-ai-on-security-in-the-payments-industry) | Reached. Full article used. |
| [Feedzai — What is GenAI fraud](https://www.feedzai.com/blog/genai-fraud-prevention/#what-is-genai-fraud) | Reached. Full article used. |
| [BNY — AI and payments fraud](https://www.bny.com/corporate/global/en/insights/ai-and-payments-fraud-an-evolving-landscape.html) | Reached. Full article used. |
| Local PDF `AI versus AI in Financial Crimes and Detection.pdf` | **File is present in the repo.** Raw extraction failed (Google Docs / Skia PDF stream). Authors and title match the public preprint. Used the readable version: [arXiv:2410.09066](https://arxiv.org/abs/2410.09066) (Kurshan, Mehta, Bruss, Balch). If any page in the PDF differs from this preprint, treat the PDF as the copy Mastercard gave you and double-check quotes against it. |
| Mastercard.com product/press pages (Decision Intelligence Pro, Scam Protect, 2026 insights) | **Direct fetch blocked** (Akamai 403). Content below is from search snippets, secondary reporting (CNBC/NBC, VentureBeat), and Mastercard-cited industry surveys. Do not treat blocked pages as unread; treat them as *not independently re-fetched*. |
| [Deloitte CFS deepfake / GenAI fraud forecast](https://www.deloitte.com/us/en/insights/industry/financial-services/deepfake-banking-fraud-risk-on-the-rise.html) | Direct fetch timed out. Figures taken from Deloitte-aligned secondary sources and Feedzai/BNY citations of the same study. |
| [FinCEN Alert FIN-2024-Alert004](https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial) | Reached via official release + alert text. |

Numbers below are **reported industry estimates**, not audited facts. Use them as scale, not as claims you “proved.”

---

## 1. What Mastercard actually asked you to build

This is **not** “build a fraud classifier on a Kaggle card dataset.” It is a **closed-loop adversarial system** with three pillars that must be one product, not three side projects.

### 1.1 The slogan is the architecture

> Build the attack, then build the defense.

Judges want a **Red Team / Blue Team loop**:

1. **Identify (ideate).** Exhaustive map of *emerging, novel, GenAI-powered* payment fraud. Breadth *and* depth. Grounded in how payments actually work (rails, authorization, KYC, scams vs stolen-card fraud).
2. **Generate.** Agents/algorithms that **simulate** those attacks at scale with **high fidelity** (realistic transactions, behaviors, timing, mule patterns, social-engineering traces — not cartoon fraud).
3. **Defend.** A detector that catches the simulated attacks with high precision/recall/F1/AUC **and low false positives on legitimate payments**, plus a story for **mitigation** (flag, step-up, hold, notify, decline — not “we detected it” only).

The winning idea in the problem statement itself:

> The attacks you generate become the training and stress-testing ground for the defense you build, and the gaps your defense reveals feed back into new attack ideas.

That is **co-evolutionary AI**. It is also the thesis of the paper Mastercard put in your pack (Section 4). Teams that only train a static XGBoost on IEEE-CIS or PaySim will look like they missed the brief.

### 1.2 What you must submit

| Artifact | Constraint |
|----------|------------|
| Public GitHub repo named **TeamName** | All three pillars, runnable, documented |
| `TeamName.docx` walkthrough | Attacks identified, generation method, detection + metrics, live-payments feasibility |
| Working **web prototype** with a presentable UI | Must *show the loop*, not a notebook |
| Kaggle team-up + Luma registration | All members; names and emails in the write-up |

### 1.3 How you will be scored (internalize this)

| Criterion | What “good” looks like to a Mastercard judge |
|-----------|-----------------------------------------------|
| **Diversity of attacks** | Many *distinct* vectors across channels (card, A2A/UPI-like, onboarding, ATO, BEC, mule) — not five flavors of CNP |
| **Fidelity of simulation** | Looks like payment data: amounts, MCCs, device, velocity, graph of payees, time zones, “authorized but scam” vs “stolen credential” |
| **Detection efficacy** | Precision/recall/F1/AUC **and** false-positive rate on genuine traffic; maybe PR curves, cost of missed fraud vs declined good txns |
| **Novelty** | Closed loop, agents, synthetic-data flywheel, graph + multimodal signals — not “we used an LLM to write phishing emails” as the whole product |
| **Real-world feasibility** | Latency (authorization is tens to a few hundred ms), explainability, human-in-the-loop, privacy, no live criminal tooling, works as a *network/issuer* decisioning aid |

**Critical thinking on the prize vs the work.** The cash prize is small relative to GFF visibility. Treat this as a **Mastercard talent and product-fit audition**. Speak the company’s language: Decision Intelligence-style scoring, false-positive reduction, scams vs card fraud, real-time rails, network graph intelligence.

---

## 2. Why this challenge exists (the real-world problem)

### 2.1 The structural shift

Payments went digital and then **instant**. Fraud used to be high-volume, low-sophistication (typo-ridden phishing, obvious stolen-card bursts). GenAI inverted that:

- **Cost of a convincing attack collapsed.** Open models, voice clone from seconds of audio, ID photo generation, fluent localized phishing.
- **Speed of rails rose.** Real-time payments, UPI, Zelle-class A2A, instant card auth. Once money moves, recovery is hard.
- **The victim often authorizes the payment.** That is **authorized push payment (APP) / credit-push scam** fraud. Rules that look for “stolen PAN + unusual MCC” miss it, because the customer did the OTP/biometric themselves.

Mastercard’s own 2025-era industry survey (FT Longitude / Mastercard, as reported by Mastercard Insights 2026 and BNY citing Mastercard) is consistent with this: executives name **synthetic identity**, **impersonation scams**, and **cross-border fraud** as the fastest-growing threats.

### 2.2 Scale (use carefully in the deck)

These figures appear repeatedly in the sources you were given and in regulator/industry reports. Present them as *cited estimates*.

- **Deloitte Center for Financial Services:** GenAI-enabled fraud losses in the **US** could reach **~$40B by 2027**, from **~$12.3B in 2023** (~32% CAGR). Email-fraud-only “aggressive adoption” path ~$11.5B in four years in some Deloitte write-ups.
- **Juniper (via BNY):** banking-institution fraud losses globally **$23B (2025) → $58.3B (2030)**, with a large lift from more sophisticated types.
- **Feedzai:** same Deloitte $40B-by-2027 citation; survey of 562 financial professionals: **voice cloning 60%**, **SMS/phishing 59%**, **deepfakes 44%** as common GenAI fraud use cases; **96%** of banks said they have implemented GenAI in some form.
- **NASDAQ–Verafin 2024 (via Kurshan et al.):** ~**$485.6B** global fraud/scam and bank-scheme losses; ~**$3.1T** illicit funds through the financial system (mostly laundering of other crimes).
- **Hong Kong case (Wipro, FinCEN, Deloitte):** deepfake **video-conference CFO** → employee sent **>$25M**. This is the canonical “GenAI broke the human control” story. Use it; do not overclaim it as typical loss size.
- **BNY / Sumsub:** identity-fraud *attempts* as a share of verifications **fell** (2.6% → 2.2%, 2024–2025) while the **share of sophisticated cases tripled** (~10% → ~28%). Fewer clumsy attacks, more expensive ones.
- **BNY citing Infosecurity (2026):** **1,210%** surge in AI-enabled fraud (deepfake/synthetic) vs **195%** traditional, Jan–Dec 2025 — treat as vendor/press statistic, still useful as “direction of travel.”
- **India (GFF host, RBI discussion paper coverage 2026):** NCRP-cited complaints **2.6 lakh (2021) → 28 lakh (2025)**; reported value **₹551 crore → ₹22,931 crore**. RBI frames this as **APP fraud** exploding while classic ATO becomes relatively smaller. That is the local story judges in Mumbai will feel in their bones.

### 2.3 What GenAI changed about *technique*, not just volume

From Wipro, Feedzai, Amazon, BNY, FinCEN, and Kurshan et al.:

| Old tell | After GenAI |
|----------|-------------|
| Grammar errors in phishing | Fluent, localized, personalized at scale (FraudGPT / WormGPT / jailbroken models — **name them as criminal-market phenomena, do not reproduce them**) |
| Static stolen ID photo | Synthetic IDs, GAN/diffusion faces, forged docs that pass first-pass KYC |
| Call-center social engineering | Voice clone of customer or executive; video clone on Teams/Zoom |
| Manual mule recruitment | Bot orchestration, human-like CAPTCHA, mass account opening |
| Probe-and-learn against rules | Attackers can **generate** synthetic transaction traces to **rehearse** against detectors |

Amazon’s payments-security piece adds two issues many hackathon teams skip: **data poisoning** of fraud models, and **AI supply-chain** risk (third-party models/APIs). Those belong in Identify *and* in your Defend threat model.

Kurshan et al. add the uncomfortable industry diagnosis: **criminals adopt AI faster** than banks, because banks have **model-risk-management (MRM)** cycles of months to years, cost-cutting, and siloed data. Static models rot. The only durable answer they argue for is **AI-versus-AI** that **co-evolves**.

That paper is not background color. **It is the intellectual specification of the challenge.**

---

## 3. Map of GenAI-powered payment fraud (Identify pillar)

Be exhaustive in the product; be structured in the deck. Organize by **where in the payment lifecycle** the attack lands, not by “cool GenAI toy.”

### 3.1 Lifecycle view (this is how payments people think)

```
Onboarding / KYC  →  Account access / ATO  →  Payment initiation
        →  Authorization / risk score  →  Clearing & settlement
        →  Disbursement / mule cash-out  →  Dispute / SAR
```

GenAI can attack **every stage**. A winning Identify catalog has **at least one novel vector per stage**, then depth inside each.

### 3.2 Typology catalog (high-level; for ideation and simulation design)

**A. Identity and onboarding**

- **Synthetic identity:** mix real identifiers (e.g. a real ID number) with fabricated name/address/selfie; GenAI documents and faces. Deloitte: **~$23B US losses by 2030** often cited. FinCEN: SARs already describe GenAI IDs used to open accounts that then receive scam proceeds, act as **funnel/mule** accounts.
- **Deepfake Video-KYC / liveness bypass:** replay, webcam plugins, “glitch then switch channel” (explicit FinCEN red flags).
- **Document forgery:** invoices, pay stubs, passports, driver’s licenses for credit, BNPL, merchant onboarding.

**B. Authentication and account takeover**

- **Voice cloning vs voice biometrics** (Feedzai: most-cited GenAI tactic in their survey). Senate/US reporting (cited in the paper): clones fool some bank voice-auth.
- **Phishing / smishing / vishing** with perfect copy, cloned bank UI, OTP-harvest bots (paper: OTP/SMS is a **single point of failure** with SIM-swap and malware).
- **Session / device mimicry:** GenAI-assisted social engineering plus malware; behavioral biometrics as the counter (Mastercard Scam Protect narrative).

**C. Social engineering that produces a “legitimate” payment (APP / scam)**

This is the **hardest and most current** class. The transaction looks authentic to the rail.

- Executive / CFO deepfake video (Hong Kong $25M).
- Family-emergency voice clone (FTC; FinCEN elder-fraud overlap).
- Romance / pig-butchering, investment, charity, grandparent — GenAI chatbots (LoveGPT-class tooling named by Feedzai as criminal market, not as something you should build).
- Bank / government / courier impersonation at India scale (UPI QR “receive money” inversion, fake refunds).

**D. Card and merchant rails**

- CNP with synthetic identities and bot checkout.
- **Card testing** and enumeration, now with more human-like bots.
- Merchant collusion / bust-out after synthetic onboarding.
- **False-positive gaming:** attackers stay inside a cardholder’s “normal” graph so inverse-recommender models hesitate (this is why Mastercard talks about merchant-relationship graphs, not just amount+MCC).

**E. Real-time A2A / RTP / UPI / Zelle-class**

- Instant credit to mule; no chargeback analog.
- Money-mule networks, layering with many small accounts (FATF “ML-as-a-service” in the paper).
- BNPL and open-banking Pay-by-Bank (BNY: bots + BNPL called out by 42% of execs in one survey).

**F. BEC and commercial payments**

- Invoice rewrite, vendor-bank-detail change, lawyer/CFO impersonation. BEC growth cited as extreme in some vendor stats (paper cites 1,760% BEC surge claims — **vendor PR; use as “BEC is exploding,” not as a precise CAGR**).

**G. Attacks on the detector itself (Amazon + NIST + Kurshan)**

- **Poisoning** training/synthetic data so fraud looks benign.
- **Evasion / probing** of the scoring API.
- **Supply-chain** compromise of a third-party KYC or LLM vendor.
- **Hallucinated GenAI in the blue team** (Feedzai: hallucinations, bias, explainability) — your defense can harm customers if it is an ungoverned LLM.

**H. Crime-as-a-service industrial layer**

- Interpol/Europol: scam centers, CAAS, jailbreak-as-a-service.
- Same playbook reused across banks because **institutions do not share** attack fingerprints (paper’s cooperation gap).

### 3.3 What “novel” should mean for *this* hackathon

Do not invent sci-fi. Novelty = **new combination of GenAI + a real rail weakness**, for example:

- Deepfake KYC → sleeper synthetic account → **priming** with small genuine-looking spend → APP inbound from a scam victim → crypto/gambling cash-out (FinCEN’s own pattern).
- Voice clone of the cardholder to the issuer call center to **lift a fraud block** (ATO completion, not just login).
- Multi-mule graph that is **individually in-distribution** but **collectively** a funnel (graph features beat tabular).
- Adversarial generator that **searches** for transactions your current model scores as safe, then you retrain — the closed loop.

Ground every idea in a **rail** (card auth, A2A, onboarding) and a **control that failed** (liveness, voice bio, OTP, human callback, velocity rules).

---

## 4. How institutions actually mitigate this (Defend, in the real world)

There is no silver bullet. Every serious program is **layered**. Your prototype should *look like* this stack, even if each layer is simplified.

### 4.1 Two-layer fraud architecture (Wipro — use this language)

1. **Layer 1 — stop initiation / ATO:** identity, device, liveness, PII/photo vs external sources, IP, behavioral biometrics.
2. **Layer 2 — stop the money if Layer 1 fails:** transaction monitoring, mule/payee intelligence, real-time hold/notify, APP scam detection (beneficiary risk, not just sender anomaly).

Wipro’s extra idea that maps **directly** to your Generate pillar: **train on GenAI-created synthetic fraud scenarios** for known schemes (ATO, synthetic ID, BEC, romance, investment, grandparent, charity, etc.) so the model sees attacks *before* they dominate production.

### 4.2 What banks, networks, and vendors actually deploy

**Real-time transaction scoring (Mastercard’s home turf)**

- **Decision Intelligence / DI Pro:** score in **~50 ms** (Mastercard claims), inside a **<300 ms** authorization envelope (VentureBeat interview with Mastercard security/data-science leaders).
- Architecture idea they advertise: **graph of cardholder–merchant–device**, recurrent / “inverse recommender” — not “is this amount weird?” in isolation. Claimed **~20% average** fraud-detection lift, **up to ~300%** in some portfolios, **>85% false-positive reduction** in their analysis. Treat as **vendor claims**; the *design lesson* is what judges want: **latency, network graph, FP reduction, issuer still decides**.
- Mastercard **Scam Protect / Consumer Fraud Risk (UK A2A):** intervene **before** the credit lands; behavioral biometrics for hesitation/typing; identity step-up. This is the product analog of APP defense.

**Identity and deepfake (FinCEN + Feedzai + DHS remote identity testing)**

- Re-review of onboarding packs; reverse image search vs **this-person-does-not-exist** galleries.
- Metadata / dedicated deepfake detectors (not conclusive alone).
- **Phishing-resistant MFA**, live video with **plugin / replay** detection.
- FinCEN red flags you can turn into **features or rules in the simulator**: webcam plugin, channel-switch during KYC, MFA refusal, photo vs DOB mismatch, new account + rapid drain to gambling/crypto, coordinated similar accounts, IP vs ID geography.

**Behavioral and continuous authentication**

- Device fingerprint, typing/swipe, session graph.
- Risk-based step-up instead of hard decline (protects genuine customers — **false positives kill issuers**).

**Graph / network intelligence (Kurshan’s other body of work; Feedzai IQ-style products)**

- Mules and syndicates are **invisible at the single-transaction level**.
- Graph neural nets / network features: shared devices, shared beneficiaries, burst fan-in/fan-out.

**Synthetic data for model training (Wipro, and implicitly Mastercard “predict unknown fraud”)**

- Institutions cannot wait for rare new typologies to appear in labeled production data.
- High-fidelity simulation is how you get **coverage of the tail**.

**Governance, not only models (Amazon, Feedzai TRUST, Treasury 2024 AI risk report)**

- Model audit against poisoning.
- Zero Trust for payment APIs.
- Explainability for declines and SARs (`FIN-2024-DEEPFAKEFRAUD` as a filing tag in the US).
- UK **mandatory APP reimbursement** (Wipro) and India’s emerging **digital-fraud compensation** (coverage says statutory direction from **1 Jan 2027**) — **liability is shifting onto institutions**, which is why they will pay for this tech.

**Human and process controls (BNY, Deloitte)**

- Dual control / callback on **known** numbers for commercial payments (deepfake-resistant *process*, not a model).
- Staff training as first line for BEC.
- Shift volume onto **more controlled rails** (BNY: AFP survey — check fraud 63% of US orgs vs mobile wallet ~3%, RTP ~2% *incident rates in that survey*; Zelle claims 99.95% of txns without reported scam/fraud). Newer rails win when they have **better controls**, not because they are magically safe.

**India-specific mitigations in motion (GFF relevance)**

- RBI discussion: lagged credit for high-value new-payee APP, trusted-person auth for vulnerable customers, caps on credits to low-KYC accounts, kill switches and customer-controlled limits.
- Banks proposing **Yes / No / timeout** prompts on risky UPI P2P so friction is optional and targeted.
- NPCI pushback in press: do not copy foreign friction blindly; lagged credit may not stop **complicit mule** or some investment scams.

A sophisticated prototype could **simulate** both the scam *and* these policy interventions (hold window, trusted-person, beneficiary risk) as **mitigation actions**, not only binary fraud labels. That scores **feasibility**.

### 4.3 What does *not* work anymore (say this in the walkthrough)

- Static rules and “typo in the email.”
- Voice biometrics **alone**.
- Document photo KYC **alone**.
- Training only on last year’s confirmed fraud (label lag; novel GenAI types are missing).
- A detector with high recall and a **ruined genuine-approval rate** (Mastercard’s whole DI pitch is approve more genuine volume).

---

## 5. The academic spine: co-evolutionary AI (your PDF / arXiv:2410.09066)

**Authors:** Eren Kurshan; Dhagash Mehta (BlackRock); Bayan Bruss (Capital One); Tucker Balch.

**Core argument:** GenAI makes crime more personalized, faster, and more evasive. Detection AI that is frozen by governance will lose. **AI-versus-AI that co-evolves** is the viable path, plus industry data-sharing / federated learning, graph methods, multi-modal/multi-channel models, risk-aware authentication (down-weight biometrics that criminals can now fake), and **self-regulating / regulatory AI** to shorten MRM cycles.

**Defense opportunities they list that you can productize in a hackathon-sized way:**

| Idea from the paper | Hackathon translation |
|---------------------|------------------------|
| Graph AI over accounts, devices, money flows | Generate mule networks; detect with graph features / GNN-lite |
| Multi-modal (language ↔ transactions) | Scam chat/call **summary features** + payment features in one model |
| Adaptive / dynamic AI | When deepfake risk rises, reduce weight of voice-match; raise step-up |
| Synthetic / generative scenarios | Your Generate pillar |
| Protect the detector from poisoning and evasion | Red-team the **blue** model; show robustness |
| Federated / shared typology intelligence | Simulated “consortium feed” of new attack signatures (even if fake data) |
| Co-evolution | Outer loop: generator maximizes evasion; detector retrains; plot the arms race |

**Do not** try to train a trillion-parameter LLM. The paper itself says GenAI cost and hallucination risk block many banks. A **small generator + strong tabular/graph detector + LLM only for typology ideation and case narrative** is more “Mastercard feasible” than a giant chatbot.

---

## 6. How to shape a solution that can win

### 6.1 Product metaphor (one sentence)

**An AI Defense Lab: a red agent invents and simulates GenAI payment attacks; a blue model scores them in authorization-time; a control plane retrains and recommends mitigations; the UI lets a fraud analyst watch the loop and the metrics.**

That is the closed loop. Everything else is a feature.

### 6.2 Recommended shape of the three pillars

**Identify**

- Knowledge base / taxonomy of 15–40 vectors tagged by: rail, GenAI modality (text/voice/video/doc/bot), kill-chain stage, which control it bypasses, which features should fire.
- Optional: LLM **researcher agent** that ingests *public* news/alerts (FinCEN-style red flags) and proposes new vectors — with human approval. Novelty + demo theater.
- Output: not a blog post; a **machine-readable attack catalog** the generator can execute.

**Generate**

- Fidelity > spectacle. Judges will sniff random `amount ~ Uniform(1, 10000)` “fraud.”
- Need **benign baseline** that looks like real spend (circadian cycles, merchant categories, home geography, device stability) **and** fraud that is a **perturbation** of that world.
- Separate simulators: (1) **stolen-credential / CNP** velocity; (2) **synthetic onboarding + seasoning**; (3) **APP scam** (victim behavior + mule beneficiary); (4) **ATO** after social engineering.
- Preserve **privacy**: fully synthetic customers; no real PANs; document that you did not use criminal LLMs to produce live attack content against real institutions.

**Defend**

- Primary: **supervised or hybrid anomaly model** on transaction + identity + graph features, with a **risk score** (Mastercard-shaped), not only a class label.
- Secondary: **rules/red-flag overlay** (FinCEN list) for explainability — analysts and regulators need reasons.
- Metrics dashboard: AUC, F1, **precision at low FPR**, estimated false-decline cost, detection lag, **evasion rate after the red agent adapts**.
- Mitigation policy: decline vs step-up vs 60-minute hold vs notify vs trusted-person — especially for APP (because a hard decline of a customer-authorized payment is a product disaster).

**The loop (this is the novelty slot)**

```
catalog → simulate N attacks + M genuine
        → score
        → measure misses
        → red agent mutates attacks toward misses
        → retrain / recalibrate blue
        → repeat
        → show lift over a static baseline
```

If you only have one generation of data and one trained model, you have **not** built the product they described.

### 6.3 UI (they explicitly grade a presentable web prototype)

Minimum screens that make judges nod:

1. **Threat map** — catalog, filters by rail/region (include **India UPI + global card** if you want GFF relevance).
2. **Simulation console** — launch a campaign, see synthetic ledger + mule graph.
3. **Decisioning** — live score stream, explainability (top features / red flags).
4. **Arms race** — chart: red evasion vs blue detection over generations.
5. **Analyst copilot** — *summarize the case* (Feedzai Case Summary Agent analog). Do **not** let the LLM be the sole detector.

### 6.4 Feasibility story (copy this logic into the .docx)

- **Latency:** heavy GenAI **off** the authorization path; on-path model is compact (they will compare you to 50–300 ms). Use GenAI in Identify, case narrative, and maybe offline simulation.
- **Human in the loop:** high-value APP and commercial payments still need process controls (out-of-band callback).
- **Liability and Reg E / UK reimbursement / future RBI compensation:** detection without a **hold/intervention** policy is incomplete.
- **Ethics:** no real phishing, no real deepfake of living people in the demo, no dark-web tooling. Synthetic personas, clearly labeled simulation.
- **Explainability:** SAR-ready reasons; bias note (Feedzai: biased models harm customers).

### 6.5 What will lose even with good ML

- Five attack types, all “phishing email.”
- A Streamlit page that only classifies a CSV.
- Claiming you “used FraudGPT.”
- 99.9% accuracy with no FPR / no class imbalance story.
- No graph, no APP/scam (only classic card fraud) — you ignored 2024–2026 reality and Mastercard Scam Protect.
- Unreadable repo, private GitHub, wrong filenames vs Kaggle team name.

### 6.6 Competitive positioning vs a typical team

Most teams will: LLM writes fake emails → dump random transactions → XGBoost.

You should: **taxonomy grounded in FinCEN + APP + synthetic ID + ATO + mule graph** → **multi-generator with realistic benign world** → **score + policy** → **co-evolution plot** → **Mastercard-shaped latency/FP narrative** → **India real-time rail subplot** because the room is GFF.

---

## 7. Suggested narrative for judges (90-second version)

Generative AI did not invent payment fraud. It collapsed the cost of **believable identity, believable speech, and believable pressure**, while rails went **irreversible**. Static rules and last year’s labels cannot see **customer-authorized scams** or **synthetic mules that look like people**. Mastercard already fights this with **network-scale, millisecond decisioning** and **scam-specific A2A intelligence**. Our lab **closes the loop they asked for**: we catalog emerging GenAI attacks, **simulate them at payment fidelity**, train a detector that **scores like an issuer decisioning service**, and **let the attacker adapt** so the defense does not freeze. The output is not a chatbot. It is a **co-evolving red/blue system** a network or bank could sit beside Decision Intelligence — with humans, holds, and explanations still in the loop.

---

## 8. Reading list (priority order)

1. Challenge statement — `MC_PS.md` (this repo).
2. Kurshan, Mehta, Bruss, Balch — [AI versus AI in Financial Crimes and Detection](https://arxiv.org/abs/2410.09066).
3. [FinCEN FIN-2024-Alert004](https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial) (red flags → features).
4. [Wipro GenAI fraud](https://www.wipro.com/banking/genai-driven-fraud-confronting-a-new-risk-for-financial-institutions/) (two-layer defense + synthetic training).
5. [Feedzai GenAI fraud](https://www.feedzai.com/blog/genai-fraud-prevention/#what-is-genai-fraud) (tactics mix + layered AI + ethics).
6. [BNY evolving landscape](https://www.bny.com/corporate/global/en/insights/ai-and-payments-fraud-an-evolving-landscape.html) (sophistication vs volume; rail mix).
7. [Amazon payments GenAI security](https://paymentservices.amazon.com/blog/the-impact-of-generative-ai-on-security-in-the-payments-industry) (poisoning, supply chain, Zero Trust).
8. Deloitte CFS — [deepfake banking fraud](https://www.deloitte.com/us/en/insights/industry/financial-services/deepfake-banking-fraud-risk-on-the-rise.html) ($40B framing).
9. Mastercard DI Pro / Scam Protect (press; Decision Intelligence product pages) — **align vocabulary** even if pages 403 in some crawlers.
10. US Treasury (Mar 2024) — *Managing Artificial Intelligence-Specific Risks in the Financial Services Sector* (cited by FinCEN and Kurshan).
11. India: RBI discussion paper coverage on **digital payment safeguards / APP** (lagged credit, trusted person) — local feasibility chapter.

---

## 9. Bottom line

The company did not ask you to “detect fraud.” They asked you to **industrialize the arms race** under payment-system constraints: **coverage of many GenAI vectors, believable synthetic payments, accurate low-FP detection, and a loop that gets stronger as the attacker does.** That is what “real-world feasibility in live payments” means here: millisecond-class scoring, mule/scam reality, explainable actions, and respect for the fact that **the most damaging GenAI fraud often looks like a genuine customer paying a genuine-looking payee.**

Build the lab. Show the loop. Speak like a network.

---

## aarush:defend research — Mid-Tier ML/AutoML for Fraud Classifiers (2–3 Day Hackathon)

**Scope.** Approaches that sit **between** (a) fixed-search AutoML (`AutoGluon`, `FLAML`) and (b) fully open-ended autoresearch (LLM proposes architectures, features, and hypotheses with autonomous code execution). Target: **tabular fraud/anomaly classifier**, **severe class imbalance**, **2–3 day build window** for Mastercard GFF hackathon Defend pillar.

**Spectrum anchors.**

| Pole | Characteristics | Hackathon fit |
|------|-----------------|---------------|
| **Plain AutoML** (`FLAML`, `AutoGluon good_quality`) | Fixed model families, fixed feature space, minutes to hours | Baseline floor — do this first |
| **Mid-tier (this doc)** | Expands features, warm-starts search, automates imbalance handling, or runs **bounded** agent loops | Where most lift + novelty lives |
| **Full autoresearch** (`AIDE`, `SELA`, `MLE-STAR`) | LLM writes/edits full pipelines; open action space; high variance | Demo theater + risk; hard to ship in 48h |

**Risk/ceiling shorthand.** `Low risk / low ceiling` → predictable, rarely beats a tuned XGBoost stack. `Medium` → meaningful PR-AUC lift on fraud tails. `High risk / high ceiling` → can discover surprising features or blow up on leakage/overfit.

**Local vs API.** `Local` = runs offline after `pip install`. `Hybrid` = core local, optional LLM API for one step. `API-required` = needs hosted LLM during training/search.

---

### 1. Feature-engineering automation (expands what AutoML sees; does not change model search)

| Tool | Automates | Still fixed / manual | Setup (hrs) | Train/infer cost | Risk / ceiling vs plain AutoML | Local? | Example |
|------|-----------|----------------------|-------------|------------------|--------------------------------|--------|---------|
| **Featuretools** | Deep Feature Synthesis: aggregations (`count`, `mean`, `time_since_previous`) across related tables | EntitySet schema, relationships, `max_depth`, primitive list; single-table fraud needs manual entity design | 2–4 | Medium CPU; feature matrix can be wide (memory) | Low–medium risk; medium ceiling on **relational** fraud (customer→txn→merchant) | Local | `fm, _ = ft.dfs(entityset=es, target_dataframe_name="customers", max_depth=2)` |
| **OpenFE** | Operator search (23 ops), feature boosting + two-stage pruning; **validated on IEEE-CIS fraud** | Operator set bounded; no semantic/domain features; runtime grows with `#features × rows` | 1–2 | Medium–high CPU; parallel `n_jobs` | Medium risk; **high ceiling** on flat tabular fraud (Kaggle-grade lift reported) | Local | `features = OpenFE().fit(data=X_train, label=y_train); X_tr, X_te = transform(X_train, X_test, features)` |
| **tsfresh** | 794 time-series features + FRESH statistical filtering | Needs **sequential** structure (per-user txn streams); not for static wide tables | 2–3 | Medium; Dask for scale | Low–medium; medium ceiling if velocity/sequence matters | Local | `X_ts = extract_features(df, column_id="customer_id", column_sort="timestamp")` |
| **AutoFeat** | Polynomial/ratio/log transforms + L1 selection | Under ~100k rows; symbolic explosion; interpretable but slow | 1–2 | High CPU on wide data | Medium; modest ceiling on small wide fraud sets | Local | `X_aug = AutoFeatClassifier(max_depth=2).fit_transform(X, y)` |
| **evo-gpfe** | Genetic-programming symbolic features (DEAP) | Population/generations; anti-bloat tuning | 2–4 | High CPU per generation | Medium–high risk; niche ceiling (interpretable nonlinear combos) | Local | `X_aug = GPFeatureEngineer(GPConfig(n_generations=20)).fit_transform(X, y)` |
| **EvolutionaryForest** | GP ensemble features for tree models | Research-oriented API; many hyperparams | 3–5 | High | High risk; research novelty, uneven production lift | Local | `EvolutionaryForestRegressor(n_gen=20, n_pop=200).fit(X, y)` |
| **PyCaret `setup()`** | Imputation, encoding, polynomial interactions, binning (bundled) | Model search is separate; FE primitives are fixed | 0.5–1 | Low setup; CV cost depends on `compare_models` | Low risk; low–medium ceiling (convenience layer) | Local | `setup(data, target="is_fraud", polynomial_features=True); compare_models()` |

**Fraud hackathon notes.**

- **Single flat transaction table:** prioritize **OpenFE** → feed into AutoGluon/FLAML.
- **Customer + transactions (+ merchants):** **Featuretools** is the natural fit (velocity, time-since, MCC aggregates).
- **Per-user time-ordered streams:** stack **tsfresh** on rolling windows, then merge to txn-level model.
- These tools **do not** pick SMOTE vs class weights — pair with Section 5.

---

### 2. Meta-learning / warm-started AutoML (smarter starting points; search still bounded)

| Tool | Automates | Still fixed / manual | Setup (hrs) | Train/infer cost | Risk / ceiling vs plain AutoML | Local? | Example |
|------|-----------|----------------------|-------------|------------------|--------------------------------|--------|---------|
| **auto-sklearn 2.0** | Portfolio warmstart (meta-feature-free) + optional KNN meta-learning init + SMAC BO + ensembling | Model pipeline components fixed; `time_left_for_this_task` budget; imbalanced metrics manual | 1–2 | High per time budget; disk for ensembles | Medium risk; **solid ceiling** in 10–60 min budgets | Local | `AutoSklearnClassifier(time_left_for_this_task=3600, metric=autosklearn.metrics.f1).fit(X, y)` |
| **AutoGluon `best_quality`** | `auto_stack=True`, dynamic stacking, zeroshot HPO, multi-layer ensembles | Preset model zoo fixed; no custom feature synthesis; imbalance needs `eval_metric` / `sample_weight` | 0.5 | **High** train time + **heavy** inference (stacked ensemble) | Low–medium risk; **high ceiling** on tabular if time budget ≥30–60 min | Local | `TabularPredictor(eval_metric="average_precision").fit(train, presets="best_quality", time_limit=3600)` |
| **AutoGluon `experimental_quality`** | Stronger stacking / foundation-model hooks (version-dependent) | Same as above; less battle-tested | 0.5 | Very high train | Medium risk; chases SOTA, less predictable | Local | `predictor.fit(train, presets="experimental_quality", time_limit=7200)` |
| **FLAML** | Fast cost-aware HPO across fixed learners; optional `resampler=` per-fold | No meta-learning warmstart; learner list bounded; imbalance not auto-detected | 0.5 | **Low** train; **fast** infer (single best model) | Low risk; medium ceiling; best for **latency story** | Local | `AutoML().fit(X, y, task="classification", metric="ap", time_budget=600, resampler=SMOTE())` |
| **H2O AutoML** | Leaderboard + stacked ensemble + optional exploitation of past runs | Java backend; less hackathon-friendly | 1–2 | Medium–high | Low–medium risk; similar ceiling to AutoGluon | Local | `H2OAutoML(max_runtime_secs=3600, balance_classes=True).train(x=cols, y="label", training_frame=hf)` |

**Fraud hackathon notes.**

- Run **FLAML** (fast, `metric="ap"` or `metric="f1"`) for the **authorization-latency** narrative; run **AutoGluon best_quality** offline for **leaderboard score**.
- auto-sklearn shines when you have **30–60 min** and want a **strong ensemble without hand-picking** — set `metric` to F1 or balanced accuracy, not accuracy.
- None of these **auto-select SMOTE variant** — combine with Section 5.

---

### 3. LLM-assisted feature / config suggestion (human or script in the loop — not autonomous autoresearch)

| Approach | Automates | Still fixed / manual | Setup (hrs) | Train/infer cost | Risk / ceiling vs plain AutoML | Local? | Example |
|----------|-----------|----------------------|-------------|------------------|--------------------------------|--------|---------|
| **DIY analyst prompt** (recommended) | LLM reads schema + `df.describe()` + current leaderboard → suggests features, resampling, metrics as **text** | Human or script applies suggestions; no auto code exec | 1–2 | API: ~$0.10–2 per iteration | Medium risk; **high ceiling** if domain-aware (fraud velocity, device graphs) | Hybrid | Paste schema + `predictor.leaderboard()` into chat; implement top 3 suggestions in Python |
| **CAAFE** | LLM generates Python feature code; validates on holdout; keeps if metric improves | `iterations` cap; base classifier must be fast (TabPFN default); **OpenAI API** | 2–4 | API + many small model fits per iteration | Medium–high risk; semantic features (scam urgency, amount ratios) | API-required | `CAAFEClassifier(base_classifier=rf, llm_model="gpt-4", iterations=3).fit_pandas(df, "is_fraud", dataset_description="card txn fraud...")` |
| **OCTree** (research) | LLM feature rules + decision-tree reasoning feedback | GitHub install; API; research code | 4–6 | API + tree fits | Medium–high; NeurIPS 2024 method | Hybrid | Clone [jaehyun513/OCTree](https://github.com/jaehyun513/OCTree); run paper pipeline |
| **OpenFE + LLM feature descriptions** | OpenFE math features + LLM explains/names them for judge deck | Two-step | 2–3 | OpenFE CPU + API | Medium; good **explainability** story | Hybrid | OpenFE features → prompt LLM: "Given columns X, suggest 5 domain fraud features" → manual add |

**Fraud hackathon prompt template (DIY).**

```
Columns: {schema}. Target rate: {pos_rate}. Metric: PR-AUC={score}.
Top model: {leaderboard_row}. Missing: velocity, device, beneficiary graph.
Suggest 5 executable pandas features for payment fraud, 1 resampling strategy,
and whether to tune threshold vs class weight. No code execution — bullet list only.
```

**Why this tier matters for judges.** You get **"semantic AutoML"** language (CAAFE paper) without betting the repo on an agent that rewrites itself into a syntax error at 3 a.m.

---

### 4. Neural architecture search (NAS) scoped to tabular — lightweight enough for hackathon?

| Tool | Automates | Still fixed / manual | Setup (hrs) | Train/infer cost | Risk / ceiling vs plain AutoML | Local? | Example |
|------|-----------|----------------------|-------------|------------------|--------------------------------|--------|---------|
| **pytorch-tabnet + Optuna** | Attention steps, depth, width, learning rate (HPO **not** full NAS) | Architecture family fixed (TabNet); GPU helpful; imbalance manual | 3–5 | GPU train; moderate infer | Medium risk; interpretable masks; sometimes beats GBDT on wide data | Local | `TabNetClassifier().fit(X_train, y_train, eval_set=[(X_val,y_val)])` |
| **TabNAS** (NeurIPS 2022) | RL NAS with rejection sampling for tabular NNs | **Research code**; setup heavy; not pip | 6–10+ | GPU | High risk; paper gains, hackathon fragility | Local | Reproduce from [TabNAS paper repo](https://github.com/google-research/google-research/tree/master/tabnet) paths |
| **pTNAS / ATLAS** (2024–2025) | Anytime NAS: zero-cost proxy filter + budgeted refinement | **No mature pip package**; research-only | 8–12+ | GPU | High risk / high ceiling academically | Local | See [arXiv:2403.10318](https://arxiv.org/abs/2403.10318) |
| **AutoKeras** | Full NAS (CNN/MLP heads) | Slow; ill-suited to 48h unless tiny data | 4–8 | Very high | High risk; rarely best on fraud tabular | Local | `ak.ImageClassifier(max_trials=10).fit(X, y)` — **avoid for this hackathon** |

**Honest verdict for hackathon.** True tabular NAS is **not** lightweight in 2025 — production teams still use **GBDT + OpenFE/Featuretools**. For novelty + interpretability, **TabNet + SHAP on attention masks** beats running NAS papers. For score, **AutoGluon stack >> TabNet** on most fraud tables unless you have GPU time to spare.

---

### 5. Imbalanced-classification automation (SMOTE variants, class weights, threshold tuning)

| Tool | Automates | Still fixed / manual | Setup (hrs) | Train/infer cost | Risk / ceiling vs plain AutoML | Local? | Example |
|------|-----------|----------------------|-------------|------------------|--------------------------------|--------|---------|
| **`TunedThresholdClassifierCV`** (sklearn 1.4+) | Post-hoc threshold on `predict_proba` to max F1 / balanced acc / **custom business cost** | Does not change features or base model; needs good scores | 0.5 | Trivial | Low risk; **high practical lift** on fraud (recall @ fixed FPR) | Local | `TunedThresholdClassifierCV(xgb, scoring="average_precision").fit(X, y)` |
| **imblearn `Pipeline` + `GridSearchCV`** | Search over **sampler × model × hyperparams** with leak-safe CV | Search space you define; combinatorial explosion if too wide | 1–2 | Medium–high (many fits) | Medium risk; reliable PR-AUC gains | Local | `GridSearchCV(Pipeline([("s", SMOTENC(...)), ("clf", XGBClassifier())]), param_grid, scoring="average_precision")` |
| **smote-variants + `model_selection`** | **86 SMOTE variants** + automated comparison framework | Still need to pick classifier list; slow if `n_repeats` high | 2–3 | High (many sampler×model pairs) | Medium; can overfit to sampler lottery | Local | `sv.model_selection(dataset, samplers=sv.list_available(), classifiers=[("sklearn", "XGBClassifier", {})])` |
| **PyCaret `fix_imbalance`** | SMOTE (default) or any `imblearn` sampler **inside CV folds** | Default SMOTE only unless `fix_imbalance_method=` set | 0.5 | Low–medium | Low–medium risk; convenient | Local | `setup(data, target="is_fraud", fix_imbalance=True, fix_imbalance_method=BorderlineSMOTE())` |
| **FLAML `resampler=`** (2025) | Per-fold resampling inside CV/holdout | Single sampler per run; no auto-selection across variants | 0.5 | +SMOTE cost per fold | Low–medium | Local | `automl.fit(X, y, resampler=SMOTE(k_neighbors=3), metric="ap")` |
| **AutoGluon `sample_weight="balance_weight"`** | Class-balanced sample weights in supported models | Not SMOTE; tree models handle differently than neural nets | 0.5 | Low extra | Low risk | Local | `TabularPredictor(sample_weight="balance_weight", eval_metric="average_precision").fit(train)` |
| **AutoImblearn** | End-to-end: imputer + **15+ resamplers** + model HPO | Medical-data focus; heavier than needed; Docker docs | 3–5 | High | Medium; overlaps PyCaret + FLAML | Local | `AutoImblearn().fit(X, y, mode="classification", pipeline=["knn", "smote", "xgb"])` |

**Fraud-specific playbook (recommended stack).**

1. **Metric:** `average_precision` (PR-AUC) or cost-weighted scorer — never plain accuracy.
2. **Resampling:** `SMOTENC` if categoricals; else `BorderlineSMOTE` or **no SMOTE** + `scale_pos_weight` (often better on large fraud data).
3. **Threshold:** `TunedThresholdClassifierCV` on holdout for **operating point** (e.g., recall @ 1% FPR).
4. Report **precision at fixed FPR** — matches Mastercard DI false-positive narrative.

---

### 6. Bounded / capped agentic loops (constrained autoresearch)

| Tool | Automates | Still fixed / manual | Setup (hrs) | Train/infer cost | Risk / ceiling vs plain AutoML | Local? | Example |
|------|-----------|----------------------|-------------|------------------|--------------------------------|--------|---------|
| **DIY co-evolution loop** (recommended) | Fixed actions: `{add OpenFE features, swap resampler, re-fit FLAML/AG}` × **N generations**; score on **fixed holdout** | You implement action space + logging; red/blue loop separate | 3–6 | N × AutoML budget | Medium risk; **best judge story** (arms race chart) | Local | `for gen in range(5): X=apply_action(state); score=fit_flaml(X,y); state=mutate(state, score)` |
| **CAAFE** (`iterations=K`) | LLM feature loop with accept/reject | Feature-only actions; API | 2–4 | API + fits | Medium–high | API-required | `CAAFEClassifier(iterations=5, ...)` |
| **AIDE** | Tree-search over **full Python scripts**; metric feedback | Needs dataset dir + goal string; API; can diverge | 4–8 | **Very high** (many full runs) | **High risk / high ceiling** | API-required | `aide data_dir=./data goal="Maximize PR-AUC fraud" eval="average_precision"` |
| **SELA** (MetaGPT ext) | MCTS over ML pipeline stages (EDA → FE → train) | MetaGPT install; datasets; API; fragile | 8–12+ | Very high | High risk | Hybrid | `cd metagpt/ext/sela && python run_sela.py --task credit` |
| **MLAgentBench** | Benchmark env for agents (not a product) | Evaluation harness | 6+ | N/A | Research only | Local | Agent reads/writes files in `benchmarks/` task folder |

**Bounded loop design for hackathon (copy this architecture).**

```text
HOLDOUT: fixed stratified 20% — NEVER used for search, only final report + plot
SEARCH:  inner CV or FLAML with time_budget per generation

Action space (pick 3–5):
  A1: OpenFE top-k features
  A2: resampler ∈ {none, BorderlineSMOTE, class_weight balanced}
  A3: model family ∈ {FLAML 10min, AutoGluon good_quality 20min}
  A4: threshold tune on inner val only
  A5: red-agent evasion batch → append to train (closed-loop only)

Stop: max_generations=5 OR no improvement × 2
Log: PR-AUC, FPR@recall=0.8, best features, evasion rate
```

This is **not** full autoresearch — the LLM (if used) only proposes actions from the menu; your script executes.

---

### 7. Master ranking — implementation effort × expected lift (2–3 day window)

**Scoring.** Effort **E** (1=trivial … 5=multi-day). Expected **lift** **L** (1=marginal … 5=large PR-AUC / judge impact). **ROI = L/E** (higher = do first).

| Rank | Approach | E | L | ROI | 🎤 Novelty | 🔧 Practical |
|------|----------|---|---|-----|------------|--------------|
| 1 | **AutoGluon `best_quality` + `eval_metric=average_precision` + `balance_weight`** | 1 | 4 | 4.0 | 🔧 | ✅ |
| 2 | **OpenFE → AutoGluon/FLAML pipeline** | 2 | 4 | 2.0 | 🎤 (IEEE-CIS proven) | ✅ |
| 3 | **`TunedThresholdClassifierCV` on best model** | 1 | 3 | 3.0 | 🔧 | ✅ |
| 4 | **FLAML + `resampler=SMOTENC` + `metric="ap"`** | 1 | 3 | 3.0 | 🔧 | ✅ |
| 5 | **imblearn Pipeline + narrow GridSearch** (2 samplers × XGB) | 2 | 3 | 1.5 | 🔧 | ✅ |
| 6 | **DIY LLM feature suggestions → manual pandas** | 2 | 4 | 2.0 | 🎤 ✅ | partial |
| 7 | **Featuretools** (if relational txn data) | 3 | 4 | 1.3 | 🎤 (graph-adjacent) | ✅ |
| 8 | **Bounded co-evolution loop** (scripted actions + holdout) | 4 | 5 | 1.25 | 🎤 ✅✅ | ✅ |
| 9 | **auto-sklearn 2.0** (60 min budget, F1/AP metric) | 2 | 3 | 1.5 | 🔧 | ✅ |
| 10 | **PyCaret `fix_imbalance` + `compare_models`** | 1 | 2 | 2.0 | 🔧 | ✅ |
| 11 | **CAAFE** (`iterations=3`, fraud description) | 3 | 4 | 1.3 | 🎤 ✅ | partial |
| 12 | **tsfresh** on per-user txn windows | 3 | 3 | 1.0 | 🔧 | ✅ |
| 13 | **smote-variants auto `model_selection`** | 3 | 2 | 0.7 | 🔧 | marginal |
| 14 | **TabNet + attention explainability** | 4 | 2 | 0.5 | 🎤 (interpretable DL) | partial |
| 15 | **AIDE** (tree-search full scripts) | 4 | 4 | 1.0 | 🎤 ✅ | ❌ risky |
| 16 | **AutoFeat / evo-gpfe** | 3 | 2 | 0.7 | 🔧 | niche |
| 17 | **SELA / MLAgentBench agent** | 5 | 3 | 0.6 | 🎤 ✅ | ❌ |
| 18 | **TabNAS / pTNAS research code** | 5 | 2 | 0.4 | 🎤 academic | ❌ |
| 19 | **AutoImblearn** | 4 | 2 | 0.5 | 🔧 | overlap |
| 20 | **EvolutionaryForest** | 4 | 2 | 0.5 | 🎤 GP | niche |

---

### 8. Recommended 48-hour Defend build path

**Day 1 morning (floor).** FLAML 10 min (`metric="ap"`) + AutoGluon 30 min (`best_quality`, `average_precision`) on raw features → leaderboard baseline.

**Day 1 afternoon (mid-tier lift).** OpenFE (or Featuretools if multi-table) → re-run AutoGluon. Add `TunedThresholdClassifierCV` on holdout. Narrow imblearn search: `{none, BorderlineSMOTE}` × XGB `scale_pos_weight`.

**Day 2 morning (novelty layer).** One LLM session: schema + leaderboard → implement 3 domain features (velocity z-score, new-payee flag, night-time amount ratio). Optional: CAAFE `iterations=2` if API key ready.

**Day 2 afternoon (closed loop).** Bounded outer loop: red agent adds evasion batch → blue retrains (action A5 above) → plot PR-AUC vs generation. **Do not** let an LLM rewrite the whole pipeline overnight.

**Inference story for judges.** Ship **FLAML single model** or **AutoGluon with `predictor.persist()` + distill** for demo latency; keep heavy stack for offline retrain.

---

### 9. Novelty vs invisible — what to say on stage

| Say this (novelty) | Don't oversell (invisible plumbing) |
|--------------------|-------------------------------------|
| "OpenFE + co-evolutionary retrain on synthetic red-team evasions" | "We used GridSearchCV" |
| "Context-aware LLM feature ideation for fraud semantics (CAAFE-style)" | "We set `class_weight=balanced`" |
| "Bounded agent loop — fixed holdout, capped actions — not black-box autoresearch" | "SMOTE in the pipeline" |
| "PR-AUC + threshold tuned for 1% FPR operating point" | "TunedThresholdClassifierCV wrapper" |
| Featuretools graph aggregations → "network-adjacent velocity features" | Raw `count(transactions)` |

---

### 10. References (tools & papers)

| Resource | URL |
|----------|-----|
| OpenFE (IEEE-CIS fraud) | [github.com/IIIS-Li-Group/OpenFE](https://github.com/IIIS-Li-Group/OpenFE) |
| Featuretools | [featuretools.alteryx.com](https://featuretools.alteryx.com/) |
| CAAFE | [github.com/automl/CAAFE](https://github.com/automl/CAAFE) |
| auto-sklearn 2.0 | [JMLR 23(261)](http://jmlr.org/papers/v23/21-0992.html) |
| AutoGluon presets | [auto.gluon.ai tabular-indepth](https://auto.gluon.ai/stable/tutorials/tabular/tabular-indepth.html) |
| FLAML resampler PR | [microsoft/FLAML#1568](https://github.com/microsoft/FLAML/pull/1568) |
| TunedThresholdClassifierCV | [sklearn classification_threshold](https://scikit-learn.org/stable/modules/classification_threshold.html) |
| smote-variants | [github.com/analyticalmindsltd/smote_variants](https://github.com/analyticalmindsltd/smote_variants) |
| AIDE | [github.com/WecoAI/aideml](https://github.com/WecoAI/aideml) |
| SELA | [arXiv:2410.17238](https://arxiv.org/abs/2410.17238) |
| TabNAS | [NeurIPS 2022](https://proceedings.neurips.cc/paper/2022/file/4e392aa9bc70ed731d3c9c32810f92fb-Paper-Conference.pdf) |
| pTNAS | [arXiv:2403.10318](https://arxiv.org/abs/2403.10318) |
| OCTree | [NeurIPS 2024 paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/a7ebe2e8d8cfd2fcec6cd77f9e6fd34d-Paper-Conference.pdf) |
