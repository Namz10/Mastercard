# Identify Pipeline Strategy — Mastercard Innovation Challenge 2026

**Purpose.** Working strategy document for the Identify pillar of the AI Defense Lab submission. Defines how we source, verify, score, and structure GenAI payment-fraud attack vectors so they plug directly into the Generate and Defend pillars, rather than existing as a standalone research exercise.

**Relationship to the main brief.** This document assumes the lifecycle taxonomy, typology catalog, and scoring criteria in `HACKATHON_RESEARCH.md` (Section 3) as the *content* map. This document is the *process* by which we populate, validate, and confidence-score that catalog.

**Planning spine.** Schema, technique IDs, and agent graph are locked in [`LOCKED.md`](LOCKED.md) and [`plans/01-identify-catalog-lock.md`](plans/01-identify-catalog-lock.md). `canary_mode` is a Generate pin to a documented case. Frozen model-eval sets are **HoldoutVault**, not “Canary Vault”.

---

## 1. Design principle

The Identify pillar is graded on **breadth and depth of attack vectors**, but its real function in the product is upstream of Generate: every entry in the catalog must be structured enough that the Generate pillar can consume it programmatically. A well-researched but unstructured taxonomy is a blog post, not a pipeline component. Everything below is designed around one output: **a machine-readable, confidence-scored attack catalog.**

We deliberately reject a three-separate-methodologies structure (scrape / OSINT-verify / honeypot-validate) in favor of a single collection method with **graded source confidence**, plus **evidence-type-specific corroboration** where it's actually available. This is both more honest about what each method can prove and more defensible under judge questioning.

---

## 2. Pipeline stages

```
Broad Collection  →  Source-Tier Confidence Scoring  →  Type-Specific Corroboration  →  Structured Catalog Entry  →  Canary Validation (via Generate)
```

### 2.1 Broad collection

Cast a wide net across public sources to generate **candidate vectors**. No filtering at this stage beyond excluding sources that would require accessing illicit infrastructure (dark-web forums, criminal marketplaces, jailbreak-as-a-service sites) — those are never accessed, even for research legitimacy.

**Source categories:**
- Regulatory and government: FinCEN alerts, RBI discussion papers, FATF typology reports, US Treasury AI-risk reports
- Academic: peer-reviewed papers and preprints (e.g. arXiv:2410.09066), published red-team / liveness-bypass studies
- Industry/vendor: Feedzai, Wipro, BNY, Deloitte, Amazon Payment Services research and blogs
- News and case reporting: documented incidents (e.g. Hong Kong deepfake CFO case), court filings, press coverage
- Existing public threat telemetry: Honeynet Project, Shadowserver, GreyNoise, SANS/DShield — used for network-layer corroboration, not general candidate sourcing

Each candidate vector, however sourced, enters the pipeline as **unconfirmed** until scored.

### 2.2 Source-tier confidence scoring

Every candidate is scored by the tier of its supporting source(s):

| Tier | Examples | Weight |
|------|----------|--------|
| **1 — Regulatory / judicial** | FinCEN alerts, court filings, RBI/central bank papers | Highest |
| **2 — Peer-reviewed / red-team research** | Academic papers, published liveness-bypass or red-team studies, DHS remote identity-proofing evaluations | High |
| **3 — Vendor / industry survey** | Feedzai, Wipro, Deloitte, BNY reports | Medium |
| **4 — News / press reporting** | Single-outlet coverage of an incident | Low-medium |
| **5 — Forum / unverified mention** | Single social or forum reference | Lowest — flag only, do not confirm alone |

