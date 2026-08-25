# Feedback loops

One place that lists **where the first rules come from**, the live scoring order (**rules → AutoML → language model**), and **every loop** that updates those pieces.

Defend details: `defense_architecture.md`. Locked categories: `decisions.md`. Lab layout: `ARCHITECTURE.md`.

---

## 1. Live order (one payment)

```
1. Rules          fast if-then checks  →  hard flags, nudges, calm-downs, reasons
2. AutoML         LightGBM (etc.)      →  risk score, using the numbers + “which rules hit”
3. Language model case tab only        →  read chat / invoice, explain, second opinion
```

The language model does **not** sit between 1 and 2 on the live payment. It can still **write draft rules** via Loop I / Loop R (sections 3 and 5).

---

## 2. Where the rule base starts (it is not empty)

If you wait for AutoML and the analyser to invent everything, day 1 has nothing to demo and genuine customers have no calm-downs.

**v0 rules** are written **before** any training run. They come from the attack catalog we already locked, turned into checks on fields we actually compute.

| Source of v0 | What we put in the file |
|--------------|-------------------------|
| `decisions.md` five groups | One or more rules per group we can see at payment time |
| Knowledge base attack cards | Conditions listed on the card (call + new payee, fan-in, device change, …) |
| Regulator-style **tells** (as fields, not how-tos) | e.g. refused extra factor, switched channel mid-check, age vs photo mismatch **as a form field** |
| Payments common sense | Calm-downs: known payee, normal amount, old device |

**v0 starter set (about 12–15 rules)** — this is the first `rules/` file:

| Rule | Kind | Why it exists on day 0 |
|------|------|------------------------|
| New payee + large amount + new/changed device | hard flag | stolen-account / takeover shape |
| Call on + payee pasted + payee not in history | hard flag | coercion / “relay” **class** |
| Many different senders into one new account in a short window | hard flag | mule receiving |
| Many payments just under a product cap | hard flag | splitting |
| Rail switch (UPI then IMPS-like hop) + burst | nudge | hopping |
| Quiet for a long time then sudden burst | nudge | farmed identity waking up |
| Invoice tax ID checks out **but** beneficiary account changed | hard flag | the document case that matters |
| Amount vs invoice total mismatch | nudge | sloppy fake invoice |
| Many tiny outbound edges | nudge | dust / layering |
| Merchant-pair cycle + refund burst | hard flag or **named gap** | collusion — only if the sim has merchant nodes |
| Long pause + paste on payee | nudge | Cat 3 session (even without full chat) |
| Known payee + amount in their usual band + same device | **calm-down** | do not block rent / kirana |
| Old account + no device change + payee used many times | **calm-down** | genuine baseline |

Calm-downs come from the **genuine** world, not from the fraud catalog.

Attacks we **cannot** see at payment time (deepfake video, live crypto cash-out, card-network BIN testing) do **not** get a fake v0 rule. They get a catalog card: “named only” or “case tab only.”

How rules get **better** after v0 (too loud / too quiet / catalog hole / easy to game): `defense_architecture.md` §3.3. Same promote gate: section 6 below.

After v0, **every new rule** is a draft until it is tested on genuine-looking traffic (section 6).

---

## 3. The analyser agent (rules that get better from flags)

This is the extra loop you asked for. It sits **after** scoring, not on the hot path.

```
Rules and/or AutoML (and case-tab LLM, if any) flag payments
        ↓
Analyser agent
  - pull flagged rows + misses + “looks unknown”
  - group similar ones
  - compare each group to similar payments we allowed
  - write a tighter rule form (fields we already have)
  - maybe rename / link to an attack type
        ↓
Test on genuine holdout + held-out fakes
        ↓
Human (or demo auto-approve) turns it on
        ↓
Next payments hit a better rule list  →  AutoML also sees new “rule hit” bits
```

**Who flags:** a hard rule, a high AutoML score, “unknown,” or a case-tab language model that said “this invoice looks swapped.” All of those go into the **same** inbox for the analyser.

**What the analyser is allowed to output:** the same rule form as v0 (conditions + kind + reason). Not Python. Not new magic fields.

**What it is for — four failures only:**

1. **Too loud (precision):** hard flag hits kirana → extra AND, or a calm-down. Do not delete the fraud tell.
2. **Too quiet (recall):** AutoML catches a group, no rule names it → new hard flag / nudge from cluster vs similar allowed payments.
3. **Hole in the catalog:** attack card exists, no rule fires on those sims → fill the same form as v0 from the card (Loop I may do this first).
4. **Rot / fragile:** never fires → retire. Only uses fields a crook can jitter → keep as nudge, add a check they cannot set (account age, stale mule list).

