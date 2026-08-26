# Defense architecture

How we detect, flag, and stop the frauds in this challenge.

Tied to: `MC_PS.md`, locked taxonomy `decisions.md` (Part A), lab layout `ARCHITECTURE.md`. **All loops** (ids I, R, T, M, A, F, C, H, G): `feedback-loop.md`. This file **replaces** `defense_2day_slm.md` for Defend. We are **not** using a language model to score live payments.

---

## 1. What we are building

When a payment happens we need:

1. A **risk score**.
2. A **short reason** a human can read.
3. An **action**: allow, warn, extra confirmation, hold, decline, or freeze incoming money on a mule account.

Scam payments (the victim typed the PIN) need a **different action** than stolen-account payments. We do not output only `fraud / not fraud`.

Live scoring must finish in **under ~300 ms** on the demo machine. Language models are used **after** the payment, to draft rules, or to generate fake attacks for training.

This is one piece of Identify → Generate → Defend. Misses go back to the catalog (`open`), Generate makes more of that pattern, we retrain, we only mark `solved` if a frozen test set does not get worse. That handshake is A3 in `decisions.md` and Loops I / M / A / G in `feedback-loop.md`.

---

## 2. One payment (order)

```
Incoming payment
    → numbers we are allowed to know at that moment
      (account age, neighborhood counts before this transfer, call on, …)
    → if-then rules
    → table model (LightGBM, picked by AutoML), also sees “which rules hit”
    → if the numbers look unlike training, mark “unknown”
    → one score + action
```

Slower, not on the instant-credit path:

```
Case tab → language model reads a chat or invoice → summary + second opinion
```

Shared record shape: thin envelope in `ARCHITECTURE.md` (`gff.txn.v1`). Do not put GSTIN + 3DS + VPA + chat embedding on every row.

### 2.1 LLM preprocessing: useful, but not a payment dependency

AutoML only understands structured columns. An LLM can convert a messy chat, email, or invoice narrative into a small, fixed set of fields. That is useful, but it must have two separate modes:

| Mode | When it runs | Can it change the immediate payment decision? |
|------|--------------|-----------------------------------------------|
| **Offline enrichment** | During simulation, training, and evaluation | No; it creates versioned training features |
| **Case enrichment** | After or beside the initial score, for an analyst | No; it can recommend a review or add evidence |

The initial payment decision must still work if the LLM is slow, unavailable, or returns invalid JSON. The decision uses rules, session fields, graph features, and the already-trained AutoML model. If the app already supplies `call_in_progress`, `payee_was_pasted`, or `pause_ms`, there is no reason to ask an LLM to rediscover them from text.

The LLM must output a versioned schema, not free text:

```json
{
  "schema_version": "case_signals.v1",
  "coercion_likely": 0.0,
  "beneficiary_change_claimed": false,
  "urgency_pressure": 0.0,
  "impersonation_claimed": false,
  "evidence_spans": [],
  "abstained": false
}
```

Rules for this extractor:

- validate types, ranges, and allowed fields;
- keep the extractor model and prompt version with every feature row;
- preserve `abstained` and missingness instead of converting uncertainty to zero;
- never let extracted text overwrite trusted transaction fields;
- treat the input as hostile content, not instructions;
- test the extractor on a blinded set and freeze its output before evaluating the AutoML model.

The AutoML model must be tested in three conditions: structured fields only, structured fields plus frozen LLM signals, and missing/abstained LLM signals. If performance collapses when LLM signals are absent, they do not belong on the live path.

---

## 3. Where the first rules come from

The rule file is **not** empty on day 0. AutoML and the analyser **improve** rules; they do not invent the first list.

### 3.1 The translation (this is the logic)

Every locked attack in `decisions.md` has:

- a **shape** (graph, identity time-series, session + payment, invoice fields, or “attack the scorer”),
- a **control that failed** (OTP, human check, velocity, checksum, …),
- fields we **can** compute at payment time vs fields we **cannot**.

A v0 rule is: **that shape, written as AND/OR of fields we already have**, tagged with the same economic class as the attack (scam vs stolen vs mule vs invoice), so the action table stays honest.

