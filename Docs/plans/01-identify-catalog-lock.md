# Plan 01 — Identify pillar and KillChain Atlas (locked)

**Status:** LOCKED.

**Depends on:** [`00-correct-planning-defects.md`](00-correct-planning-defects.md) global locks.

**SSOT:** [`MC_PS.md`](../MC_PS.md) Identify = exhaustive, grounded, novel GenAI **payment** fraud. [`HACKATHON_RESEARCH.md`](../HACKATHON_RESEARCH.md) §3 = content map (lifecycle + typology). Process: patched [`Updated Identify Phase.md`](../Updated%20Identify%20Phase.md).

**Job.** Diversity score = coverage of **lifecycle × rail × economic class**, not 24 generation pipelines. Output is one Pydantic `AttackSpec` catalog Generate and Defend can consume.

---

## 1. Component names

- Store / UI: **KillChain Atlas**
- Model: **`AttackSpec`** in `packages/catalog/`
- Graph: `identify_graph` in `packages/agents/`
- Fetch: `packages/osint/`

---

## 2. Twenty-four techniques (IDs `T01`–`T24`)

Derived from HACKATHON_RESEARCH §3 and [`decisions.md`](../decisions.md) A1. This is the threat-map census. Write-up line: *24 techniques grouped into 5 structural categories.*

### Cat 1 — Network / transaction structuring

| ID | Name | generate_mode | Notes |
|---|---|---|---|
| T01 | Mule fan-in funnel | `generate` | Many senders → new/low-KYC account |
| T02 | Mule fan-out cash-out | `generate` | Burst outbound to sinks (taxonomy: cash/crypto/gaming; sim uses MCC/sink flags, not live rails) |
| T03 | UPI-cap smurfing | `generate` | Amounts just under product caps |
| T04 | Rail hop UPI ↔ IMPS-like ↔ wallet | `generate` | Typed hops in sim time |
| T05 | Dust / layering | `generate` | Many tiny outbound edges |
| T06 | Synthetic merchant collusion | `generate` if merchant nodes exist; else `name_only` + named gap | Cycle + refund burst |
| T07 | Card testing / BIN enumeration | `name_only` (stretch: proxy injector after loop works) | Auth-plane, not UPI transfer graph |

### Cat 2 — Identity

| ID | Name | generate_mode | Notes |
|---|---|---|---|
| T08 | Synthetic identity mix | `generate` | Structured fields only; no real ID numbers |
| T09 | Deepfake VKYC / liveness bypass | `generate` **flags only** | `liveness_score`, channel-switch flags; **no video/audio files** |
| T10 | KYC document field forgery | `generate` | Text/fields; no images |
| T11 | Identity farming / ~150d seasoning | `generate` | Quiet then burst |
| T12 | ATO device / session shift | `generate` | New device + velocity |

### Cat 3 — Social engineering / APP

| ID | Name | generate_mode | Notes |
|---|---|---|---|
| T13 | UPI impersonation APP (India) | `generate` | Customer-authorized; new/mule payee; session flags |
| T14 | Family / emergency voice-clone APP | `generate` | Flags + optional capability-limited transcript |
| T15 | Romance / investment long-con APP | `generate` | Same; public repo is templated, not operator playbooks |
| T16 | Voice-clone BEC / CFO (commercial) | `generate` | Linked Cat 5 beneficiary change when invoice-timed |
| T17 | Polymorphic phishing / smishing | `generate` | Labels + session; no live send |
| T18 | Invoice-timed impersonation | `generate` | Session + Cat 5 fields |
| T19 | Live MFA-relay **class** | method `name_only`; **session flags `generate`** | Do not name criminal tools in the public repo; signal = call + paste + new payee + OTP timing |

### Cat 4 — Model / pipeline-targeted (the loop, not an engine)

| ID | Name | generate_mode | Notes |
|---|---|---|---|
| T20 | Detector evasion / probing | Cat 4 Loop A | Masked `x_adv` only |
| T21 | Training-data poisoning | Cat 4 + trust tiers | Mislabeled mix cap; canary = HoldoutVault veto |
| T22 | Detector fingerprinting | `name_only` in UI; Loop A query cap is the control | Oracle Guard |
| T23 | KYC/LLM supply-chain, merchant-bot injection, agentic payment | `name_only` + tag Cat 3∩4 | Do not simulate attacking a third-party vendor |

