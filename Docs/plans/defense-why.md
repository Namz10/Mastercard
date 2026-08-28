# Why we defend this way

**AegisLoop design rationale** — companion to the Defend architecture SSOT (`defense-architecture.md`). This file is the argument, not the spec. It does not reopen locked choices. It explains them so a judge or a teammate can see *why* the taper looks like Mastercard, not like unfinished homework.

**Audience:** GFF 2026 judges and the team.  
**Problem statement:** [`MC_PS.md`](../../MC_PS.md) — Identify, Generate, Defend as one closed red-team / blue-team system. Detect, flag, and mitigate. Score diversity, fidelity, detection efficacy, novelty, and live-payments feasibility.  
**Status vs architecture SSOT:** locked decisions below are treated as given. Isolation Forest is **GO-with-modifications** until the architecture SSOT stamps the exact wiring; the argument in §10 is written so that stamp cannot quietly turn IF into a family detector or a Cat-4 claim.

---

## 1. The problem in one page

Generative AI made payment fraud cheaper to invent, cheaper to scale, and easier to disguise as a normal person tapping “pay.” The Mastercard Innovation Challenge does not ask for a better static rule pack, and it does not ask for a standalone classifier on a public Kaggle table. It asks for **one system that owns the full cycle**:

1. **Identify** — research and map emerging GenAI-powered payment fraud. Breadth *and* depth. Grounded in how rails actually work, not buzzword lists.
2. **Generate** — simulate those attacks at scale with enough fidelity that a defense can train and be stress-tested on them.
3. **Defend** — detect, **flag**, and **mitigate** the generated attacks, with high detection on fraud and low false positives on genuine payments.

“Detect” is a score. “Flag” is a reason a human can read. “Mitigate” is an action that is allowed to differ by economic class. A victim who was coerced into authorizing a UPI push (authorized push payment, APP) is not the same problem as a stolen session (account takeover, ATO), which is not the same problem as a mule account soaking inbound money. Treating all three as `fraud / not fraud` → `decline` is how you either punish the victim or let the mule keep the float.

The environment we actually have is a **lab**, not live NPCI. A quiet UPI-shaped world is generated first; four injectors plant five fraud families; features are computed only from the past (`G(t−)`); a champion scores the row; YAML rules name the tell; a Brake table maps family + hits + score to an action. When blue misses a family, red is allowed to add more of that family to **train**, the recipe is refit, and a **new world seed** photographs whether anything actually transferred. That is the product. A bigger AutoML bake-off on the same leaked table is not.

What the problem statement will punish, if we are sloppy:

- Claiming 24 live detectors because the census has 24 names.
- Quoting a metric computed on the same fold we used to mine rules, attach specialists, or harvest misses.
- Selling APP accuracy that is really “Generate stamped four flags true on every APP row.”
- One decline button for APP, ATO, and mule.
- Novelty as “we ran AutoGluon” or “we trained a GNN.”

What it will reward, if we are honest: a threat map with named gaps, a simulator whose features are causal, a decision stack an issuer could actually run, and a loop you can click.

---

## 2. What winning looks like

Judges score five axes. Winning is **mapping each axis to a claim we can defend when someone opens the repo**.

