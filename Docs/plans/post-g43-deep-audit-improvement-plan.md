# Post G-test 43 — Deep Audit & Improvement Plan

> **Superseded for execution by the Post-G43 controlling plan** (`.cursor/plans/post-g43_plan_audit_95013f3c.plan.md`). Key patches landed: nested inner_val A/B Optuna (no outer eval), `genuine_fp` = fp/n_normal, Brake E1b (`act_thr` + nudge≠restrict), sim_days calendar cut, museum v0 via `models/features.v0.json`.

**Date:** 2026-08-29  
**Status:** plan only — do not implement until Wave 0 freeze is acknowledged  
**Frozen benchmark:** G-test seed **43** (`make-gtest`) is historical. Never retune against it.  
**Stage 4:** still `blocked_no_adapter`. This plan is the work that must happen **before** an honest external adapter.

Photography Day numbers (same 390,967-row population):

| Model | binary AP | genuine FPR | precision | recall | ATO AP | Identity AP | Mule AP |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stage 1 HGB | 0.99247 | 5.01% | 11.60% | 99.50% | 0.426 | 0.481 | 0.0247 |
| Stage 2 Optuna | 0.99201 | 14.35% | 4.40% | 100% | 0.489 | 0.457 | 0.0215 |
| Loop M | 0.99258 | 6.67% | 9.01% | 99.96% | 0.487 | 0.392 | 0.0215 |

Headline recommendation from Photography Day (**keep Stage 1**) is correct on FPR. It is **not** evidence the defense is good.

---

## The actual question

> Can this defense reliably detect realistic, evolving payment fraud without relying on artifacts of our own simulator?

**Current answer: no.** Binary AP ≈ 0.99 is a stamp-separability result. The families that look like real payment crime (mule, ATO, identity burst) are either statistically unusable or only moderately ranked, and the action layer credit-restricts ~33k accounts against 29 mule positives.

HGB is not the bottleneck. The generator, the mix budget, the calendar/split interaction, the Optuna objective, and Brake are.

---

## A. What is actually broken (ranked)

### CRITICAL

**C1 — APP and invoice are near-labels, not detection.**  
Evidence: `call_active_flag` / paste / pause / urgency are True iff `app_fraud` (`packages/sim/export.py` zeros them on every other family; `features.py` replay only passes flags when `label_family == "app_fraud"`). Invoice `beneficiary_changed` + `gstin_checksum_ok` + `lookalike_domain_flag` are True iff `invoice_fraud` (`doc_beneficiary.py`; `features.py` explicitly calls this a “stamp skill”). Benign world never emits conflicting rows. G-test AP = 1.0 / 1.0 is the expected outcome of a 3–4 bit label copy. APP ablation still reports AP = 1.0 without flags because `is_new_payee=1` and `amount_vs_p30 ≥ 3.5` remain APP-exclusive.

**C2 — Mule mix share 40% is fiction.**  
`alloc["mule"]` is computed in `mix.py` then ignored. Funnel/cashout/smurf/hop/dust emit a **fixed ~26–34 row toy graph** per world. G-test mule `n_pos=29` is not a sampling accident; it is the injector cardinality. The n_pos child plan’s recommended lever (“raise `DEFAULT_SHARES['mule']`”) **does nothing**.

**C3 — Inner-fit never sees ATO or identity_burst.**  
Seasoning clamped to 76 days parks both bursts at ~day 77. Invoice/APP schedules stretch observed `event_ts` max to ~day 120, so `calendar_cut` (2/3 of *observed* span) falls *after* the bursts. All 111 ATO + 103 identity rows land in outer train, then in the last 20% (`inner_val`). Inner-fit (Optuna, first HGB, permutation importance) has **0 ATO, 0 identity, 4 mule**. Eval fold has **0 ATO, 0 identity**. `results.md` attributing eval zeros to entity holdout is **wrong** — `VID-SIM-F-*` is not in the holdout prefix list.

**C4 — Optuna FPR penalty cannot bind.**  
Objective is `binary_AP(inner_val) − 10 · max(0, genuine_fp − 0.01)`, but `τ` is chosen on the **same** inner_val slice to keep ROC FPR ≤ 1%, so the penalty is ≈ 0. Optuna maximizes AP. Stage 2 then selected `max_depth=5` (search bound). Observed FPR ladder: 1% inner-val target → 3.7% outer eval → 10% Stage 2 eval → **14.35% G-test**. `tune_champion` docstring claiming the threshold stays frozen is false; Stage 2 `op_threshold` moved 1.18e-4 → 2.15e-4.