| If the catalog says… | v0 check is… | If we cannot see it at payment time… |
|----------------------|--------------|--------------------------------------|
| Mule: many senders, short-lived account | fan-in + unique senders + account age | — |
| Splitting under a cap | many amounts just under the cap | — |
| Hopping / dust | rail change + many tiny edges | — |
| Merchant collusion | two “merchants” cycling money, burst refunds | if we have no merchant node, **named gap** |
| Quiet then burst (farmed ID) | seasoning days + velocity jump | — |
| Takeover | new device + new payee + large amount | — |
| Coercion / live-relay **class** | call + paste + new payee | — |
| Invoice: real-looking tax ID, wrong account | beneficiary_changed + checksum pass | — |
| Deepfake video, crypto cash-out, card BIN testing | — | catalog card only, no fake rule |

Calm-down rules do **not** come from the fraud catalog. They come from the **genuine world** we simulate first (known payee, usual amount, old device). Without them, hard flags will block rent.

### 3.2 v0 starter list (write these before any training)

About 12–18 rows in `rules/` — full table also in `feedback-loop.md` §2. Must include **both** hard flags **and** calm-downs. Extra v0 rows so locked types are not invisible:

- merchant-pair cycle + refund burst (collusion), or a **named gap** if the sim has no merchant nodes yet
- many tiny outbound edges (dust), not only “just under cap”
- typing pause + paste (Cat 3 flags), even if we do not have a full chat
- invoice sequence / Benford as a **nudge** (weak; Cat 5 is beneficiary change, not amateur checksum fails)
- dispute pack: fields disagree with the original payment (case-plane rule, not auth)

### 3.3 What happens after v0 (the rules loop)

Rules get better by fixing **one of four failures**. That is the whole loop. The analyser (Loop R), tree extraction (Loop T), and catalog drafts (Loop I) are just three ways to propose a patch. The **test** is the same.

```
                    ┌─ too many genuine hits (precision)  → tighten AND, or add calm-down
  live rules +      ├─ miss a cluster AutoML already saw (recall) → new hard flag / nudge
  AutoML flags      ├─ catalog type with no rule firing (coverage) → draft from the card
                    └─ rule never fires or only uses easy-to-game fields (rot / fragile)
                                    ↓
                         propose a form (not Python)
                                    ↓
                         test on genuine holdout + frozen fakes
                                    ↓
                         promote / reject / retire
                                    ↓
                         next payment: better rules, AutoML sees new hit-bits
```

**Precision failure.** A hard flag also fires on kirana. Do not delete the fraud tell. Add a calm-down: known payee + normal amount **caps** the score. Or add one more AND that genuine traffic rarely has.

**Recall failure.** LightGBM scores the cluster high; no rule names it. Walk the trees (Loop T) or cluster the misses against similar allowed payments (Loop R). Keep a new rule only if it is quiet on genuine holdout.

**Coverage failure.** Identify added “invoice-timed impersonation.” No v0 rule. Loop I fills the **form** from the card: session flags **and** invoice beneficiary change. If the card needs a selfie model, we mark **named / case**, we do not invent a live rule.

**Rot / fragile.** Zero hits in many cycles → retire. Rule uses only fields a crook can jitter (amount, which mule they own) → keep it as a nudge and add a check on something they cannot set (account age, stale mule list).

Who may **propose**: catalog (I), trees (T), analyser on flags/misses/unknowns/case-tab (R).  
Who may **turn on**: the gate in `feedback-loop.md` §6 (genuine FPR, alert volume, no mixing scam with stolen, no generator-id cheats). Auto-draft yes. Auto-promote no, except one demo click.

Language models may fill the form or **title** a data-mined rule. They may not add conditions the numbers did not support, and they may not execute code.

### 3.4 Rule quality is learned from outcomes, not from rule-hit count

A rule is not “better” merely because it catches more simulated fraud. For every rule version we store:

`rule_id, version, technique_id, rail, economic_class, sample_count, alert_rate, precision, recall, FPR, customer-friction_rate, latency, label_lag, data_version`

Compare a candidate against the current rule set on the same frozen slices:

- **precision:** of the alerts, how many later become fraud;
- **recall:** of the relevant fraud cases it catches;
- **legitimate FPR:** how many genuine payments it affects;
- **alert rate:** whether investigators can handle the volume;
- **friction cost:** warnings, step-ups, holds, and declines separately;
- **stability:** whether it works across time, rail, amount band, and customer segment.

Promote a candidate only when it improves the intended operating point without violating the genuine-payment and alert-capacity limits. If it increases recall but creates too much friction, keep it as a case-only rule or a nudge. If it is high precision but covers very few cases, keep it as a hard flag only for that narrow pattern. This prevents the analyser from producing impressive-looking but unusable rules.

