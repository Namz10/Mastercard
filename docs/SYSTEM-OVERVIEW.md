# AegisLoop system architecture

Mastercard Innovation Challenge 2026. AI Defense Lab for Payment Security. Problem statement: [`MC_PS.md`](../MC_PS.md). Champion numbers: [`docs/submission/FROZEN-MODEL.md`](submission/FROZEN-MODEL.md).

This is a research-lab prototype. It is not live UPI, not India prevalence, and not a production authorization service. Numbers below are from an internal synthetic evaluation unless a row says otherwise.

**Missing from source.** No component named HSTI-1 exists in this repository. The causal feature engine is `FeatureComputer` in `packages/sim/features.py`.

---

## What the brief requires

The brief asks for one closed-loop system, not three disconnected tools.

**Identify.** Research and map emerging GenAI-powered payment fraud. Breadth and depth. Ground each vector in how payment rails actually work.

**Generate.** Simulate those attacks at scale with fidelity close enough to real payment data that a detector can train and be stress-tested on the result.

**Defend.** Detect, flag, and mitigate the generated attacks. Maximize detection while keeping false positives on genuine payments low.

The attacks you generate become the training and stress-testing ground for the defense. Gaps the defense reveals feed back as new attack work. Judges score diversity of attacks identified, fidelity of simulation, detection efficacy, novelty, and real-world feasibility in live payments.

Unverified in this section: none.

---

## Identify

Identify emits a machine-readable catalog, not 24 generation pipelines. Diversity is coverage of lifecycle, rail, and economic class.

**KillChain Atlas.** Postgres plus pgvector store of `AttackSpec` rows. Census is 24 technique ids (T01-T24) in five categories: network, identity, social / authorized-push (APP), model-targeted, document. Seed file has 29 rows. Some ids have more than one row. Card, 3DS, and network vectors are named even when the simulator stays UPI-structured. Each row is `generate` or `name_only`, with citations and `simulatable_signals`.

**Identify pipeline.** LangGraph `identify_graph` in `packages/agents/identify_graph.py` runs, in order:

1. Scout (candidate collection from Tavily search, RSS, and a domain allowlist)
2. Curator (rank before deep extract)
3. Extractor
4. Grounder (payment-rail grounding)
5. Tier scorer
6. Corroborator
7. Librarian (write to the catalog)

**Analyst gate.** A human promotes, rejects, or edits a row before it is treated as generation input. Dark-web scrape and exploit write-ups are out of scope.

Unverified in this section: whether every newly promoted catalog row currently changes the default population mix. Plan 08 treats `vector_id` as a filter on generate-eligible injectors. `Docs/plans/architecture-defense-doc.md` says the default mix is `DEFAULT_SIGNALS` unless `vector_id` is passed.

---

## Generate

Generate builds a quiet UPI-like world first. Fraud is a constrained perturbation of that baseline, not a separate file glued on.

**Quiet world.** `data/priors.json` plus `packages/sim/world.py`. Deterministic, event-driven, Poisson. Personas, daily caps, known payees, circadian spend. Amounts are integer paise. Party ids use the `VID-SIM-` namespace. An LLM does not write rupees or mule edges.

**Injectors.** Four engines in `packages/sim/inject/`: `graph_mule`, identity trajectory, `app_session`, `doc_beneficiary`. Mix shares and default signal packs live in `packages/sim/inject/mix.py`.