**Confirmation rule:** a vector is marked **"confirmed"** only if it clears Tier 1 or Tier 2 alone, **or** is corroborated by two **independent organizations** at Tier 3 or better (not a news reprint of the same regulator alert, not two URLs on the same domain). Anything resting on a single Tier 3–5 source (e.g. one vendor's "1,210% surge" statistic) is tagged **"reported, unverified"** in the catalog and carried forward with that label intact — not silently upgraded.

### 2.3 Type-specific corroboration

Confirmation tier alone doesn't capture *how* a vector should be validated, because GenAI payment fraud splits into two evidentially different classes:

| Vector class | Corroboration method | Why |
|---|---|---|
| **Technical / network-footprint** (bot-driven onboarding, credential stuffing, card testing, scanning) | Cross-check against live public telemetry (GreyNoise, Shadowserver, DShield) when APIs are configured; otherwise leave `not-yet-corroborated` | These can leave an observable network trace; telemetry confirms infrastructure activity *now*, not just a historical write-up. Telemetry never “confirms” deepfake KYC |
| **Human / social-engineering** (deepfake KYC, voice clone, APP scam, BEC impersonation) | Documented incident case studies, regulator alerts, published red-team / liveness-bypass research | These happen through human interaction, not network intrusion — traditional honeypots cannot observe them, so documentary evidence from Tier 1–2 sources is the corroboration that exists |

This distinction is stated explicitly in the catalog and in the write-up: it is not a weakness that honeypots don't validate deepfake-KYC vectors — it is the exact diagnosis the challenge's own reference paper (Kurshan et al.) makes about why static, network-layer detection lags behind sophisticated human-facing attacks.

### 2.4 Structured catalog entry

Every confirmed (or flagged) vector is written into a common schema so Generate can consume it without manual translation:

| Field | Description |
|---|---|
| `vector_id` | Unique identifier |
| `name` | Short descriptive name |
| `rail` | Card / A2A-UPI / onboarding / commercial-BEC / other |
| `genai_modality` | Text / voice / video / document / bot |
| `lifecycle_stage` | Onboarding-KYC / account-access-ATO / payment-initiation / authorization / clearing-settlement / disbursement-mule / dispute-SAR |
| `control_bypassed` | e.g. liveness check, voice biometric, OTP, human callback, velocity rule; **Merchant / business:** business document verification, UBO / beneficial-ownership check, MCC classification check, bank-account ownership match |
| `actor_type` | Consumer / Merchant — which side of the payment the attack targets; determines whether consumer-authentication controls or merchant/KYB controls apply |
| `source_tier` | 1–5, per Section 2.2 |
| `confidence_level` | Confirmed / reported-unverified |
| `corroboration_type` | Network telemetry / documentary-case / not yet corroborated |
| `source_urls` | Citations backing the tier/confidence rating — one URL per supporting source, listed best-tier first; required for confirmed entries, enables canary cases to pin their documented incident |
| `simulatable_signals` | Concrete fields the Generate pillar needs: transaction pattern, timing/velocity, device signals, graph structure, seasoning behavior, etc. |
| `canary_eligible` | Boolean — is this vector well-documented enough (Tier 1–2) to anchor a targeted canary test case |

The `simulatable_signals` and `canary_eligible` fields are the hand-off points to Generate — this is what keeps Identify from being a research appendix.

### 2.5 Canary validation (executed inside Generate, not Identify)

Validation of "does our system actually reproduce and catch this vector" is not performed via a live honeypot. Real honeypots require weeks-to-months of attacker discovery time to produce meaningful signal, and vectors requiring human social engagement (mule recruitment lures, fake investment pages) would require knowingly interacting with real criminal actors — both are outside what should be built into a hackathon submission.

Instead, validation runs as a **targeted mode of Generate**:

- **Canary accounts** are synthetic entities seeded into the same sandbox as bulk-generated training data.
- Unlike bulk generation (which samples vectors/parameters broadly for training volume), a canary case pins its **attack parameters** to match one specific, `canary_eligible` (Tier 1–2 confirmed) real-world case as closely as possible — e.g. reproducing the FinCEN-documented pattern of deepfake-KYC onboarding → seasoning period → large inbound APP credit → rapid cash-out.
- The red agent executes the attack against the canary using the catalog's `simulatable_signals`; the current blue model's **defend parameters** (feature set, thresholds, decision policy) score it.
- Outcome is logged as a labeled validation checkpoint: did the detector catch the documented pattern, and at what lifecycle stage — feeding directly into the co-evolution loop's "gaps feed back into new attack ideas" mechanism.

This makes canary validation a checkpoint *within* the closed loop rather than a separate research stage, and it is described to judges accordingly: "simulated canary accounts used to validate that our detector correctly catches known, documented attack patterns" — not implied to be live-attacker engagement.

---

## 3. Why this shape over the alternatives considered

| Alternative considered | Why not used as designed |
|---|---|
| Three fully separate stages (scrape / OSINT-verify / honeypot-validate) | Scrape and documentary verification are mechanically the same action (fetching and reading public text); presenting them as distinct methodologies overstates independence |
| Honeypots as the general validation method | Public honeypots (Honeynet, Cowrie, T-Pot) observe network/infrastructure-layer attacks only; they cannot see deepfake KYC, voice cloning, or APP scams, which are human-interaction-driven and are the harder, more current class the brief emphasizes |
| Live bait content to attract real scammers (fake mule job ads, seeded scam-bait phone numbers) | Risks real engagement with criminal actors, potential real-victim data collection, and legal/compliance exposure under hackathon time pressure — avoided regardless of timeline |
| Standalone unrestricted web-crawling as a demo feature | Adds engineering risk for a stage judges spend little time on. Optional allowlisted researcher agent on fixtures / Tavily is the demo; Firecrawl crawl is not |

---

## 4. Output contract with Generate

Identify's sole deliverable to the rest of the system is the structured catalog (Section 2.4). Generate consumes it in two modes:

1. **Population mode** — samples across catalog entries (weighted or distributional) to produce bulk synthetic attack + benign traffic for training and stress-testing.
2. **`canary_mode`** — pins to a single `canary_eligible` entry to reproduce one documented case exactly, for validation against the current blue model. Frozen promotion holdouts are **HoldoutVault**, not this mode.

Both modes read the same schema. This is what keeps Identify, Generate, and Defend functioning as one product rather than three side projects — the explicit failure mode the brief calls out.

---

## 5. Summary statement (for the write-up)

> Our Identify pillar curates candidate GenAI payment-fraud vectors from regulatory, academic, vendor, and news sources, scoring each by source tier and marking a vector confirmed only when it clears a top tier or is corroborated across two independent tiers. Corroboration is evidence-type-specific: network-footprint vectors are cross-checked against live public attack telemetry, while human/social-engineering vectors — the harder and more current class — are corroborated through documented incident case studies and published red-team research, since these evade the network-layer detection traditional honeypots are built to catch. Every confirmed vector is written into a structured schema consumed directly by our Generate pillar in two modes: bulk population-scale simulation for training, and targeted canary cases pinned to specific documented incidents for validating that our detector catches known real-world patterns. This keeps Identify tightly coupled to the closed loop rather than standing alone as a research appendix.