**C5 — Brake treats mule nudges as credit-restrict, and ignores `min_score`.**  
Stage 1 G-test `mule_credit_restrict = 33,027` vs 29 mule positives. Rules `smurf-under-cap` (`fan_in_1h ≥ 4`) and `rail-hop-burst` (`fan_out_1h ≥ 4`) are `kind: nudge` but Brake ORs any `applies_to: mule` into hard restrict, above calm-down. YAML `min_score` is loaded and never read. 95.8% of detection FPs are still `allow` because Brake’s 0.5 / 0.65 cutoffs sit ~4000× above `op_threshold`. Detection and mitigation are decoupled, and both are wrong in opposite directions.

### HIGH

**H1 — No hard negatives.** Quiet world never produces call/paste/urgency, beneficiary-change, lookalike domain, crypto sink, IMPS hops, device changes, or legitimate high fan-in hubs. High volume ≠ mule is untested because there are no legitimate hubs.

**H2 — Operating point is an ultra-low threshold, not a policy.** Stage 1 `op_threshold ≈ 1.18e-4`. Precision 11.6% at recall 99.5% is Bayes + that threshold (CM: 2,572 TP / 19,597 FP). Loop T `n_fn=0` is the same fact: everything is “caught.” The miner never ran. This is protocol-valid and scientifically empty.

**H3 — Loop M “pass” hid an 18.6% identity_burst AP drop.** ATO 0.426 → 0.487 on `make-gtest`, but identity 0.481 → 0.392. Gate only checks miss-family AP and genuine_fp ε=0.02. Extras: 106 ATO rows, timestamps forced to train `t0` (inner-fit), `seasoning_days_effective=0`. Not a representative ATO campaign.

**H4 — Stage 1/2 `top_features = rail, kyc_tier, account_age_days, …` is the silent permutation fallback**, not importance. `rail` is 99.999% `upi_like`. Loop M is the only run where permutation actually executed. Do not cite rail/KYC dominance from Stage 1 metrics.

**H5 — ATO `is_new_device` is almost unused.** Only 1/111 train ATO rows flip device despite `device_hash_shift: True`. Benign never changes device, so the feature is still a near-lab-exclusive — just not the one the injector claimed to vary.

**H6 — Invoice ablation does not exist.** APP ablation is copied onto G-test JSON (`app_ablation_source=champion_fit`) and still 1.0. No drop-stamps / behavioral-only / portable-only matrices on disk.

### MEDIUM

**M1 — `account_age_days` is a seasoning stamp for ATO/identity (exactly 76.0, std=0).**  
**M2 — `seasoning_txn_count: 45` is never generated.** Farmed accounts are quiet then burst.  
**M3 — Salary/rent priors exist in `priors.json` and are unused.** No geography.  
**M4 — `genuine_fp` is `fp/n_eval`, not `fp/n_normal` (VALIDATION.md).** ~0.3pp.  
**M5 — Isolation Forest is fitted then disabled (`enabled_default: false`).** Not a headline defect.  
**M6 — Optuna trials are in-memory; F5’s “0.678 → 0.702” has no JSON source.** Delete it from the fault log.

### LOW

**L1 — `results.md` still has a duplicate “Photography Day pending” block.**  
**L2 — Stage 1/Loop M `gtest_protocol.json` still names `__gtest` after scores were overwritten to `make-gtest`.** Ledgers are byte-identical; IDs are not.  
**L3 — Stub `injectors.py` is unused for population but still teaches the wrong pattern.**

---

## B. What is merely suspicious (hypotheses)

| Hypothesis | Status | Why it stays a hypothesis |
|---|---|---|
| Deeper Optuna tree overfits inner-val ranking and shifts genuine score mass on seed 43 | Strong, unproven | No score-histogram dump per trial |
| `amount_vs_p30 = 1.0` on cold-start hides first-large-txn | Plausible | No ablation |
| Same-timestamp H(t−) visibility (sort by event_id) | Minor | Causal by ledger order |
| Loop M early timestamps bias inner-fit more than single-family oversample | Plausible | Confounded |
| HGB vs LightGBM vs logistic would change mule ranking | Open | Never benchmarked; mule n=29 so any comparison is noise |

