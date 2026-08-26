# Plan 00 — Correct planning defects and lock the spine

**Status:** LOCKED. Do not reopen forks listed here.

**Role.** This file kills every documented defect, inconsistency, and competing-architecture fork. After this layer, [`plans/01-identify-catalog-lock.md`](01-identify-catalog-lock.md), [`plans/02-generate-defend-loop-lock.md`](02-generate-defend-loop-lock.md), and [`plans/03-platform-demo-build-lock.md`](03-platform-demo-build-lock.md) are the only design authorities besides the problem-statement SSOT.

**SSOT for every lock:** [`MC_PS.md`](../MC_PS.md) (judges’ rubric: one closed-loop Identify → Generate → Defend product; diversity, fidelity, detection efficacy, novelty, live-payments feasibility) then [`HACKATHON_RESEARCH.md`](../HACKATHON_RESEARCH.md) (typology, APP vs stolen-credential, latency/FP, co-evolution, safety). Other repo docs are **inputs to merge**, not competing authorities.

**Companion:** repo-root [`LOCKED.md`](../LOCKED.md) is the one-page pointer judges and implementers should read first.

---

## 0. Global locks (canonical; copied into Plans 01–03)

These decisions are closed.

1. **One product, three pillars, one loop.** Identify is a machine-readable catalog, not a blog. Generate is labeled synthetic events. Defend is score + reason + action. Gaps feed new catalog tickets and oversample. Matches the MC_PS closed-loop sentence.

2. **Product name:** AegisLoop (UI). **Components:** KillChain Atlas, ShadowRail, rail-rules, PulseFeatures, AuthGate, CaseScore, Brake, Oracle Guard, LoopGovernor, HoldoutVault, RedBlue Console. Drop the name “Canary Vault”.

3. **Repo layout:** [`V1_MASTERPLAN.md`](../V1_MASTERPLAN.md) §3.2 (`apps/web`, `apps/api`, `packages/{agents,catalog,osint,sim,features,models,policy,eval}`). Orchestration: LangGraph supervisor + subgraphs. Supervisor routing is **deterministic**.

4. **LLM never writes the ledger and never sits on authorization.** Live path: rules → compact GBDT → Brake. LLM: Identify extraction, GapAnalyst/rule drafts, Cat 3 language, case tab.

5. **Safety:** synthetic customers/rails only; no dark web; no criminal LLMs; no live phishing; no real deepfake media; no exploit steps. Identify = public typology. Cat 4 offline, not on the public generate API.

6. **Diversity story (write-up):** “24 techniques grouped into 5 structural categories; v1 generates 4 engines (1, 2, 3, 5); Cat 4 is the loop.” V1’s 8 families are **aliases** of those 24, not a second taxonomy. Mapping is in Plan 01.

7. **Primary simulated rail:** UPI-like instant credit-push (India / GFF). Card / 3DS / BIN testing remain **on the threat map as `name_only`** unless a stretch CNP proxy injector is added **after** the closed loop works. Do not ship a fake ISO-8583 network.

8. **Defend champion:** AuthGate = **FLAML-selected LightGBM** (or single GBDT), Optuna/FLAML, PR-AUC, graph features from `G(t−)` only. AutoGluon `best_quality` is **optional overnight challenger**, never the live scorer.

9. **Identify collection:** Local corpus + fixtures are the default (`IDENTIFY_LIVE_SEARCH=false`). Optional demo: Tavily Search/Extract with `include_domains` allowlist only. Firecrawl is feature-flag **extract** fallback, not crawl. No open-web swarm.

10. **Two “canary” concepts renamed:**
    - `canary_mode` — Generate pins one `canary_eligible` documented case (FinCEN-style).
    - `HoldoutVault` — frozen G-test + real-proxy tables for promotion. Any “canary regression” in older docs means HoldoutVault regression.