| Axis | Problem-statement wording | What we put on the table | What we refuse to claim |
|------|---------------------------|--------------------------|-------------------------|
| **Diversity of attacks identified** | Breadth and depth of GenAI payment fraud | Census T01–T24 (seed catalog covers all technique ids) plus a coverage map that marks `built` / `case` / `offline_loop` / `named_gap` | “We detect all 24.” Diversity is the Atlas, not 24 scorers. |
| **Fidelity of attacks in simulation** | Realistic distributions, behaviours, edge cases | Quiet Poisson world + four injectors + PSI vs **this run’s priors**; causal `G(t−)` features; APP flags only on APP rows | “This is live UPI.” PSI is sampler QA. Lab fraud rate 0.5–3.5% is oversample, not India prevalence. |
| **Detection efficacy** | Precision, recall, F1/AUC; low FP on genuine | Lead with **average precision by family**, TPR at genuine FPR 0.1% / 0.5% / 1%, `n_pos` on every cell, APP ablation with vs without session flags, laptop AuthGate p50/p99 | Accuracy; ROC-AUC as headline; F1 shopping; hiding APP death without flags; quoting CI-sized `n=20` as the walkthrough number |
| **Novelty** | Overall solution | Closed loop: miss → Generate extra on train → refit frozen recipe → photograph on a new seed. Brake typology. HITL rules. Honest taper. | AutoGluon on the path, five live models, GNN, Featuretools DFS, CaseScore LLM at auth |
| **Real-world feasibility** | Live payments | Rules + one histogram GBDT + Brake; LLM **off** the auth path; HITL promote; synthetic-only ethics; measured in-process latency | Mastercard issuer SLA 50–300 ms; “we beat production”; auto-promote rules; auto-`solved` catalog |

Detect / flag / mitigate maps to the live order: **rules flag**, **HGB scores**, **Brake mitigates** (`allow | notify | step_up | hold | decline | mule_credit_restrict | case`). APP may hold or notify; it does not silent-decline. ATO may decline. Mule inbound is a **credit restrict on the payee**, not a slap on the last sender.

A submission that aces one axis and lies on another loses. The walkthrough should be able to say, in one breath: *we named 24, we simulate five families through four engines, we score with one model and nine rules, we show the loop, and we show the gaps.*

---

## 3. Two diagrams

### 3.1 The lab loop (red team / blue team)

```
  IDENTIFY                         GENERATE                         DEFEND
  (census, HITL)                   (ShadowRail)                     (no graph)

  Scout → Curator →                quiet world (Poisson,            9 YAML rules
  Extractor → Grounder →           personas, priors)                  │
  TierScorer → Corroborator →           │                             ▼
  Librarian → HITL approve              │ four injectors         one multiclass HGB
       │                                │  graph_mule                 │
       │ Atlas cards                    │  identity_trajectory        ▼
       │ generate_mode:                 │  app_session              Brake
       │   generate | name_only         │  doc_beneficiary       action + reasons
       │                                │                             │
       │  default mix does NOT          ▼                             │
       │  consume Atlas recipes    FeatureComputer G(t−)              │
       │  unless a vector_id is    train.parquet  seed 42             │
       │  passed                   G-test.parquet seed 43  <──────────┤ photograph
       │                                ▲                             │
       │                                │ extras, train only          │
       └────── coverage / Loop I        │                             │
              drafts (HITL)        Loop M: miss family ───────────────┘
                                   (Loop T MUST: G-dev trees →
                                    draft rules, same HITL gate; not a substitute for M)
```

Loop **M** is the demonstrated red/blue data loop. Loop **T** is the mandatory readable-rule HITL loop (trees → drafts → human promote). They are **not** exclusive-or: T does not replace M, and M does not make rules unnecessary. Loops that are named in older nine-loop prose and not on this diagram are roadmap, not the demo claim.

### 3.2 One authorization-time decision

```
  Payment arrives at time t
           │
           ▼
  Snapshot features from G(t−) only
  (account age, 1h fan-in/out, unique payers 1h,
   new payee, new device, amount vs 30d mean,
   APP session fields if the envelope has them,
   invoice envelope booleans if the envelope has them)
           │
           ▼
  Evaluate 9 live YAML rules
  (hard_flag / nudge / calm_down; applies_to stays typed)
           │
           ▼
  One HistGradientBoostingClassifier
  y = label_family
  (normal | mule | identity_burst | ato | app_fraud | invoice_fraud)
  P(family)  +  rule-hit bits on X
           │
           ├─ optional: Isolation Forest on a STAMP-FREE numeric subset
           │    if champion is calm but row is weird → notify, not a new family
           │
           ▼
  Brake (locked typology)
           │
           ├── mule            → mule_credit_restrict
           ├── calm_down, no hard_flag → allow   (kirana / rent)
           ├── APP             → hold or notify  (never silent decline)
           ├── invoice / BEC   → hold or case
           ├── ATO             → decline or step_up
           └── identity_burst  → step_up or notify
           │
           ▼
  Action + reason codes
  (LLM may polish analyst text AFTER this. Never between rules and HGB.)
```