AutoML keeps fuzzy patterns. The analyser turns **stable** patterns into rules so the next payment is cheaper, faster, and explainable. It may not output Python or new magic fields.

---

## 4. LLM preprocessing loop (messy input → tested columns)

The language model can turn a chat, email, or invoice narrative into a small fixed set of fields. It does not make an unreviewed payment decision.

```
chat / email / invoice narrative
        ↓
LLM extractor with fixed JSON schema
        ↓
type/range checks + prompt-injection isolation
        ↓
versioned fields + abstain flag + evidence spans
        ↓
compare AutoML with/without these fields
        ↓
keep as optional live evidence, or keep case-only
```

The extractor must:

1. Output only known fields such as `urgency_pressure`, `impersonation_claimed`, and `beneficiary_change_claimed`.
2. Preserve uncertainty as `abstained` or missing, never as a false zero.
3. Never overwrite trusted transaction fields with text from the LLM.
4. Store the model, prompt, and schema versions with every extracted row.
5. Be tested with the fields present, missing, and invalid. If the model fails without the LLM, the fields remain case-only.

Use this heavily for offline training and case review. Do not make a slow or unavailable extractor a single point of failure for a live payment.

---

## 5. All loops (tracker)

Use these ids in tickets, UI, and the write-up.

### Loop I — Catalog ↔ defense coverage

| | |
|--|--|
| **Trigger** | New attack card, or a card still marked “open” |
| **Does** | Show Identify what we already catch. Draft a v0-style rule from the card (language model fills the form). |
| **Writes** | Knowledge base status; a **draft** rule |
| **Must not** | Invent a live rule for something we cannot measure at payment time |

### Loop R — Analyser: flags → better rules

| | |
|--|--|
| **Trigger** | Batch of flags / misses / unknowns (from rules, AutoML, or case LLM) |
| **Does** | Find groups, write tighter or calmer rules |
| **Writes** | Draft rules |
| **Must not** | Turn drafts on without the test in section 6; mix scam-victim and stolen-account in one rule |

### Loop T — Trees → readable rules

| | |
|--|--|
| **Trigger** | AutoML just finished a training run |
| **Does** | Turn short tree paths into if-then rules; keep only those that stay quiet on genuine holdout |
| **Writes** | Draft rules (no language model required) |
| **Must not** | Use “which simulator made this row” as a condition |

### Loop M — Misses → more training data

| | |
|--|--|
| **Trigger** | We missed a fraud, or the red-team payment still looked valid and slipped through |
| **Does** | Add a **capped** extra set of those patterns to the **training** pile; retrain AutoML; also feed Loop R |
| **Writes** | New model file; maybe drafts from R/T |
| **Must not** | Put those rows into the frozen test set we report; flood training with copies of one trick |

### Loop A — Red team vs blue team (category 4)

| | |
|--|--|
| **Trigger** | A frozen copy of the current scorer exists |
| **Does** | Change only fields a crook could change; ask the scorer; keep only payments our ledger rules still accept |
| **Writes** | Evasion examples → Loop M (train only); query log |
| **Must not** | Live website API; tell the attacker the tree weights; unlimited score queries |

### Loop F — Lab vs public data vs “would this annoy people”

| | |
|--|--|
| **Trigger** | After train, or after a rule batch |
| **Does** | Compare: our fakes vs frozen other fakes vs SAML-D/BAF-style public tables vs action mix on genuine-shaped traffic |
| **Writes** | If lab ≫ public: ticket to **Generate** (fix amounts, mule lifetime, scam vs stolen labels). If too many genuine hurts: Loop R calm-downs + threshold change. |
| **Must not** | Only retrain the detector when the simulator is the thing that is wrong |

### Loop C — Identify hunts holes

| | |
|--|--|
| **Trigger** | Coverage map updated (which cards have a live rule, which are named-only) |
| **Does** | Ask Identify to propose attacks in empty cells (lifecycle × rail × scam vs stolen vs mule) |
| **Writes** | New catalog cards → Loop I |
| **Must not** | Five clones of the same card-not-present idea |

### Loop H — Human overrides (after a real deployment)