**Verifier and fidelity.** Rail rules in code. Accept or bounded repair. Population export must pass a fidelity gate (PSI versus this run's priors, fraud-rate band, independent `fan_in_1h` recompute). Schema: `gff.txn.v1`. Train target is `label_family` (`normal`, `mule`, `identity_burst`, `ato`, `app_fraud`, `invoice_fraud`), never technique id.

Unverified in this section: hour-of-day in priors is a stated assumption (bimodal 10-12 and 19-22), not a cited NPCI hourly table. Plan 08 forbids calling that a measured UPI distribution.

---

## Defend

Detection without an action is not the product. Live order on one payment at time t:

1. `FeatureComputer` snapshots causal features from `G(t-)`. Deques are pruned to the past, the current event is snapshotted, then the edge is appended. Windows: 1 hour, 24 hours, 7 days, 30 days. Signal groups: velocity, timing, payee/graph, amount, session. Code: `packages/sim/features.py`.
2. Nine live YAML predicates in `data/rules/v0_rules.yaml` fire. Rule-hit bits join the allowlisted feature columns.
3. `sklearn.ensemble.HistGradientBoostingClassifier` predicts `P(label_family)`. Fraud score is `1 - P(normal)` after isotonic calibration. Frozen weights at inference. Not an LLM. Not AutoGluon on this path.
4. Score is compared to `detect_threshold`.
5. Brake (`packages/eval/brake.py`) maps predicted family, score, and rule hits to one action: allow, notify, step-up, hold, decline, mule credit-restrict. APP never silent-declines. Mule action restricts credit on the payee. Hub payees (`VID-SIM-HUB-*`) skip the mule fan-in rule because high fan-in is expected merchant behavior.

**Threshold tradeoff.** A low threshold catches almost all fraud and flags a large share of genuine traffic. The operating rule is maximum recall subject to genuine false-positive rate at most 0.1 percent. That threshold is selected on the training inner validation split of the train world only. It is not searched on the held-out test world.

**Hyperparameter search.** Optuna `TPESampler` (Tree-structured Parzen Estimator) runs on inner fit / inner validation only (`packages/eval/fit.py`). It is not on the authorization path.

Unverified in this section: no numeric leakage-test result (full-graph AUC versus `G(t-)`) is attached here. IsolationForest exists in the fit path and is not the live champion.

---

## Closed loop

The loop cannot grade its own homework.

**Worlds.** Train world seed 46. Development world seed 47 is the promote / reject gate. Photography holdout seed 48 is frozen: never used to choose the threshold, never used to retrain, never regenerated. Seed 49 is a one-shot confirmatory world after a loop ends.

**Loop M (evaluation-gated family-targeted retraining).** Missed fraud families on train / development produce extra events of that family, mix-capped, appended to the train world only. The same classifier class is refit. Promote only if family average precision, genuine FPR, and cost sketch do not collapse versus the prior champion on the development world.

**Reject path.** Hard-negative mining (`v1-train-46__hn-train`) and FPR-only Optuna (`v1-train-46__fpr-v2`) were fit and rejected: identity-burst average precision dropped and cost exploded. Extra data is not assumed to be free.

**Loop I.** Catalog cards can draft YAML rules (`packages/policy/loop_i.py`). Drafts are not live until gated. Techniques that cannot be seen at authorization time stay named gaps (for example T07 card testing, T20-T23 model-targeted classes).

Unverified in this section: none for the v1 seed protocol above. Museum seeds 42/43/44 are a different population and are not mixed into these claims.

---

## Internal synthetic results

Provisional champion: `v1-train-46__loopm-train` (`HistGradientBoostingClassifier`). All rows below are internal G-test seed 48 unless labeled. They are not production and not SAML-D.

Two protocols, two numbers. Do not report the more impressive one alone.

| Protocol | Where the threshold is chosen | Where it is scored | Genuine FPR | Recall |
|---|---|---|---:|---:|
| Protocol freeze | Inner validation of train world 46 (42,399 rows). Max recall subject to genuine FPR ≤ 0.1%. `detect_thr` = 0.9152 | Time-cut eval fold of seed 48, once | 0.032% (57 / 179,049) | 98.52% (3,917 / 3,976) |
| Pareto envelope | Score sweep on G-test (diagnostic, not the operating claim) | Full seed 48 | 0.1% | 98.7% |

Source: [`docs/submission/FROZEN-MODEL.md`](submission/FROZEN-MODEL.md), [`data/validation/v1/internal_01pct_fpr_freeze.json`](../data/validation/v1/internal_01pct_fpr_freeze.json). Precision at the freeze: 98.57%. Confusion at the freeze: TN 178,992, FP 57, FN 59, TP 3,917.

Family ranking on full seed 48 (average precision does not depend on `detect_thr`):

| Family | Positives | AP |
|---|---:|---:|
| App fraud | 1,572 | 0.983 |
| ATO | 395 | 0.533 |
| Identity burst | 1,542 | 0.967 |
| Invoice fraud | 747 | 1.000 |
| Mule | 3,162 | 0.995 |

ATO is the weakest family on ranking. At the frozen operating point on the eval fold, ATO recall is 88.67% (150 positives). Do not treat that recall as the 0.056 eval-fold ATO AP. They answer different questions.

Unverified in this section: SAML-D transfer is documented elsewhere and is not the headline. Cost sketch is a lab relative unit, not Indian rupee loss.

---

## How it runs

One Python process. FastAPI on port 8000. Vite UI on 5173 proxies `/api`. Postgres plus pgvector on host 5433. LLM and Tavily keys stay server-side. Catalog seed: `data/catalog/seed.yaml`.

Unverified in this section: none.

---

## Architecture diagram prompt

Paste the block below into an image model as a single prompt. Layout is Identify (left), Generate (center), Defend (right, dominant), governance band underneath. Solid arrows are runtime. Dashed arrows are offline improvement. Optuna is not on the live path. FeatureComputer is the causal engine. HistGradientBoostingClassifier is the detector. Brake is the policy table.

```
Draw a single flat vector enterprise architecture diagram, landscape 16:9. Title at the top center in dark charcoal: AegisLoop - Software Architecture. No tagline. No paragraph of body text outside the diagram. This is a software architecture diagram of AegisLoop for the Mastercard Innovation Challenge 2026. A technical reviewer must understand IDENTIFY then GENERATE then DEFEND as one governed closed loop in about ten seconds.

Style: Stripe, AWS, GCP, Azure, C4 architecture documentation. White or very-light gray background. Subtle light pastel fills. Dark charcoal typography (IBM Plex Sans or Helvetica Neue). Thin 1-2 px borders. Small corner radius 4-6 px. Generous whitespace. Invisible alignment grid. Orthogonal right-angle connectors only. No crossing arrows. No arrows through boxes.

Palette: restrained teal strokes and pale teal fills for the real-time DEFEND detection path. Muted amber/orange for Brake, policy, and action chips. Muted indigo/navy for the offline governance and retraining band. Pale gray for data-store cylinders. Light gray outlines for the three phase containers. Do not use bright blue as a dominant color. No neon, no gradients, no glassmorphism, no 3D, no glossy surfaces, no drop shadows.

Icons: small professional flat line-art only, subordinate to text. Allowed: database cylinder, document, clock (on FeatureComputer only), graph, gear, model, policy. Never decorative.

Layout. Three large phase containers left to right. LEFT, about 22 percent width: IDENTIFY - Fraud intelligence, pale cool gray-green fill. CENTER, about 28 percent width: GENERATE - Synthetic scenario generation, pale warm gray fill. RIGHT, visually dominant, about 50 percent width: DEFEND - Detection and response, pale teal tint. Beneath all three containers, one full-width horizontal band labeled FEEDBACK LOOP / governance, muted indigo/navy tint. Not a circle. Not an infinity loop.

Each box: concise title plus one subtitle, 5-8 words. No paragraphs in boxes. No metrics in boxes. Total 22 boxes including cylinders. Prefer strong components over clutter.

IDENTIFY column, top to bottom.

Box 1 title: OSINT collection. Subtitle: Tavily, RSS, domain allowlist. Document icon.

Box 2 title: Identify pipeline. Subtitle: Collect, extract, rank, ground in rails.

Box 3 title: KillChain Atlas. Cylinder. Subtitle: Postgres AttackSpec catalog, T01-T24. Tiny side labels, not extra boxes: five categories (network, identity, social/APP, model-targeted, document), 29 seed rows, generate vs name-only, citations, simulatable_signals. This cylinder is the Attack catalog (Postgres plus pgvector). Do not draw a second catalog store.

Box 4 title: Analyst gate. Subtitle: Promote, reject, or edit catalog rows.

GENERATE column.

Cylinder A, top of GENERATE, pale gray: World priors. Subtitle: priors.json, personas and circadian caps.

Box 5 title: Quiet world. Subtitle: Poisson UPI-like ledger from priors. Tiny caption under the box, not a box: personas, circadian spend, daily caps, known payees. LLM never writes rupees or mule edges.

Box 6 title: Injectors. Subtitle: Four engines perturb the quiet world. Tiny side labels, not extra boxes: graph_mule, identity_trajectory, app_session, doc_beneficiary.

Box 7 title: Verifier / fidelity. Subtitle: Rail-rules, PSI, accept or repair.

Cylinder B, bottom of GENERATE, pale gray: Training ledger. Subtitle: gff.txn.v1 Parquet plus sidecar. Tiny caption: seed recorded. label_family train target: normal, mule, identity_burst, ato, app_fraud, invoice_fraud.

DEFEND column, left to right on one dominant teal runtime row. This row is the visual center of gravity.

Box 8 title: Payment event. Subtitle: Amount, parties, timestamp, rail. Tiny caption: synthetic VID-SIM- namespace.

Box 9 title: FeatureComputer. Subtitle: Causal features at time t, G(t-) only. Clock icon. Tiny labels beside the box, not separate services: velocity, timing, payee/graph, amount, session. Caption: prune deques to G(t-), snapshot, then append current edge.

Box 10 title: v0 rules. Subtitle: Nine live YAML predicates. Policy/document icon.

Box 11 title: HistGradientBoostingClassifier. Subtitle: Multiclass P(family), frozen weights. Model icon. Tiny caption: sklearn.ensemble histogram-based gradient boosting. Fraud score equals 1 minus P(normal), after isotonic calibration. This is the detection model. Not AutoGluon. Not an LLM. Not IsolationForest.

Box 12 title: Operating point. Subtitle: Score vs detect_threshold from inner val. Tiny caption: threshold selected on training inner validation only, max recall subject to genuine FPR at most 0.1 percent. Not chosen on the held-out test world.

Box 13 title: Brake. Subtitle: Deterministic policy table, one action. Muted amber/orange fill. Gear or policy icon. Tiny caption: maps predicted family plus score plus rule hits to one action. Not a second model. Not six services. APP never silent-declines. Mule restricts credit on the payee. Hub merchants VID-SIM-HUB-* skip mule-fan-in-burst.

To the right of Brake, six small muted amber action chips, not boxes: allow, notify, step-up, hold, decline, mule credit-restrict.

FEEDBACK LOOP / governance band, left to right under the three zones, muted indigo/navy fills.

Box 14 title: Evaluation. Subtitle: Score held-out synthetic worlds. Tiny caption: development world is the promote/reject gate.

Box 15 title: Weakness detection. Subtitle: Missed fraud families on train, dev. Tiny caption: not the photography holdout.

Box 16 title: Retrain. Subtitle: Same HistGradientBoostingClassifier, new fit. Beside Retrain, a small annotation that is not a live-path box: Optuna TPESampler. Tree-structured Parzen Estimator on inner_fit / inner_val only. Searches HistGradientBoostingClassifier hyperparameters. Optuna must not appear on the teal DEFEND row.

Box 17 title: Validation gates. Subtitle: Family AP, genuine FPR, cost sketch. Tiny caption: must not collapse vs prior champion. Reject path required.

Box 18 title: Model promotion. Subtitle: Champion joblib plus detect_threshold.

Cylinder C, pale gray, next to Model promotion: Model artifact. Subtitle: champion.joblib plus threshold.

Cylinder D, pale gray, next to Evaluation: Holdout worlds. Subtitle: Read-only, photography holdout seed 48. Tiny caption: scored once, never used to pick threshold or retrain.

SOLID arrows (real-time / runtime data flow). Every solid arrow has an obvious source and destination.

IDENTIFY: OSINT collection to Identify pipeline, label candidates. Identify pipeline to KillChain Atlas, label draft AttackSpecs. KillChain Atlas to Analyst gate, label catalog rows. Analyst gate back to KillChain Atlas, short solid, label promote / reject / edit.

IDENTIFY to GENERATE: Analyst gate to Injectors, solid, label Approved AttackSpec patterns.

GENERATE: World priors to Quiet world, solid, label personas, caps, circadian priors. Quiet world to Injectors, solid, label baseline ledger. Injectors to Verifier / fidelity, solid, label candidate events. Verifier / fidelity to Training ledger, solid, label accepted labeled events. World priors to Verifier / fidelity, solid, label PSI vs this run priors.

DEFEND live path, restrained teal, left to right, never interrupted by Optuna: Payment event to FeatureComputer, label event at time t. FeatureComputer to v0 rules, label causal feature vector. v0 rules to HistGradientBoostingClassifier, label features plus rule-hit bits. HistGradientBoostingClassifier to Operating point, label P(family), fraud score. Operating point to Brake, label family plus score plus rule hits. Brake to the six action chips.

DASHED arrows (offline model-development, evaluation, governance, feedback). Route on the governance band and the left/right margins so no dashed shaft crosses a solid shaft. Label the dashed family: Offline improvement / governance.

From Operating point, dashed orthogonal down the right margin, then left along the governance rail into Evaluation, label Offline improvement / governance. Predictions, misses, family metrics.

Holdout worlds to Evaluation, dashed, label photography holdout, score once, read-only.

Evaluation to Weakness detection, dashed, label Offline improvement / governance.

From Weakness detection, a short dashed arrow up into Injectors, label Loop M - family-targeted retrain extras. Caption: evaluation-gated extras appended to TRAIN world only, mix-capped.

From Weakness detection, one thin dashed line left then up into KillChain Atlas, label Loop I, misses to catalog/rules draft. Do not overdraw this. Do not add more Identify return arrows.

Training ledger down to Retrain, dashed, label Offline improvement / governance. Labeled train world.

Weakness detection to Retrain, dashed, label Offline improvement / governance.

Retrain to Validation gates, dashed, label challenger artifact.

Validation gates to Model promotion, dashed, label gated candidate.

From Validation gates, a short dashed reject return to Retrain, label reject, gates must not collapse.

Model promotion to Model artifact, dashed, label approved weights plus threshold.

Model promotion up into HistGradientBoostingClassifier in DEFEND, dashed, label Offline improvement / governance. Approved live scorer.

Tiny legend, bottom corner: Solid arrow = Real-time data flow. Dashed arrow = Offline / governance flow.

Negative constraints. Do not invent or draw: HSTI-1, AI Engine, Data Processor, Smart Module, Analytics Engine, chatbot, internet cloud, NPCI or Mastercard logos, recall percentages, 99.9 percent, AI-powered, robots, brains, shields as decoration, IsolationForest, AutoGluon as the live scorer, Qdrant, Optuna on the live DEFEND path. Do not put metrics in boxes. Do not draw all seven Identify graph nodes. Do not draw six Brake services. Do not draw a giant circle of arrows. Photorealism forbidden.
```

Unverified in this section: the diagram is a system view. It does not claim default Generate always consumes a newly promoted Atlas row (see Identify).