---

## 4. The funnel 24 → 4 → 1, and why that is honest

A Mastercard-shaped lab does not ship one detector per named technique. It ships:

| Layer | Count | Job |
|-------|-------|-----|
| **Identify census** | **24** technique ids (seed catalog has 29 rows; some techniques have more than one card) | Exhaustive map. Every cell is `built`, `case`, `offline`, or a **named gap**. Missing is not allowed. |
| **Generate engines** | **4** injectors | The rails we can actually replay: graph mule, identity trajectory, APP session, document/beneficiary. |
| **Economic families** | **5** fraud + `normal` | What Brake and the champion speak: `mule`, `identity_burst`, `ato`, `app_fraud`, `invoice_fraud`. |
| **Defend live** | **1** multiclass HGB + **9** YAML rules | Authorization-time stack an issuer could run on a laptop in-process. |

That taper is the product, not a concession.

**Why 24 at Identify.** The problem statement asks for breadth and depth. A FIU-style typology catalog is how a payments company thinks: name the kill-chain, the rail, the failed control, and whether payment-time fields even exist. If we only listed the five families we can inject, a judge would correctly say we did not Identify — we started from the simulator and worked backwards.

**Why not 24 engines.** Several techniques are the same economic motion with a different story (vishing vs impersonation vs MFA-relay class all ride `app_session`). Several cannot be seen on a UPI-shaped auth envelope at all: merchant collusion needs a merchant-settlement graph we do not have; BIN testing needs card-auth events; KYC-vendor supply-chain and model poisoning are not payment-time detectors. Building fake engines so the count matches the census would be the dishonest move. `name_only` and `named_gap` are the honest ones.

**Why four engines / five families.** Four mechanisms cover the five economic classes Brake must distinguish. Identity trajectory plus a device-shift card becomes `ato`; without the shift it is `identity_burst`. KYC-flavoured cards that we do generate still collapse to identity families at payment time — that is not a KYC-vendor detector, and we should not call it one.

**Why one model.** See §5. The short version: family AP is a **metric** on one head, not five pickled specialists. Shared graph and velocity structure is real. APP and invoice “specialists” that split on Generate’s stamps are near-labels.

**Mastercard-shaped, not incomplete homework.** An issuer threat team maintains a long atlas. An issuer lab simulates a handful of economic classes on the rails they have. An issuer auth service runs **one** fast model, a small promoted rule file, and a policy table that is not “decline everything spicy.” Gaps are written down. Retrain is a loop with a frozen test photograph, not a vibe. That is what this funnel copies. Pretending we have 24 live models would copy a student poster, not a payments company.

---

## 5. Why one champion

We considered five family HGBs, and we considered small decision-tree specialists for APP and invoice. We rejected both as the live architecture.

**Shared strength.** Fan-in, unique counterparties, seasoning then burst, new device, new payee, amount vs personal 30-day mean — these are not five unrelated tables. A multiclass histogram GBDT is allowed to share splits across families. Five models fragment sample size (ATO is a thin mix share by design) and force a fusion layer that silently steals probability mass from `normal` unless you renormalize carefully. We would spend the contest debugging softmax splice instead of the loop.

**Brake needs a family, not five independent yes/no scores.** Brake’s job is typology: APP hold ≠ ATO decline ≠ mule credit restrict. One head that outputs `pred_label_family` plus a score is the input that table expects. Five binary models disagree (APP 0.7 and ATO 0.6 on the same row). Then you invent a referee. The referee is a sixth model we did not want.