| | |
|--|--|
| **Trigger** | Analyst or customer disagrees with our action |
| **Does** | Log (payment, our action, their action). Later: retrain AutoML on late labels; optionally tune the **case** language-model prompt. |
| **Writes** | Preference / override log |
| **Must not** | Claim we RLHF’d LightGBM in four days; treat overrides as instant ground truth (disputes are late) |

### Loop G — Generate uses defender feedback

| | |
|--|--|
| **Trigger** | Loop F gaps, or Loop A “too easy / too hard” |
| **Does** | Change how fakes are built (still: model proposes, **code** builds, **code** checks) |
| **Writes** | New simulated ledger batches |
| **Must not** | Copy real customer rows; copy public datasets row-for-row |

---

## 6. Shared gate (every new rule, every new model)

Before a draft rule or a new LightGBM becomes “live”:

1. Run on a **genuine** holdout (our benign world + public genuine-shaped data if we have it).
2. If it bothers too many genuine payments → reject or convert to a nudge / add a calm-down.
3. Run on the **frozen** fake test set (different generator settings than train).
4. A human clicks promote (demo may auto-click once).
5. Version the file. Keep the old one so we can roll back.

“Solved” on an attack card means: at least two red-team rounds, frozen test not worse, genuine false alarms not worse, and we credit the **same** attack type (a mule trick is not a chat-scam win).

For every candidate rule or model, also compare against the current version at the same alert budget. Record precision, recall, genuine false-positive rate, alert volume, friction by action, latency, and performance by rail. More alerts alone do not mean improvement.

### Conditions that apply to every loop

- **No future data:** live features use only events before the payment; no post-payment labels, refunds, disputes, future graph edges, generator metadata, or test-set markers.
- **No contaminated test:** generated evasions and analyser examples enter training only. The frozen test set is physically separate and never appended to.
- **No related-row leakage:** split by time and account/component, not just random rows.
- **Delayed labels:** an approval is not a genuine label. Store label source and label time; use verified or delayed outcomes for retraining.
- **Safe LLM output:** extractor and rule-drafter output is schema-checked data. It cannot execute code, alter trusted transaction fields, promote itself, or change thresholds.
- **Rollback:** each promotion records model/rule/feature versions and preserves the previous version. A canary regression restores it.
- **Browser is not trusted:** the UI can request a draft, run a shadow test, and display a candidate. Promotion and threshold changes happen server-side.
- **Rule quality is not alert count:** compare precision, recall, false-positive rate, alert capacity, customer friction, latency, and rail/class stability against the current version.

---

## 7. What talks to what (picture)

```
                    ┌──────────────┐
                    │ Attack catalog│◄──────── Loop C (holes)
                    └──────┬───────┘
                           │ Loop I
                           ▼
 v0 rules ──► live rules ──► AutoML score ──► action
      ▲            ▲    │         │
      │            │    │         │
      │     Loop T ┘    │         │
      │     Loop R ◄────┴─────────┘  flags, misses, unknown
      │            ▲
      │            │ Loop M + Loop A (harder fakes, capped)
      │            │
      └──── Loop F may also say: fix Generate (Loop G)
                                 or add calm-downs (Loop R)

 Case language model ──► flags into Loop R only (not live allow/decline)
 Loop H (later) ──► AutoML labels + case-prompt tweaks
```

---

## 8. Four-day: which loops are real vs sketched

| Must work in the demo | Can be one scripted example | Write-up only |
|------------------------|----------------------------|---------------|
| v0 rules live | Loop R: one batch of flags → one new draft → pass or fail genuine test | Loop H at production scale |
| AutoML trained | Loop T: trees → a few readable rules | |
| Loop M once (miss → retrain → better catch) | Loop I: add one catalog card → draft rule | |
| Loop F chart (lab vs public-ish) | Loop A offline, not on the public site | |
| Coverage map for Loop C | | |
| One fixed-schema LLM extractor on a case example | Missing-signal comparison (with/without extracted fields) | Continuous production extractor retraining |

---

## 9. Short answers

**Where do rules start?** From the locked catalog and a small v0 file (section 2), including calm-downs. Not from a blank YAML waiting for AutoML.

**Rules → AutoML → LLM?** Yes for **scoring a payment**. LLM is case/explain/drafts.

**Analyser as its own loop?** Yes: **Loop R**. Flags from rules **or** AutoML **or** case LLM → groups → better rules → test → live rules → better AutoML inputs next time.

**LLM preprocessing?** Yes for offline enrichment and case review. It outputs versioned, validated fields. It is optional for the live decision and must not become a single point of failure.