11. **Catalog workflow statuses (single enum):** `proposed | rejected | rejected_unsafe | open | generating | defending | solved`. HITL approve turns `proposed` → `open`. LoopGovernor moves `open` → `generating` → `defending` → `solved`.

12. **Co-evolution:** Cat 4 Loop A (masked JSON patch + verifier) **plus** Loop G numeric param search (nevergrad-class; code executes). LLM proposes; code applies; Oracle Guard caps queries. Never train/report on the same generator split.

13. **Identify graph (v1):** linear Scout → Extractor → Grounder → TierScorer → Corroborator → Librarian + HITL interrupt. No parallel specialist swarm.

---

## 1. Document bugs (exact patches)

### 1.1 Corrupted §2.3 table in `Updated Identify Phase.md`

**Defect.** Two vector classes were merged into one table row mid-sentence (“infrastr Documented incident…”). Corroborator logic was not implementable.

**Lock / patch.** Restore two rows:

| Vector class | Corroboration method | Why |
|---|---|---|
| **Technical / network-footprint** (bot-driven onboarding, credential stuffing, card testing, scanning) | Cross-check against live public telemetry (GreyNoise, Shadowserver, DShield) when APIs are configured; otherwise leave `not-yet-corroborated` | These can leave an observable network trace; telemetry confirms infrastructure activity *now*, not just a historical write-up |
| **Human / social-engineering** (deepfake KYC, voice clone, APP scam, BEC impersonation) | Documented incident case studies, regulator alerts, published red-team / liveness-bypass research | These happen through human interaction, not network intrusion — traditional honeypots cannot observe them |

**Honesty lock.** GreyNoise-class APIs corroborate **only** `vector_class=network_footprint`. Never claim telemetry “confirms” deepfake KYC.

**Independence lock.** “Two Tier ≤3 sources” means **two different organizations**, not a Reuters reprint of a FinCEN alert, not two URLs on the same domain, not a vendor blog citing its own survey twice.

### 1.2 Corrupted §3 alternatives table

**Defect.** The honeypot-reject row concatenated with a stray “Human / social-engineering vectors” row and a leftover fragment (“ucture is active *now*…”).

**Lock / patch.** Four clean rows only:

| Alternative considered | Why not used as designed |
|---|---|
| Three fully separate stages (scrape / OSINT-verify / honeypot-validate) | Scrape and documentary verification are the same action (fetch public text); presenting them as distinct methodologies overstates independence |
| Honeypots as the general validation method | Public honeypots observe network-layer attacks only; they cannot see deepfake KYC, voice cloning, or APP scams |
| Live bait to attract real scammers | Real engagement with criminal actors, victim-data risk, legal exposure under hackathon time — forbidden |
| Standalone unrestricted web-crawling as a demo feature | Engineering risk; judges spend little time on Identify theater. Optional **allowlisted** researcher agent on fixtures / Tavily is the demo, not Firecrawl-crawl |

### 1.3 Broken cross-reference `research_brief.md`

**Defect.** File does not exist.

**Lock / patch.** Every reference becomes [`HACKATHON_RESEARCH.md`](../HACKATHON_RESEARCH.md) Section 3 (content map). Process remains [`Updated Identify Phase.md`](../Updated%20Identify%20Phase.md) as amended by this plan.

### 1.4 Two Identify process docs

**Defect.** `Identify Phase.md` lagged `Updated Identify Phase.md` (missing `actor_type`, merchant controls, `source_urls`) and shared the same corruption.

**Lock.** [`Identify Phase.md`](../Identify%20Phase.md) is **superseded**. Do not edit it further except a one-line banner pointing here. Schema and pipeline live in Plan 01 + the patched Updated Identify Phase.

### 1.5 Stub README

**Defect.** [`README.md`](../README.md) is not a clone-and-run path (MC_PS requires a runnable documented repo).

**Lock.** Plan 03 owns the README skeleton. Until code exists, README may stay short but must link `LOCKED.md` and the four plans.

### 1.6 Unverified holdout citations