### Cat 5 — Document / content forgery

| ID | Name | generate_mode | Notes |
|---|---|---|---|
| T24 | Beneficiary / invoice rewrite + dispute-pack field forgery | `generate` | Genuine-looking tax math + **wrong account**; checksum-pass cases matter; no letterhead images |

**Also named on the lifecycle map (not extra IDs):** nested PSP, cross-border last mile, 3DS/token misuse, QR overlay, refund-to-wrong-VPA, SIM-swap as social assist, friendly fraud. These are Identify extras / `name_only` cards if needed for empty lifecycle×rail cells (Loop C), not a 25th–30th required generate path.

### V1 eight-family aliases (not a second taxonomy)

| V1 family | Maps to |
|---|---|
| Synthetic ID / deepfake KYC | T08, T09, T10, T11 |
| Voice-clone ATO / call-center | T12, T14, T19 flags |
| APP / impersonation (India) | T13, T15, T17 |
| BEC / deepfake CFO | T16, T18, T24 |
| CNP / bot + synthetic card | T07 (`name_only` unless stretch) |
| Mule / funnel cash-out | T01, T02, T03, T04, T05 |
| Seasoned synthetic bust-out | T11 + T01/T02 |
| Detector probing / poisoning | T20, T21, T22, T23 |

---

## 3. Unified `AttackSpec` (Pydantic v2)

One model for YAML seed, Postgres Atlas, Extractor JSON, Generate hand-off.

```text
vector_id: str                    # ULID or stable slug
technique_id: T01..T24
name: str                         # alias: title
one_liner: str | None
category: 1..5
rail: upi_like | imps | neft | rtgs | card_cnp | card_cp | wire | crypto_offramp | onboarding
lifecycle_stage:
  onboarding_kyc | account_access_ato | payment_initiation | authorization
  | clearing_settlement | disbursement_mule | dispute_sar
genai_modality: text | voice | video | document | bot | poisoning | mixed
social_surface: email | sms | voice | video_call | in_app | merchant | none
control_bypassed: list[str]       # alias: failed_control
  consumer examples: liveness, voice_bio, otp, static_kyc, velocity_rule, human_callback
  merchant examples: business_doc_kyc, ubo_check, mcc_classification, bank_account_ownership
actor_type: consumer | merchant
economic_class: APP | ATO | CNP | mule | BEC | detector
is_authorized_push: bool
generate_mode: generate | name_only
dual_use_rating: low | medium | high   # high ⇒ rejected_unsafe unless generate_mode=name_only
source_tier: 1..5
confidence_level: confirmed | reported-unverified
corroboration_type: network-telemetry | documentary-case | not-yet-corroborated
vector_class: network_footprint | human_social
source_urls: list[HttpUrl]        # best-tier first; alias: citations
simulatable_signals: dict         # validated against injector schema
canary_eligible: bool
simulator: { injector_id: str, param_schema: dict }
features_expected: list[str]      # alias: feature_contract
entities: list[str]               # victim, mule, merchant, device, ...
novelty_notes: str | None
status: proposed | rejected | rejected_unsafe | open | generating | defending | solved
```

**Required for `confidence_level=confirmed`:** at least one `source_urls` entry.

**Grounder rejects if:** no payment `rail`; GenAI as buzzword only (no `control_bypassed`, no `economic_class`); cosine > **0.92** vs existing `name`+`rail` embedding; exploit-step / payload / criminal-market how-to (keep high-level typology only).

---

## 4. Source-tier scoring (deterministic)

| Tier | Meaning | Examples |
|---|---|---|
| 1 | Regulatory / judicial | FinCEN, FTC, RBI, court filings, US Treasury AI-risk papers |
| 2 | Peer-reviewed / published red-team | arXiv:2410.09066, DHS remote identity-proofing evals |
| 3 | Vendor / industry | Feedzai, Wipro, Deloitte, BNY, Amazon Payment Services blog |
| 4 | News | Reuters, BBC, FT on documented incidents |
| 5 | Forum / unverified | Single social mention — flag only |