**APP and invoice stamps are near-labels.** The APP injector writes session flags **by construction** on APP rows only (`call_active_flag`, `copy_paste_payee_flag`, `pause_ms`, `urgency_pressure`). Genuine rows get empty flags. Invoice injection writes envelope booleans (`beneficiary_changed`, checksum-ok, lookalike domain) on invoice rows. A tiny tree that splits on those flags will look brilliant and teach nothing about payment behaviour. Family AP computed from a specialist that only saw stamps is not detection efficacy; it is a round-trip test of the injector. The honest APP number is the **ablation**: with flags vs without. If AP dies without flags, we document it. We do not glue flags onto genuine traffic to save the chart.

**What we still allow, later, if evidence demands it.** At most **one** one-vs-rest adapter, and only if a family is dead on a nested confirmation set — not on the photographed G-test, and not because stamps made a toy tree look good. Default remains zero specialists, honestly. Family AP from the single head is the metric either way.

**What “champion” means.** `HistGradientBoostingClassifier`, `y = label_family`. Optuna may search a small box on **inner validation only**, then we freeze `models/features.json` and refit the outer train. That freeze **is** AutoML for this contest. AutoGluon may exist as an overnight write-up challenger. It is not on the path, not in the demo scorer, and not the novelty story.

---

## 6. Why rules still exist

If the model is good, why YAML?

**Explainability at authorization.** A reason code like `call-and-paste-new-payee` is a sentence an analyst and a judge can check against the row. A 0.81 APP probability is not. The problem statement asks to **flag**, not only to score. Rule-hit bits also go onto `X` so the model can use “the floor already fired” without replacing the floor.

**APP is not ATO.** Rules carry `applies_to`. Mixing scam-coercion and stolen-session into one predicate would teach Brake the wrong action. YAML makes that typing visible. A single binary fraud score cannot.

**Calm-down kirana.** Hard flags without a genuine-world counterweight will hold rent and the neighbourhood grocer. Calm-down rules (known payee, usual amount, old device) are allowed to **allow** even when the model is noisy, as long as no hard_flag also hit. That is not a model trick; it is policy. It exists because false positives on genuine UPI are how you lose feasibility, not how you lose a Kaggle medal.

**Coverage you can audit.** Nine live rules are a floor we can list. Loop I can draft from a catalog card; Loop T drafts from short trees on G-dev misses. Drafts stay drafts until a human promote, after a genuine-FPR / alert-volume gate. Auto-promote is rejected because a lab that promotes its own synthetic tells will look perfect until the first calm hour of real traffic.

**Rules cannot see what is not on the row.** Invoice predicates need invoice envelope fields on the auth snapshot, not buried in a denylisted payload. Graph rules that meant “many different senders” need unique in-degree, not event-count fan-in. Those are feature-contract choices (§9), not a reason to delete YAML.

---

## 7. Why the closed loop is the moat

Novelty, for this challenge, is not a fancier estimator. Every serious team can fit a GBDT. The problem statement’s own sentence is the moat:

> The best solutions turn their own simulated attacks into the training ground for a stronger defense.

That is Loop **M**: find a miss **family** (with support), ask Generate for a capped extra mix of that family, append to **train only**, refit the **frozen** recipe, photograph on a **new** `world_seed`. Win conditions are boring on purpose: family AP on G-test does not collapse, genuine FPR does not jump, extras never appear on the photographed ledger, catalog `solved` stays false unless a human later meets a strict bar we are not auto-writing.

**Not AutoML.** Optuna freeze is hygiene (§11). AutoGluon-on-path is a bake-off. Bake-offs do not answer “what happens when red changes the mix.”

**Not GNN.** Graph Neural Nets at payment time want a neighborhood that is expensive to fetch, awkward to keep causal, and slow relative to a histogram GBDT on windowed degrees. Literature that matters for AML (trees with graph features vs GNN) already says the quality gap is often small and the latency gap is not. We take windowed `G(t−)` counts — including unique counterparties — and stay on CPU milliseconds. Dynamism is **the graph at t− plus the loop**, not a deeper message-passing stack.