---

## 4. Three kinds of rules

| Kind | Job | Example |
|------|-----|---------|
| **Hard flag** | Sets a minimum risk. Can force a serious action. | Call + pasted payee + never paid them |
| **Nudge** | Adds a bit of risk. Never declines by itself. | Quiet for months then burst |
| **Calm-down** | Caps risk so we do not block rent / kirana | Known payee, usual amount, same phone |

Example (data, not code):

```yaml
id: call-and-paste-new-payee
kind: hard_flag
applies_to: scam_coercion
when:
  - call_in_progress: yes
  - payee_was_pasted: yes
  - payee_is_new: yes
min_score: 0.72
reason: "Possible coercion: call + new payee pasted in"
```

---

## 5. The table model

**AutoML** (FLAML in the hackathon; AutoGluon overnight if we have time) trains **LightGBM** (or random forest) on:

- account age, velocity, device/IP change, seasoning → burst
- graph on transfers **before** this payment: degree, fan-in/out, clustering in the window, burst
- optional **stale** mule prestige (batch job, not PageRank on the finished sim)
- Cat 5: checksum, arithmetic, continuity, weak Benford, `beneficiary_changed`
- bits: which **promoted** rules already hit

Train on simulated attacks + simulated genuine. Report on:

1. Frozen fakes from a **different** generator setup than train.
2. Public tables we can map (SAML-D, BAF, injected takeover proxies). If lab looks great and these look bad, **fix Generate** (Loop G), not only the detector.

**Cat 3 live path:** we do **not** put MiniLM/BERT vectors into this live model. Session flags at auth; chat text and optional embeddings on the case tab only. See `decisions.md` B2.2.

---

## 6. Language models

Use a large model for Identify (with the coverage map), Generate proposals (code still builds the ledger), case tab, and Loop I form-fill.

Do **not** use it to allow/decline the live payment.

---

## 7. “This looks new”

**IsolationForest** on the numeric vector. If the table model is calm but this says weird → extra confirmation, not silent allow.

---

## 8. Score then action

```
score = max(hard_flag_minimum, table_model_score + nudges)
then apply calm-down caps
if looks_new and score still low: at least extra confirmation
```

| Situation | Action | Do not |
|-----------|--------|--------|
| Looks fine | Allow | Randomly decline honest small payments |
| Likely **scam** (victim walked through UPI) | Warn / extra yes / hold on large **new** payee | Instant decline of a payee they always pay |
| Likely **stolen account** / card-not-present | Decline / kill session | Treat as a scam |
| Receiving account looks like a **mule** | Limit or freeze **incoming** money | Only punish the sender |
| No idea | Extra confirmation | Silent allow |

---

## 9. Locked fraud types — coverage

Covered means **Built** (simulate + score), **Case** (after the payment), **Named** (on the map, honest gap), or **Loop** (Cat 4). Missing is not allowed for Part A items.

### Group 1 — Network

| Technique | Mode | Live check |
|-----------|------|------------|
| Mule fan-in / fan-out | Built | Neighborhood counts on `G(t−)`; catch the **account** |
| Smurfing under UPI caps | Built | Many amounts just under cap |
| Chain-hopping | Built | Rail switch + burst |
| Dust / layering | Built | Many tiny edges, high out-degree |
| Synthetic merchant collusion | Built if sim has merchant nodes; else **Named** | Cycle + refund burst |
| Off-ramps / nested PSP / mule-as-a-service | Named | No live cash/crypto rail |

### Group 2 — Identity

| Technique | Mode | Live check |
|-----------|------|------------|
| Synthetic ID fields | Built | KYC inconsistency bits, new-account velocity |
| Long-horizon farming (~150d) | Built | Seasoning → burst |
| Account takeover | Built | Device change + velocity + new payee |
| Forged KYC docs | Named / Case | Form flags only, **no images** |
| Deepfake / liveness | Named / Case | Refused extra factor, channel switch, age/photo mismatch **as fields** |
| KYC-vendor / LLM supply-chain | Named | Cat 4 ∩ 2; onboarding, not UPI auth |

### Group 3 — Social / APP

Live path is **session flags**, not chat AUC.