**Confirmation rule.** `confirmed` iff:

- any supporting source has `source_tier <= 2`, **or**
- ≥2 **independent organizations** at tier ≤ 3.

Else `reported-unverified`. Never silently upgrade a single vendor “1,210% surge” statistic.

**Independence.** Different registrable organizations. Same domain, same parent, or a news reprint of a regulator alert = **not** independent.

### Domain → tier table (v1 freeze)

| Domain | Tier |
|---|---|
| fincen.gov | 1 |
| ftc.gov | 1 |
| rbi.org.in | 1 |
| treasury.gov | 1 |
| arxiv.org | 2 |
| dhs.gov | 2 |
| feedzai.com | 3 |
| wipro.com | 3 |
| deloitte.com | 3 |
| bny.com | 3 |
| paymentservices.amazon.com | 3 |
| reuters.com | 4 |
| bbc.com | 4 |

Unknown allowlisted domain: default tier **4** until a human edits the table. Mastercard.com may return Akamai 403 — **do not scrape around it**; use secondary reporting already in HACKATHON_RESEARCH and mark the citation as secondary.

---

## 5. Corroborator (deterministic + optional APIs)

1. Set `vector_class`:
   - `network_footprint` if `genai_modality` in {bot} **or** `technique_id` in {T01,T02,T03,T04,T05,T07} **or** controls include scanning / stuffing / card-testing.
   - else `human_social`.
2. If `human_social`: `corroboration_type = documentary-case` when `confidence_level=confirmed`; else `not-yet-corroborated`. **Never** call GreyNoise.
3. If `network_footprint` and telemetry clients configured: optional GreyNoise / Shadowserver / DShield lookup. Hit → `network-telemetry`. Miss or timeout → do not fake a hit; keep `not-yet-corroborated` (tier/confidence still stand).
4. `canary_eligible = true` **iff all of:** `confidence_level=confirmed`; best `source_tier <= 2`; `generate_mode=generate`; `simulatable_signals` validates against `simulator.param_schema`.

---

## 6. `simulatable_signals` contracts (minimum keys)

Generate **must** reject catalog rows that claim `generate` but fail these schemas. Extra keys allowed; missing required keys fail Pydantic.

**Cat 1** (`injector_id`: `graph_mule`):

- `fan_in_1h` (int ≥ 0)
- `fan_out_ttl_hours` (float > 0)
- `smurf_cap_ratio` (float in (0,1], 1 = at cap)
- `hop_rails` (list of rail enums)
- `mule_account_age_days` (int ≥ 0)
- `cashout_mcc_or_sink` (str)

**Cat 2** (`injector_id`: `identity_trajectory`):

- `seasoning_days` (int)
- `seasoning_txn_count` (int)
- `liveness_score` (float 0–1, simulated)
- `doc_consistency` (float 0–1, simulated)
- `device_hash_shift` (bool)
- `kyc_tier` (str)

**Cat 3** (`injector_id`: `app_session`):

- `persuasion_labels` (list[str])
- `call_active_flag` (bool)
- `copy_paste_payee_flag` (bool)
- `pause_ms` (int ≥ 0)
- `new_payee` (bool)
- `urgency_pressure` (float 0–1)
- `transcript_ref` (str | null) — optional; templates only in public repo

**Cat 5** (`injector_id`: `doc_beneficiary`):

- `beneficiary_changed` (bool)
- `gstin_checksum_ok` (bool)
- `amount_vs_invoice_delta` (float)
- `lookalike_domain_flag` (bool)

**Cat 4 patches** (not a bulk injector; Loop A):

- `x_adv` allowlist only: amount jitter, mule payee among **owned** synthetic accounts, device rotate.
- Forbidden: `generator_id`, `persona_id`, full-graph stats, future edges, post-auth transcripts, SHAP/tree dumps to the attacker.

---

## 7. `identify_graph` nodes (v1 linear)

No parallel specialist swarm.

### 7.1 Scout