**Defect.** [`decisions.md`](../decisions.md) Part C warns SAML-D / TransXion / BAF / MoMTSim links are unverified.

**Lock.** Do **not** cite those datasets as evaluated holdouts in `TeamName.docx` until Plan 02’s verification checklist is ticked. Until then: synthetic frozen G-test (generator family B) + documented **proxy-injection** protocol. Aggregates-only calibration (never row copy) is allowed once a dataset is verified.

---

## 2. Architectural forks — winner table

| Fork | Loser reading | Winner (locked) |
|---|---|---|
| AttackSpec vs Atlas row | Two schemas | **One Pydantic `AttackSpec`** (Plan 01). “KillChain Atlas” is the store / UI name for the same rows |
| `proposed\|approved\|rejected` vs `open\|…\|solved` | Two workflows | **Single enum:** `proposed \| rejected \| rejected_unsafe \| open \| generating \| defending \| solved` |
| Tavily-live vs local-KB-only | Opposite demos | **Fixtures default** (`IDENTIFY_LIVE_SEARCH=false`) + **optional allowlisted Tavily**. No criminal-market scrape. Aligns MC_PS Identify with HACKATHON_RESEARCH optional researcher agent and ARCHITECTURE “no illicit crawl” |
| LightGBM-only vs AutoGluon-locked | Contradictory build | **FLAML/LightGBM (or single GBDT) on-path**; AutoGluon `best_quality` optional overnight **challenger**, never live AuthGate. Matches 50–300 ms feasibility and V1 “do not AutoGluon on the demo laptop” |
| GapAnalyst/nevergrad vs Cat 4 LoopGovernor | Two loops | **Both, split:** Loop A = masked Cat 4 patches vs frozen scorer; Loop G = numeric injector search; LoopGovernor = promote/reject using HoldoutVault; GapAnalyst LLM proposes which param/patch, code executes |
| Canary mode vs Canary Vault | Same word | **`canary_mode`** (documented-case pin) vs **`HoldoutVault`** (frozen eval). Rename every “Canary Vault” occurrence in later edits of ARCHITECTURE / feedback-loop |
| 8 families vs 24 techniques / 5 cats | Two diversity scores | **24 / 5 canonical.** Eight V1 families are aliases (Plan 01 § mapping) |
| AegisLoop vs named components | Two product vocabularies | **AegisLoop** product; ARCHITECTURE component names in UI and write-up |
| Linear Identify vs parallel specialists | Over-agenting risk | **Linear six-node graph** (lock 13). ARCHITECTURE §6.3 parallel specialists are **rejected for v1** |
| UPI-only vs multi-rail sim | Scope fight | **UPI-like generate;** card/BIN/3DS **named** on the map. Stretch CNP injector only after loop works |
| `title` / `failed_control` / `citations` vs `name` / `control_bypassed` / `source_urls` | Field aliases | Canonical names in Plan 01; old names are aliases in Pydantic (`validation_alias`) if needed |
| Cat 4 in public prototype vs offline-only | Dual-use | **Offline only.** Public UI may **replay** a recorded evasion chart, not expose `query_automl` |

---

## 3. Naming map (do not mix in code)

| Concept | Locked name | Forbidden / deprecated |
|---|---|---|
| Product | AegisLoop | None (working title from V1) |
| Catalog store | KillChain Atlas | “KB” informal OK in comments |
| Simulator | ShadowRail | “WorldSim” = same package |
| Live scorer | AuthGate | “the LightGBM” informal OK |
| Case / batch scorer | CaseScore | Concatenating embeddings into AuthGate |
| Policy head | Brake | Binary-only “fraud/not fraud” as the product |
| Frozen eval set | HoldoutVault | Canary Vault |
| Documented-case Generate mode | `canary_mode` | Calling HoldoutVault “canary” |
| Promotion controller | LoopGovernor | Auto-promote from G-dev ROC |
| UI | RedBlue Console | Streamlit as primary UI (backup only) |