| Technique | Mode | Live / case |
|-----------|------|-------------|
| Vishing | Built | Call-in-progress + payment |
| Push-payment coercion | Built | Call + paste + new payee |
| Live MFA-relay **as a class** | Built | Call + paste + payee change + OTP-timing **fields** — not a named kit |
| Romance / investment long-con | Built (weak) + Case | Slow-burn then burst + new payee; script on case tab |
| Phishing generic + polymorphic | Named / Case | Landing → pay session flags if we have them; **no kits** |
| Invoice-timed impersonation | Built | Cat 3 session **and** Cat 5 beneficiary change (not the same as invoice-only) |
| Voice-clone BEC | Case / Named | No audio |

### Group 4 — Attacking the detector (this **is** the loop, not model #5)

| Technique | Mode | What we do |
|-----------|------|------------|
| Evasion | Loop A | Change only fields a crook could set; ledger must still accept the payment; retrain on train pile only |
| Poisoning | Loop | Trust tags on rows (`human` / `sim_checked` / `evasion`); cap how much evasion we mix in (~15%); reject a new model if genuine false alarms jump |
| Fingerprinting | Loop | Cap score queries; do not return tree weights or SHAP to the attacker; offline only |
| Merchant / support bot injection | Named | Not in the public website |
| Agentic payment (Cat 3 ∩ 4) | Named / Built if envelope has `agent_initiated` | Catalog + optional flag |

Do not put Loop A on the public site as an open API.

### Group 5 — Documents (fields only, reuse Cat 2 engines)

| Technique | Mode | Live check |
|-----------|------|------------|
| Fake invoice / wire fields | Built | Arithmetic, lookalike payee, checksum in **code** |
| Beneficiary swap that **passes** checksum | Built | `beneficiary_changed` — the case that matters |
| Fabricated dispute / chargeback pack | Case | Fields disagree with the original payment; no fake letterheads |

### Card / 3DS / BIN / token

**Named** if Generate stays UPI-shaped. Still on the threat map.

Leakage tests: full-graph vs `G(t−)` must collapse; no `generator_id` in the live model.

---

## 10. Closed loop (PS + A3)

Miss → catalog `open` → Generate extra examples of **that** type (capped) → retrain AutoML **and** propose rules (R/T) → frozen test + public-ish tables must not get worse → `solved` only after ≥2 red-team rounds on the **same** type.

| Id | In English | In this file |
|----|------------|--------------|
| I | New catalog card → draft rule | §3.3 coverage |
| R | Flags / misses → better rules | §3.3 |
| T | Trees → readable rules | §3.3 |
| M | Miss → extra train rows (capped) | below |
| A | Red vs blue, offline | §9 Group 4 |
| F | Lab vs public vs “annoy genuine users” | below |
| C | Identify hunts empty cells | below |
| G | F says fix the **simulator** | below |
| H | Analyst overrides (later) | below |

**Loop M + poisoning:** extra rows go to **train only**, never the frozen test. Cap copies of one trick. Tag evasion rows so they cannot drown `human` / `sim_checked` data. If genuine false-alarm rate jumps, **do not** ship the new model.

**Loop F:** lab ≫ SAML-D/BAF → Loop G (amounts, mule lifetime, scam vs stolen labels). Genuine users bothered → calm-downs and thresholds, not more fake fraud.

**Loop C:** Identify sees which of the 24 have a live rule vs named gap.

**Loop H:** log (our action, their action). Later: retrain LightGBM on late labels; optionally tune the **case** prompt. We will not RLHF a tree model in four days.

---

## 11. What we report

- Catch rate **by type** (scam, mule **account**, takeover, invoice swap, chargeback-pack case).
- Catch rate at 0.1% / 0.5% / 1% genuine bother.
- Per rule: fires, right, hurt genuine.
- Cost sketch: miss vs extra confirm vs decline.
- Score latency (median and tail).
- After Loop A: frozen test still okay; query count.
- Chats: agreement on labels — **not** the headline payment number.
- Can a simple classifier tell our fakes from public data? If ~90%+, fakes are junk.
- Count of 24: Built / Case / Named / Loop — **zero Missing**.

Do not lead with accuracy on a 50/50 mix.

---

## 12. Non-negotiable correctness gates

These gates prevent the prototype from producing impressive but false results.

### Gate 1 — No future information

For a payment at time `t`, every live feature must be computed from information available before `t`. The feature builder must reject:

- the payment itself or later payments when calculating history;
- future graph edges;
- post-payment dispute, refund, or chargeback information;
- generator name, attack ID, persona ID, patch round, or train/test membership;
- case-review text that was created after the payment.