**Confirmed *not* broken:** prune → snapshot → append H(t−) is causal. Denylist keeps technique IDs / `economic_class` / `is_authorized_push` out of X. Freeze identity (`model_freeze_id`) works. Loop T skip on `n_fn=0` is correct given the caught definition. Seed 43 was not used for HPO.

---

## C. Origin of each family AP (generator → features)

| Family | How the attack is written | What the model actually uses | Why the number looks like that |
|---|---|---|---|
| **APP** | One outbound per victim, 3.5× p30, new `VID-SIM-APP-*` mule, all four session flags True | Flags (near-label) + new payee + amount ratio | AP=1.0 even after flag ablation |
| **Invoice** | Uniform ₹2k–9k, lookalike bene, all three payload bools True | Three bools = label | AP=1.0; code comments admit it |
| **ATO** | One farmed account, seasoning 76d, burst every 8 min; device shift almost never applied | Burst velocity / fan-out; age=76 constant | AP~0.43; inner-fit never trained the class head |
| **Identity** | Same injector, no device shift | Age=76 + burst | AP~0.48 Stage 1; **regressed** under Loop M |
| **Mule** | Five tiny modes, ~30 edges, one crypto sink, one IMPS hop; `alloc` ignored | Graph windows only (no stamp) | AP~0.02; n=29 not comparable; 30% payee holdout → train n=4 |

Benign: Poisson UPI-like, fixed device forever, no hubs, no geo, friends may not exist.

---

## D. What should be fixed before external validation

Strict order. Each wave has an acceptance gate. **New generated worlds only.** Seed 43 stays a museum piece.

### Wave 0 — Freeze and measurement (1–2 days, no generator rewrite)

1. Acknowledge G-test 43 as frozen historical. Do not `score_run` it after any recipe/param change.
2. Persist Optuna trials (SQLite or `trials.json`). Delete unsourced 0.678→0.702.
3. Fix permutation-importance fallback: fail the fit if PI throws; store `importances_mean`.
4. Persist `n_pos` by `{fold × inner_fold × family}` in `metrics.json`.
5. Fix `genuine_fp` denominator to `fp / n_normal`.
6. Stop copying APP ablation from champion_fit onto G-test JSON — recompute on the scored world.
7. Document Brake vs detection histograms as separate claims.

Gate: a developer can see inner_fit ATO=0 without a forensic parquet dump.

### Wave 1 — Generator: kill stamps, scale mule, add hard negatives (highest product value)

**Do not bump `n_customers`.** Do not “just add rows.”

**Mule (must do first)**

- Honor `alloc["mule"]`. Target ≥ 150 mule-labeled rows per 90-day 2400-customer world (comparable with margin), via **multiple campaigns**, not one bigger star.
- Vary fan-in (4–40), fan-out, holding period, amount ratios, hops (1–3), mule age, mix of recycled vs new mules.
- Time-spread campaigns across early / mid / late thirds so no family is a single-day spike.
- Add **legitimate hubs** (payroll, marketplace, bill-pay aggregators) with high fan-in that are labeled `normal`. High volume ≠ mule.
- Keep dust/smurf/hop as variants, not the whole family.

**APP**

- Flags become **noisy and partial**: some APP without call, some genuine with paste (support-desk, shared phone). Multiple amount regimes, rails, merchants, mixed into otherwise normal histories. Low-and-slow APP, not only 19:00 3.5× p30.
- Stop gating flag export on `label_family == "app_fraud"`.

**Invoice**

- Payload booleans are **not** a 3-bit label. Legitimate beneficiary changes, valid GSTIN on real payees, lookalike-looking domains that are genuine. Gradual vendor-change campaigns. Varied amounts.

**ATO / identity**

- Multiple farmed accounts; `burst_start` sampled in `[14d, sim_days−7d]`, not one clamped 76.
- Honor `seasoning_txn_count` (actually emit quiet txns).
- Honor `device_hash_shift` with partial takeover, delayed high-value, low-value recon.
- Benign device upgrades so `is_new_device` is not lab-exclusive.

**Calendar**

- Clamp all injector timestamps into `[t0, t0+sim_days)`. Outer/inner cuts use **world horizon**, not observed max.

Gate (on a **new** world, e.g. seed 46): mule `n_pos ≥ 100` on full pop; APP/invoice AP **without stamp columns** < 0.90 (if still 1.0, stamps were not the only shortcut); at least one legitimate hub with `fan_in_1h ≥ 6` labeled normal.