---

## 4. Status enum — transition rules

```
proposed ──HITL approve──► open ──LoopGovernor start sim──► generating
                │                                              │
                ├──HITL reject──► rejected                    ├──train/score──► defending
                └──unsafe dual-use──► rejected_unsafe         └──HoldoutVault stable──► solved
```

- Seed YAML rows that are hand-grounded in FinCEN/arXiv start as `open` (already approved), not `proposed`.
- `name_only` rows can be `open` (they count for diversity) but **never** `generating`.
- `solved` requires Plan 02 criteria (≥2 Cat 4 rounds, HoldoutVault not worse, genuine FPR not worse, same typology credited).
- There is no `approved` token. Old docs that say `approved` mean `open`.

---

## 5. Logical gaps closed here (detail in later plans)

| Gap | Closure |
|---|---|
| `simulatable_signals` named but unspecified | Plan 01 JSON contracts per category |
| Merchant / KYB half-added | `actor_type` required; merchant controls on `control_bypassed`; v1 generate still UPI-consumer-heavy; BEC/Cat 5 is the merchant-side generate path |
| Network telemetry overclaim | `vector_class` gate in Corroborator |
| Nine feedback loops unmapped to LangGraph | Plan 02 mapping table |
| No API/UI contract | Plan 03 six-click script + endpoint list |
| Poisoning / Cat 4 public-repo scope | Offline; capability card in SECURITY.md (Plan 03) |
| `feedback-loop.md` “canary regression” | Means HoldoutVault regression |
| V1 build order vs ARCHITECTURE build order | Plan 03 single critical path |

---

## 6. What remains **not** architecture (explicitly open, not forks)

These are the only items Plan 00 does **not** lock:

1. Kaggle / GitHub **TeamName** string (Plan 03 blocker before public repo rename).
2. Verified download URLs and licenses for SAML-D / TransXion / BAF / MoMTSim (checklist in Plan 02; until then do not cite as scored holdouts).
3. Which machine, if any, runs overnight AutoGluon (optional; AuthGate does not depend on it).

Implementation may start at Plan 03 step 1 without re-litigating Identify vs Generate vs Defend.

---

## 7. Doc-patch checklist (apply in this planning layer)

- [x] This file
- [x] [`LOCKED.md`](../LOCKED.md)
- [x] Patch [`Updated Identify Phase.md`](../Updated%20Identify%20Phase.md) §1 relationship, §2.3, §3
- [x] Banner-supersede [`Identify Phase.md`](../Identify%20Phase.md) if present
- [ ] Later code phase: replace “Canary Vault” in [`ARCHITECTURE.md`](../ARCHITECTURE.md) and [`feedback-loop.md`](../feedback-loop.md) with HoldoutVault (wording only; behavior already locked here)
- [ ] Later: [`decisions.md`](../decisions.md) Part B marked LOCKED by reference to Plans 01–02 (do not fork new Part B items)

---

## 8. SSOT alignment check (why winners are not derailments)

| MC_PS / research demand | How the winner satisfies it |
|---|---|
| Breadth and depth of Identify | 24 named techniques on the map; live Identify adds rows with citations; `name_only` still counts |
| Fidelity of simulation | Deterministic ledger; calibrators as priors; APP vs stolen labels; no LLM-written amounts |
| Detection efficacy + low FP | PR-AUC, FPR@TPR, calm-down rules, APP hold vs CNP decline |
| Novelty | Closed loop + typed catalog + co-evolution (Cat 4 + Loop G) + policy actions |
| Live-payments feasibility | ≤300 ms AuthGate story; LLM off-path; HITL; synthetic-only ethics |
| One product not three side projects | Single AttackSpec consumed by population + canary_mode; Defend reads the same ledger |
| Kurshan co-evolution | Retrain on misses; mutate attacks; HoldoutVault so the loop cannot grade its own homework |