**Not specialists.** Five models and APP/invoice DTs optimize the wrong leaderboard: injector stamps and fragmented heads. They do not create a flywheel.

**Loop M and Loop T together, not XOR.** M changes the **data** the champion sees. T proposes **readable** drafts from trees for the HITL inbox. One is red-team volume; the other is blue-team language. Using T as a substitute for M would freeze the world and only rewrite rules. Using M as a substitute for rules would hide typology and kirana. We demo both. We do not claim nine production loops because four HTTP-shaped loops exist (I, C, M, T).

**Identify stays in the loop as census, not as auto-generate.** Coverage holes and Loop I drafts are how new names enter. Miss clusters do not auto-spawn AttackSpecs. That is how you keep the atlas from laundering simulator artifacts into “novel OSINT.”

---

## 8. Why G-test / nested protocol (what a judge would catch)

A competent judge will look for the oldest fraud-ML sin: **the number on the slide was also the coach.**

| Slice | Role | May it coach? |
|-------|------|----------------|
| Inner fit (early train calendar) | Fit trees | Yes |
| Inner val (last chunk of **train** calendar) | Optuna, early stopping, operating-point / genuine-FPR floor | Yes, and **only** here for those jobs |
| Same-run outer eval (last 1/3 of train world + entity holdout) | Diagnostic | Log it. Do not lead the slide. |
| **G-test** (new `world_seed`, same scale and engines) | **Photographer** | **No.** No HPO, no threshold search, no rule mining, no specialist attach, no FN harvest for a second Loop M you then quote on the same G-test. |
| Optional G-dev (third seed) | Harvest / confirmation | Yes, if we keep 43 untouched as headline |

**G-test is photographer, not coach.** It takes one picture of transfer: same FeatureComputer, different random world. If AP falls off a cliff, we memorized entities or a seed-specific mule layout. If we then harvest misses from that picture, generate extras, and photograph again on the same ledger, we have a selfie, not a test.

**Nested, not shuffle.** Random `train_test_split` leaks mule payees and future edges into train. We cut time (first 2/3 of **this run’s** calendar) and hold out mule-like entity ids. Inner val is carved from train so Optuna cannot see G-test parquet. After freeze, we **refit full outer train**. Scoring an inner-fit-only model against a full-train baseline is an unfair comparison we refuse.

**Loop M isolation.** Extras get train-calendar timestamps and ids that must be disjoint from G-test. G-test seed ≠ train seed. That is the entire credibility of the before/after chart.

**What a judge would catch, because we already listed it for ourselves:**

- Headline metrics from CI `n=20` or from the same-run eval fold.
- APP AP without the ablation.
- Family AP without `n_pos` (NaN dressed as a win).
- Invoice AP while envelope flags never reached `X`.
- “Loop M improved AP” after mining the photographed seed.
- Coverage `live_rule` sold as fire-rate on techniques that share one injector.
- PSI vs own priors sold as live UPI.
- Five models in the walkthrough while `champion.joblib` is one file.

The nested protocol is how we make those catches fail in *our* CI instead of on stage.

---

## 9. Why these features (and why not Featuretools)

Payment-time features have one job: **what could an issuer know before this credit posts?** That is `G(t−)`: running account state, deques of recent edges, envelope fields on **this** payment. One pass, O(n) updates, not a pairwise explosion.

**Causal windows.** `fan_in_1h` / `fan_out_1h` are past-hour event counts on payee / payer. Account age, payee history, new device, amount vs 30-day personal mean — all from state that existed before the snapshot. If training used the finished graph, a mule’s *future* inbound would leak into the first edge. A judge who recomputes `G(t−)` vs full-graph features would see AUC diverge. We would rather that test be boring.

**Unique degree.** Event-count fan-in treats ten payments from one sender like ten senders. Mule funnels are many **counterparties**. Unique payers in the last hour on the payee is the graph-lite tell that matches the typology without standing up a GNN. Volume fan-in still matters (smurf/dust). They are different columns. Cloning `burst_velocity` from `fan_out_1h` is not a feature; it is a duplicate we do not defend as signal.