### Wave 2 — Split floors (same generator release)

- After fold assignment, assert min positives per family in `{inner_fit, inner_val, eval}` (or fail loud).
- Mule holdout stays, but hold **campaigns** when `n_mule_payees < 20`.
- Optionally hold a fraction of `VID-SIM-F-*` if identity should be entity-held.
- Loop M extras: sample timestamps from the miss-family empirical prior on train, not `t0 + i seconds`.
- Loop M gate: also fail if any *other* comparable family drops > 5% relative AP (VALIDATION.md already says this; code does not enforce it).

Gate: inner_fit contains every fraud family with n_pos ≥ 15.

### Wave 3 — Features (after Wave 1, or the ablations lie)

Add only what mule/ATO need and what can transfer:

- 24h / 7d velocity, inter-arrival, burstiness vs own 30d baseline (ratio, not only absolute).
- New-counterparty ratio, inbound/outbound asymmetry, payee outbound cashout degree.
- Temporal fan-in (unique payers 1h **and** 24h).

Then run the anti-shortcut matrix on a **fresh** world:

| Slice | Must exist |
|---|---|
| ALL | current |
| WITHOUT_STAMPS | drop 4 APP + 3 invoice + stamp `rule__*` |
| BEHAVIORAL+GRAPH | fan_*, amount_vs_p30, history, burst, new payee, new ratios |
| CURRENT_TXN_ONLY | rail, amount_vs_p30, kyc, age |
| PORTABLE | Wave 8 list |
| WITHOUT_RULE_BITS | drop all `rule__*` |
| WITHOUT_METADATA | drop rail, kyc_tier, account_age_days |

Gate: WITHOUT_STAMPS binary AP drop is **visible**. If ALL and WITHOUT_STAMPS are both ~0.99, Wave 1 failed.

Do **not** add GNN / Featuretools / live prestige scores (architecture forbids them; they also will not exist on SAML-D).

### Wave 4 — Model, Optuna, threshold (HGB stays)

Diagnostic bake-off on the **new** inner_val, not 43: HGB vs logistic (calibrated) vs ExtraTrees. Purpose: is the tree the bottleneck? Expected answer: no.

Replace Optuna objective with a constraint that **cannot** be satisfied by picking τ on the same slice:

```
maximize recall_at_fpr(inner_val, 0.01)
subject to genuine_fp(outer_eval) <= 0.02
```

or: maximize partial AUC in FPR ∈ [0, 0.02], and **select** the trial whose outer-eval FPR is ≤ ceiling. Persist every trial’s inner **and** outer FPR.

**Two operating points:**

| Name | Role | Typical region |
|---|---|---|
| `detect_thr` | ranking / Loop T FN definition | TPR@FPR=1% on inner_val |
| `act_thr` | hard mitigation | precision ≥ 0.40 or score ≥ 0.5, family-calibrated |

Loop T mines against `detect_thr` only if `n_fn ≥ 10`. Do not lower `detect_thr` to manufacture FNs. Do not force a rule.

Calibration: keep isotonic on inner_val; actually read `calibration.stage1_binary`; report ECE **per family**. Loop T must apply the same calibrators as `score_run`.

Gate: new G-test-v2 genuine_fp ≤ 2% at recall ≥ 90% **or** an explicit documented ceiling with precision. Stage 2 must not increase outer FPR by > 2pp vs Stage 1.

### Wave 5 — Brake / rules

- Wire `min_score` into `rule_fires` / Brake.
- Nudge ≠ hard action. Only `hard_flag` (or `pred_family==mule` ∧ score ≥ `act_thr`) may `mule_credit_restrict`.
- Residual `notify` uses a threshold on the PR curve, not a dead 0.65.
- Report `(detection_yhat, policy_action)` jointly. Target: `mule_credit_restrict` count within ~10× of mule n_pos, not 1000×.

Gate: G-test-v2 `mule_credit_restrict / mule_n_pos < 20`, and detection FPs are mostly `notify`/`allow`, not silent restrict.

### Wave 6 — New synthetic photograph (not 43)

| World | Seed | Role |
|---|---|---|
| Historical G-test | 43 | Frozen. Quote only as “v0 lab.” |
| Train v1 | 46 | Fit / HPO / threshold |
| G-dev v1 | 47 | Loop M family pick, Loop T mine |
| G-test v1 | 48 | Headline for the **improved** system |
| Confirm (only if 48 leaked) | 49 | Replacement headline |