Run a leakage test by comparing the normal feature builder with one that is deliberately allowed to see the future. If the normal and future-enabled scores are nearly identical on suspiciously easy data, inspect the features before reporting results.

### Gate 2 — Separate people, components, and time

Do not randomly split related transactions into train and test. Split by time and, for graph data, by connected component or account group. A mule network must not appear partly in both train and test. Keep one frozen test set that the feedback loop can never write to.

### Gate 3 — Validate the LLM extractor

The LLM extractor is a model, not ground truth. Freeze its prompt and model version for an evaluation run. Test:

- structured payment fields without LLM signals;
- structured fields plus LLM signals;
- missing, malformed, and abstained LLM signals;
- adversarial text containing instructions aimed at the extractor.

If performance depends on the LLM being available, keep those signals off the live path. Never let extracted narrative text overwrite an amount, payee, account, or timestamp supplied by the payment system.

### Gate 4 — Do not learn from immediate outcomes

An approval is not proof that a payment was genuine, and a decline is not proof that it was fraud. Use verified or delayed labels for retraining. Record `label_source`, `label_time`, and `label_lag_hours`. During the demo, simulated labels may be used, but they must be clearly marked as simulated.

### Gate 5 — Candidate rules and models need a baseline

Every proposed rule or model is compared with the currently promoted version at the same alert budget. It must report precision, recall, legitimate false-positive rate, alert volume, friction by action, latency, and performance by rail and economic class. A candidate that catches more fraud by bothering many more genuine users does not pass.

### Gate 6 — Rollback is part of promotion

Keep the previous rule set and model artifact. Promotion writes a version, timestamp, data versions, feature versions, and approval record. Any canary regression immediately restores the previous version. The browser can request a candidate or display results; it cannot promote a rule, change a threshold, or choose a model.

### Gate 7 — Honest coverage

For each locked technique, record exactly one status: `built`, `case_only`, `offline_loop`, or `named_gap`. A named gap must state which missing signal or rail prevents live detection. Never count a generic “fraud” score as proof that every technique was detected.

The prototype is ready to claim results only when all seven gates have passed. If a gate fails, show the failure in the UI and label the result exploratory.

---

## 13. What we submit (PS artifacts)

| Artifact | Defend must show |
|----------|------------------|
| Public GitHub | Rules, features, AutoML train, eval, loop scripts — plus Identify + Generate in the same repo |
| `.docx` | Coverage table §9, metrics §11, one before/after loop, live-payment limits |
| Web UI | Map of 24 types with status; score + reason + action; draft rule that **fails** genuine test; one retrain; **offline** Cat 4 chart — not a public attack API |

---

## 14. Four-day build

- **Day 1:** envelope, features, v0 rules (hard flags **and** calm-downs), actions, three canned payments.
- **Day 2:** graph + identity + Cat 5 fields; train LightGBM; Loop T → a few readable rules.
- **Day 3:** session flags + sample chats; one catalog `open` → extra fakes (Loop M); one **offline** Loop A round; Loop R on one miss group; Loop F chart; one draft that **fails** genuine FPR.
- **Day 4:** UI beats in §12.

Write-up only: full bank catalog, overnight AutoGluon, real issuer logs, production overrides.

---

## 15. Do not build

- Graph neural net on the live path.
- MiniLM/BERT inside the live scorer.
- Eight AutoGluon artifacts; language model as live scorer.
- Crime-market scrape; Loop A as a public web toy.
- Promote every draft; one action policy for scams and stolen accounts.

---

## 16. How to say this to judges

- First rules are the locked catalog, turned into checks on fields we actually have, plus calm-downs from genuine traffic.
- Rules improve when they are too loud, too quiet, missing a catalog type, or easy to game — propose, test, then turn on.
- Live detector is a table model. Language models write attacks, draft rule **forms**, and help analysts.
- Cat 4 is retrain-under-attack, with caps and a frozen test, not a fifth detector.
- If the rail cannot see it, we say **Named**.

---

## 17. Pointers

- `MC_PS.md`, `decisions.md`, `ARCHITECTURE.md`, `feedback-loop.md`
- Trees → readable rules: Feedzai RIFF; skope-rules
- FinCEN deepfake alert: **fields**, not how-tos

We describe attack **types**. We do not publish kits or exploit steps.