**Invoice envelope.** Beneficiary-changed, GSTIN checksum-ok, lookalike-domain flag are **on the payment at t−** the way APP session flags are — if we copy them through feature replay onto the auth snapshot. They are not the GSTIN string (identity leak) and not the raw payload (denylist). Amateur checksum-fail invoices are the uninteresting case; the interesting BEC case **passes** checksum with the wrong account. Training on amateur fails would teach the wrong lesson.

**APP flags are real-shaped and lab-stamped.** Call-active, paste-payee, pause, urgency are the class of SDK / session signals APP detection actually needs. Generate sets them **true on APP rows by construction** and empty on genuine. That is honest about the *channel* and dangerous about the *metric*. Hence ablation, and hence no APP-flag products as “moat features.”

**Optional gated interactions.** A few products of already-allowlisted numerics (`fan_in_1h * account_age_days`) may exist if inner-val says they lift. They are not an Auto-FE search.

**Why Ticket-1-shaped features beat pairwise Auto-FE as a “moat.”** Deep Feature Synthesis and Featuretools-style pairwise aggregations will happily invent `MEAN(amount WHERE payee)` using tables that include the future, or explode width until every injector stamp has a cousin. The contest novelty is not “we enumerated aggregations.” It is that **dynamism lives in `G(t−)` plus Loop M**, while the columns stay few, named, causal, and checkable. Unique in-degree and invoice envelope are *the* graph and document tells the engines exist to produce. Auto-FE that rediscovers `copy_paste_payee_flag` under another name is a costume.

**Still forbidden on `X`:** generator ids, technique ids, world seed, transcripts, GSTIN string, `is_authorized_push` as a cheat, onboarding liveness copied onto every payment, embeddings, anything in the train denylist.

---

## 10. Isolation Forest: for, against, and the honest modification

Older Defend prose proposed an Isolation Forest on the numeric vector: if the table model is calm but the row looks unlike training, do not silent-allow. We **lean GO-with-modifications** until the architecture SSOT writes the exact hook. We do not lean GO-as-a-family-detector, and we do not lean GO-as-coverage for named gaps.

### Argument for

- **Generation-0 / “we have not named this yet.”** A multiclass head can only emit families it was trained to emit. Weird geometry on causal features — young account, unique fan-in spike, amount far from personal mean, device change — can still be a reason to **notify** rather than allow.
- **Cheap, causal, CPU.** Same snapshot vector (restricted). No extra rail. Fits the feasibility story.
- **Complement, not competitor.** IF does not replace HGB or YAML. It is a confidence check on residual weirdness.

### Argument against

- **It does not see missing rails.** Isolation Forest cannot detect **BIN testing (T07)** if we never simulate card-auth events. It cannot detect **synthetic merchant collusion (T06)** if we have no merchant-node cycle engine. It cannot detect **model poisoning (T23)** or detector evasion as Cat-4 *attacks*; those are training-set and query-budget problems, not a one-row anomaly score. Saying “IF covers Cat 4 / T06 / T07” would be a coverage lie. The forest only flags **weird rows on the existing FeatureComputer**. If the computer has no card BIN fields, there is no BIN anomaly to isolate.
- **Stamps dominate.** If IF is allowed `call_active_flag` and `beneficiary_changed`, it will isolate APP and invoice the same way a stump would. That is a second near-label, not novelty detection.
- **False positives are the product risk.** Isolation Forest on imbalanced payments will flag genuine bursts (salary day, festival, new landlord). Unbounded IF → notify is how you recreate the kirana problem with a cooler name.
- **Name collision with “unknown attack detector.”** Judges hear Isolation Forest and think unsupervised coverage of the atlas. We will not sell that.

### The modification that keeps it honest