- Input: optional topic (default: “GenAI payment fraud regulator alert”).
- Calls: RSS (FinCEN, FTC, arXiv API) always; Tavily Search **only if** `IDENTIFY_LIVE_SEARCH=true`, with `include_domains` = allowlist.
- Output: `candidate_urls[]` with `source_domain`, `snippet`, `fetched_at`.
- **Safety:** never query dark-web, criminal-market, jailbreak-as-a-service, or exploit-payload terms. Fixture mode reads `data/osint/fixtures/`.

### 7.2 Extractor

- Body: Tavily Extract **or** `httpx` + trafilatura. If `OSINT_EXTRACTOR=firecrawl`, single-URL scrape on allowlisted hosts only — **no site crawl**.
- LLM structured output → partial `AttackSpec` (temperature ≤ 0.2, retry on validation fail).
- Store raw chunk + embedding in Qdrant payload `{url, date, source_type, domain}`.

### 7.3 Grounder

Deterministic rules in §3 plus light LLM optional for “is this payments + GenAI?”. Reject list is binding.

### 7.4 TierScorer

Domain table + independence aggregation → `source_tier`, `confidence_level`.

### 7.5 Corroborator

§5.

### 7.6 Librarian

Merge vs Postgres Atlas; bump depth on duplicates; route `status=proposed` → **HITL interrupt**. On approve → `open` (visible on threat map). On dual-use fail → `rejected_unsafe`.

**HITL payload:** diff vs nearest existing `technique_id`, tier badges, `source_urls`, `vector_class`, `generate_mode`, preview of `simulatable_signals`. Actions: approve / reject / edit fields / reject_unsafe.

---

## 8. Collection policy

| Mode | Flag | What runs |
|---|---|---|
| Airplane / default demo | `IDENTIFY_LIVE_SEARCH=false` | Fixtures (FinCEN alert text, RBI-style note) in `data/osint/fixtures/` |
| Live demo | `true` + `TAVILY_API_KEY` | Allowlisted Search + Extract |
| Telemetry | optional `GREYNOISE_API_KEY` | Network-footprint only |

Local corpus for `kb_search` / RAG: fixture markdown + seed citations. Identify tools: `kb_search`, `kb_get_chunk`, `upsert_taxonomy`. Unrestricted Google/scrapy/Firecrawl-crawl: **forbidden**.

---

## 9. Seed catalog

- Path: `data/catalog/seed.yaml`.
- **28–36 rows** covering **all 24 `technique_id`s** (name_only rows still catalogued so the map is full on day 1).
- Hand-transcribe from HACKATHON_RESEARCH §3 with `source_urls` and pre-filled tiers. FinCEN/arXiv-backed rows start `open`.
- Agents **add** rows; they do not start from empty.

**Demo `canary_mode` pin (locked):** FinCEN FIN-2024-Alert004 pattern as a **composite campaign**, not one technique:

1. T09 flags (deepfake KYC) → 2. T11 seasoning → 3. T13 large inbound APP credit → 4. T02 rapid cash-out.

Catalog may store this as one `vector_id` with `technique_id` primary T13 and `novelty_notes` listing the chain, **or** a campaign object in Generate config that lists those four `vector_id`s. Generate Plan 02 must pin **all** attack parameters from those rows’ `simulatable_signals`.

---

## 10. Embeddings and dedup

- Model: local `BAAI/bge-small-en-v1.5` (sentence-transformers).
- Qdrant filterable by `source_type`, `date`, `domain`.
- Dedup key: embedding of `name` + `rail` + `technique_id`; cosine > 0.92 → merge depth, do not insert a clone (Loop C must not spawn five CNP clones).

---

## 11. Merchant / actor coverage (gap closed)

`actor_type` is required. Consumer APP/ATO/mule is the v1 generate volume. Merchant-side depth in v1 = T06 (if nodes exist), T16/T18/T24 (BEC/invoice). KYB controls belong on `control_bypassed` even when `generate_mode=name_only` so Loop I does not invent a live selfie-model rule.

---

## 12. Identify success criteria (demo + write-up)

- Threat map shows all 24 IDs with status chips, `confidence_level`, `source_tier`.
- Run Identify on a fixture → 1–3 `proposed` rows → HITL → `open`.
- Every `generate` row has a valid `simulatable_signals` blob.
- Citations on confirmed rows.
- No dark-web, no exploit steps, no live criminal tooling.