Scale stays 2400 × 120 × 90 until Wave 1 mule cardinality is proven. Then increase **campaign count / sim_days**, never customers, if n_pos still thin.

Champion for write-up: the model that wins **FPR-constrained recall + mule ranking + WITHOUT_STAMPS**, not max binary AP.

### Wave 7 — External adapter (only after Wave 3 portable set exists)

Do not reshape SAML-D to look like the simulator.

Portable X (replay from SAML-D 12 CSV headers via FeatureComputer):

```
payee_history_count, amount_vs_p30, fan_in_1h, fan_out_1h,
fan_in_unique_payers_1h, is_new_payee, burst_velocity
```

Optional disclosed proxies: first-seen `account_age_days`, collapsed `Payment_type` → rail.

Never in portable X: APP×4, invoice×3, `is_new_device`, `kyc_tier` constants, stamp `rule__*`.

Lead metric: TPR@FPR, prevalence 0.1039% stated. No subsampled AP vs lab AP. Never map SAML-D to `app_fraud` / `ato`.

Until the adapter exists: `blocked_no_adapter` remains the only honest Stage 4 line.

---

## E. What should NOT be changed

- Frozen G-test 43 numbers and `model_freeze_id`s already photographed.
- Causal H(t−) prune-snapshot-append contract.
- Denylist / `assert_no_x_leak`.
- Multiclass `label_family` with binary score `1−P(normal)` (fine; the OP and stamps are the problem).
- HGB as the default classifier (benchmark others; do not start with a net).
- Loop T “no rule required” as a valid outcome.
- `n_customers=2400` as the mule fix.
- Live GNN, Featuretools, or catalog knobs as X.
- Manufacturing APP/ATO labels on SAML-D.

---

## F. Proposed architecture (after waves)

```
Quiet world + legitimate hubs + noisy channel signals
        ↓
Diverse campaigns (mule networks, partial ATO, mixed APP, ambiguous invoices)
        ↓
Timestamps clamped to sim_days; H(t−) snapshot (unchanged contract)
        ↓
Behavioral + graph + current txn   [stamps optional, never near-labels]
        ↓
Rule bits (hard_flag / nudge distinguished)
        ↓
HGB (or winner of bake-off), isotonic on inner_val
        ↓
detect_thr (FPR-constrained)  and  act_thr (precision-constrained)
        ↓
Brake: hard actions only at act_thr ∧ (hard_flag | high-precision family)
        ↓
Feedback: Loop M on G-dev miss family with time-matched extras;
          Loop T only if real FNs exist at detect_thr
        ↓
Headline: G-test seed 48  →  portable subset  →  SAML-D adapter
```

---

## G. Experimental contract

**Metrics (in this order):** genuine FPR, precision@OP, recall@OP, TPR@FPR={0.1%,0.5%,1%,2%}, family AP only if n_pos≥30, WITHOUT_STAMPS binary AP, Brake action / n_pos ratios.

**Stopping:** Wave 1 fails if APP/invoice WITHOUT_STAMPS AP remains 1.0. Wave 4 fails if Optuna again raises outer FPR > 2pp. Wave 5 fails if restrict/n_pos stays > 100.

**Honesty lines required in any write-up:**

- v0 G-test 43 APP/invoice AP=1.0 is stamp skill.
- v0 mule AP is not comparable (n=29) and the mix share did not control volume.
- Stage 2 Optuna made FPR worse; Stage 1 remains the v0 champion on operations.
- Loop T added zero rules because FN=0 at τ≈1e-4, not because residual fraud was solved.
- External champion AP is not quoted until FeatureComputer replay exists.

---

## H. Suggested implementation sequence for the next agent

1. Wave 0 measurement fixes (small, testable, no world regen).  
2. `mix.py` honor `alloc["mule"]` + campaign loop + timestamp clamp (Wave 1 mule).  
3. Hard-negative hubs + APP/invoice noise (Wave 1 rest).  
4. Split floors + inner_fit family assert (Wave 2).  
5. Ablation harness (Wave 3) **before** adding many new features — prove stamps were the cheat.  
6. Optuna + dual threshold (Wave 4).  
7. Brake `min_score` + nudge semantics (Wave 5).  
8. Generate 46/47/48, photograph 48 once.  
9. Stage 4 adapter against portable X only.

Do not open seed 43 after step 1 except to copy the frozen JSON into an appendix.
