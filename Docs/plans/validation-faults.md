# Mastercard Defense — Validation Fault Log

Running record of weaknesses/faults discovered during validation.

**Superseding plan (2026-08-29 deep audit):** [`post-g43-deep-audit-improvement-plan.md`](post-g43-deep-audit-improvement-plan.md)

G-test seed 43 is a **frozen historical benchmark**. Do not retune against it.

## Current faults

### F1 — Synthetic class separability
- **Severity:** CRITICAL (upgraded from Medium after code audit)
- APP fraud and invoice fraud have AP = 1.00 on G-test.
- **Confirmed mechanism:** APP session flags are True iff `app_fraud` (export zeros them on other families; replay only passes flags when `label_family == "app_fraud"`). Invoice payload booleans are True iff `invoice_fraud`. `features.py` already calls invoice a “stamp skill.” Benign world has no hard negatives.
- APP ablation still AP = 1.0 without flags (`is_new_payee` + `amount_vs_p30 ≥ 3.5` remain exclusive). Invoice ablation does not exist.
- **Action:** Wave 1 — noisy/partial stamps, hard negatives, stop label-gating flags.

### F2 — Mule detection is weak
- **Severity:** High
- Mule AP ~0.02–0.06.
- **Confirmed:** no stamp columns; detection must use graph windows; five tiny modes under one label; binary training dominated by stamped APP/invoice.
- **Action:** Wave 1 mule campaigns + legitimate hubs. Do not “fix” by n_customers.

### F3 — Low mule sample size
- **Severity:** CRITICAL (upgraded)
- G-test mule n_pos = 29 < 30 (`not_comparable`).
- **Confirmed:** `alloc["mule"]` is computed in `mix.py` then **ignored**. Injectors emit a fixed ~26–34 row graph. Raising `DEFAULT_SHARES["mule"]` (npos child plan lever) is a no-op.
- **Action:** Honor mix allocation with multiple time-spread campaigns. Target ≥ 150 mule rows before quoting AP.

### F4 — Operating FPR does not generalize
- **Severity:** High
- Inner-val target 1%; Stage 1 outer eval 3.7%; G-test 5.01%; Stage 2 G-test **14.35%**.
- **Action:** Wave 4 — constrain Optuna on outer-eval FPR, not inner-val AP.

### F5 — Optuna objective mismatch
- **Severity:** High
- Inner objective cannot penalize FPR: τ is chosen on the same inner_val slice to keep FPR ≤ 1%, so `binary_AP − 10·max(0, FPR−0.01)` ≈ AP. Stage 2 `max_depth=5` at search bound.
- **Retract:** the “~0.678 → ~0.702” line had **no JSON source** (trials not persisted). Do not quote it.
- **Action:** Persist trials; constrain on outer-eval FPR; dual detect/act thresholds.

### F6 — Optuna boundary warning
- **Severity:** Medium
- Best config `max_depth=5` at bound, combined with worse outer FPR.
- **Action:** Reconsider search space only after Wave 4 objective is fixed.

### F7 — Loop M trade-off
- **Severity:** High (upgraded)
- ATO AP 0.426 → 0.487 on frozen G-test; genuine FPR 5.0% → 6.7% (within ε=0.02).
- **Confirmed additional:** identity_burst AP 0.481 → **0.392** (−18.6% relative). Code gate does not enforce VALIDATION.md “other families <5% relative drop.” `pass: true` is therefore weaker than the written protocol.
- Extras: 106 ATO rows, timestamps forced to train t0, seasoning_effective=0.
- **Action:** Wave 2 — other-family AP gate; time-match extras.

### F8 — Feature quality / shortcut risk
- **Severity:** Medium, with a correction
- Stage 1/2 `top_features = rail, kyc_tier, account_age_days, …` **matches allowlist order**. Permutation importance silent-fallback on exception. `rail` is 99.999% `upi_like` — it cannot honestly dominate.
- Loop M is the only photographed run where PI actually ran (`call_active_flag` first — consistent with APP stamps).
- Real shortcuts are the stamp columns and ATO/identity `account_age_days === 76`.
- **Action:** Wave 0 fail-loud PI; Wave 3 ablation matrix.

### F9 — Inner-fit missing ATO / identity (new)
- **Severity:** CRITICAL
- Train seed 42: all 111 ATO and 103 identity_burst sit in `inner_val`. Inner-fit has 0 / 0 / 4 mule. Eval fold has 0 ATO / 0 identity.
- **Not** VID-SIM-F entity holdout. Cause: seasoning 76d + invoice/APP stretching observed calendar so the 2/3 cut falls after the bursts.
- Optuna and first HGB never train those class heads.
- **Action:** Clamp injector ts to `sim_days`; family floors after split.

### F10 — Brake mule blast radius (new)
- **Severity:** CRITICAL
- Stage 1 G-test `mule_credit_restrict=33027` vs 29 mule positives. Nudge rules (`fan_in ≥ 4`, `fan_out ≥ 4`) set `applies_to: mule`; Brake treats that as hard restrict. YAML `min_score` is never read. 96% of detection FPs are still `allow` (score ≥ 1e-4 but < 0.5).
- **Action:** Wave 5 — nudge ≠ restrict; wire min_score; dual thresholds.

### F11 — Loop T empty FN set (new, protocol-valid)
- **Severity:** Medium (process), High (scientific emptiness)
- `n_fn=0` on G-dev because `op_threshold ≈ 1.18e-4`. Miner never ran. Not “residual fraud solved.”
- Loop T also scores **uncalibrated** probabilities against a calibrated threshold.
- **Action:** Do not force a rule. Redefine FN against a detection threshold that leaves residual errors. Apply calibrators in Loop T.

### F12 — External transfer blocked (unchanged)
- **Severity:** High for Stage 4
- No FeatureComputer adapter. Champion X is mostly simulator stamps. Portable surface is ~7 graph/velocity columns.
- **Action:** Wave 7 only after Wave 3 portable set. Keep `blocked_no_adapter` until then.

## Evaluated this pass (was “not yet”)

- Loop T — skipped, `insufficient_fn`, 0 drafts. Valid skip, empty science.
- Photography Day / untouched G-test 43 — complete; freeze it.
- Champion selection — **keep Stage 1** on FPR; Loop M wins ATO and loses identity; Optuna loses FPR.
- External dataset — still blocked.

## Rule for this log

Add faults as they are discovered. Do not hide negative results. For each fault record:
1. What happened
2. Why it matters
3. Severity
4. What should be tested/fixed