1. **Role:** confidence check → **`notify`**, never a new `label_family`, never a silent decline, never a mule restrict by itself.
2. **Stamp-free subset:** numeric causal columns only. No APP session flags, no invoice envelope booleans, no rule-hit bits that are themselves stamps, no denylist fields. If it cannot fire on a genuine-shaped vector, it does not belong in IF.
3. **Ablate FPR:** report genuine FPR with vs without IF at the same champion operating point. If notify volume blows a frozen epsilon, IF stays off or becomes a case-tab badge, not auth-path.
4. **Named gaps stay named.** Coverage map for T06, T07, Cat 4 does not gain a `built` cell because IF exists.
5. **Pending SSOT:** architecture document must say “IF ⊆ notify / looks_new,” not “IF ⊆ family.” Until that sentence exists, this rationale is the constraint.

If those modifications make IF weak on T06 / T07 / Cat 4 — **it is weak there.** That is correct. Strength on those cells would be a simulator and a rail we refused to fake.

---

## 11. Cheap ML hygiene (professionalism, not novelty)

None of this is the pitch. All of it is how you avoid looking like a weekend notebook.

| Practice | Why |
|----------|-----|
| **Class weight** (or equivalent imbalance handling) from the **lab** mix | Fraud is 1–3% in-sim on purpose. Unweighted HGB will nap on `normal`. Weights are not a claim about India prevalence. |
| **Early stopping on inner-val** | Histogram GBDT can memorize seed-42 mule layouts. Stop on inner val, not on G-test. |
| **Isotonic calibration before any OVR / displayed probability** | Family AP can be ranking-fine and probability-drunk. Brake thresholds (`hold` vs `notify`) assume a score that means something. Isotonic on inner val; report ECE. If we never attach an OVR adapter, we still calibrate the scores Brake reads. |
| **Binary AP + genuine-FPR floor as the HPO / operating-point objective** | Min-family AP without an `n_pos` floor will optimize ATO sampling noise. Binary fraud-vs-normal AP plus a frozen FPR ceiling is the issuer-shaped tradeoff. Family AP remains the **report**, not the unsupervised objective. |
| **Cluster-aware bootstrap CI** | iid row bootstrap pretends 400 mule inbounds to one payee are 400 independent miracles. Resample **entities** (payee / customer), then quote an interval. Wide CI on a thin family is an honest slide. |
| **Permutation importance for the walkthrough only** | A bar chart of “fan_in_unique matters” helps a judge. It is not a live SHAP API, not an attacker oracle, and not a training signal. |

Optuna in a small box, 30–50 trials, freeze recipe, refit: that is AutoML. Shopping architectures on the photographed seed is not.

---

## 12. Rejected ideas

| Idea | Why it looked tempting | Why we rejected it |
|------|------------------------|--------------------|
| **Five one-vs-rest live models** | “Family AP will be cleaner”; architect-peak energy | Fragments data; fusion bugs; walkthrough fights the single `champion.joblib`; Brake wants one family. Family AP is a metric on one head. At most one later OVR if a family is dead on confirmation, not on G-test. |
| **GNN at auth** | Graph fraud papers; looks novel on a poster | Latency, causal neighborhood fetch, GPU story we will not have. Windowed `G(t−)` + unique degree is the graph we can defend. Dynamism is the loop. |
| **AutoGluon (or FLAML/LightGBM AutoML) on the live path** | Leaderboard juice; “we used AutoML” | Novelty becomes a bake-off. Nested Optuna + freeze **is** AutoML. AutoGluon overnight challenger only, never hot path. |
| **CaseScore LLM on authorization** | Chat/invoice narratives are GenAI-shaped | Slow, hostile-promptable, abstention-as-zero risk. LLM may draft analyst text **after** Brake. Auth path is rules + HGB + Brake. Case enrichment is not a payment dependency. |
| **Featuretools / Deep Feature Synthesis on the event log** | Auto-FE as moat | Leakage, width, stamp cousins. Causal named columns + unique degree + invoice envelope beat pairwise Auto-FE as the thing we can explain. |
| **Auto-promote rules / auto-`solved` catalog** | Closed loop looks more closed | Synthetic self-promotion. HITL like Identify: approve is the only path to live / open. Loop M returns `catalog_solved: false`. |
| **Nine working loops** | Older feedback-loop prose | Demo **I + C + M + T (HITL)**. Naming nine handlers we did not build is a judge-fake. Loop G is out. |
| **Harvest FN from the reported G-test** | Fast Loop M “win” | Photographer became coach. Harvest from train/inner or a held G-dev. Headline stays seed 43, one shot. |
| **APP/invoice DT specialists as default** | Easy AP | Near-labels from Generate stamps. Ablation exists to expose that cheat, not to productize it. |
| **Binary fraud-only champion** | Simpler metrics | Cannot feed Brake. APP hold vs ATO decline vs mule restrict would collapse to one button. |

---

## 13. Risks we accepted

We chose this design knowing the following will be true, and we would rather say them than paper over them.

1. **APP without SDK-grade session signals is hard.** Ablation may look ugly. That is the real product constraint, not a failed GBDT.
2. **Several atlas cells will never light a live rule** (T06, T07, Cat 4, some KYC-vendor / deepfake-as-pixels). Isolation Forest does not rescue them. Named gap is the answer.
3. **Default Generate does not train on 22 Atlas recipes.** The mix is five families and default signals unless a `vector_id` is passed. Diversity of Identify ≠ diversity of the parquet. The coverage map must say so.
4. **PSI is sampler QA**, not a claim we match live UPI amount clocks.
5. **Lab base rate ≠ India prevalence.** Class weights and AP are in-lab. Cost sketches are lab units.
6. **AuthGate latency is in-process laptop p50/p99**, not an issuer 50–300 ms SLA.
7. **Loop M is “more of the same injector,”** not a knob-search Loop G, until/unless G is built later. We will not caption M as G.
8. **Invoice and unique-degree contracts must actually be on `X`** or invoice AP / “many senders” rules are theater. We accept that the rationale is only as strong as that feature contract.
9. **One Loop M demo is not an arms race.** `solved` stays unused by the fitter. The UI may show a trajectory; the catalog does not auto-complete.
10. **Isolation Forest, even modified, may not survive the FPR ablation.** Then it stays off. We accepted a maybe-notify, not a coverage miracle.
11. **Thin families (ATO, invoice) will have noisy AP and wide cluster-bootstrap CIs.** We will print `n_pos` rather than invent specialists to stabilize a small cell.
12. **Clock risk:** if the clickable loop is not honest, we keep the honesty floor (coverage, G-test protocol, Brake, causal features) and do not spend remaining time on GNN, AutoGluon, or nine-loop fiction.

---

## 14. Walkthrough narrative

AegisLoop is a closed red/blue lab for GenAI payment fraud, not a 24-headed detector. Identify builds a 24-technique census with named gaps for what payment-time rails cannot see. Generate builds a quiet UPI-like world and injects five economic classes through four engines, with features computed only from the past and a fidelity gate against our own priors — sampler QA, not NPCI production. Defend is one fast histogram GBDT plus nine explainable YAML rules; Brake holds APP, declines ATO, and credit-restricts mule payees instead of treating fraud as a single decline. When blue misses a family, Generate adds a capped extra mix on train only, we refit the frozen recipe, and we only call it a win if average precision on a **new world seed** holds and genuine false positives do not rise. Session flags are stamped on APP rows by construction; we show APP with and without them. Invoice tells are envelope fields at t−, not a GSTIN identity model. Unique in-degree is the graph we need without a GNN. Optuna freeze is AutoML; AutoGluon is not the scorer. Isolation Forest, if present, is a stamp-free weirdness check that may notify — it does not detect BIN testing or poisoning, and it does not mint a new family. Coverage is a census. The loop is the product. That is Decision Intelligence you can click, and that is the argument we will still stand behind when a judge opens the repository.

---

*End of design rationale. Spec, contracts, and live order live in the Defend architecture SSOT. If the two files drift, the SSOT wins on wiring; this file wins on the explanation of locked choices until the SSOT is updated to match them.*
