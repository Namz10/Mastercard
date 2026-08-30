# Child 4 — Stage 4 external-dataset (required; no adapter in-repo)

**Parent:** [Master validation protocol](../../.cursor/plans/external_holdout_validation_64f9d54e.plan.md)  
**When:** After generate-dataset Stage 3b freeze.  
**Audit:** [`evaluation-validity-audit.md`](evaluation-validity-audit.md) Check 9 — no SAML-D adapter implemented.  
**Lab spec (old names, do not copy “vault”):** [`VALIDATION.md`](../../VALIDATION.md) §6.

**Terminology:** **external-dataset**. Never HoldoutVault / vault.

**This child is protocol + mapping + citations.** It does **not** add an in-repo adapter, Makefile target, or `packages/eval/holdout/`. Building FeatureComputer replay for SAML-D is a **separate** code plan after this SOP.

**Do not quote lab-champion AP or TPR@FPR on external-dataset until that adapter exists.** Mapping table + citations are **still required** for the .docx. Mark the metrics row `blocked_no_adapter`.

---

## Ranking (locked)

### PRIMARY scored Cat 1 — SAML-D (when adapter exists)

| Item | Value |
|---|---|
| Kaggle live | [berkanoztas/synthetic-transaction-monitoring-dataset-aml](https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml) |
| Paper | ICEBE 2023, doi [10.1109/ICEBE59045.2023.00028](https://doi.org/10.1109/ICEBE59045.2023.00028) (also cited as arXiv:2404.14746 in older notes — cite the IEEE DOI in the .docx) |
| Scale | 9,504,852 transactions; **0.1039%** suspicious; `SAML-D.csv` **996.17 MB**; **12** columns; **28** typologies; **15** graph structures |
| Authors’ limit | Will not fully capture real-world transaction unpredictability — quote, do not hide |

**CSV headers (adapter MUST use these):**

`Time`, `Date`, `Sender_account`, `Receiver_account`, `Amount`, `Payment_currency`, `Received_currency`, `Sender_bank_location`, `Receiver_bank_location`, `Payment_type`, **`Is_laundering`**, **`Laundering_type`**

Paper / Kaggle **prose** often says “Is Suspicious” / “Type”. Those are **not** confirmed CSV headers. Mapping and code that look for `Is_Suspicious` will fail on the live file.

**Never map SAML-D rows to `app_fraud` or `ato`.** No UPI session stamps, no ATO device graph in this table.

**FeatureComputer replay** ([`packages/sim/features.py`](../../packages/sim/features.py) `G(t−)`):

| Use | Replay required? |
|---|---|
| Score the **lab champion** (Stage 3b HGB on TRAIN_ALLOWLIST) | **YES** — map to events → causal features → missing APP/invoice flags **false** → `reindex` to champion columns |
| Aggregate **PSI** (amount, hour, degree) | **NO** |
| A **native-column** SAML-D model (train trees on SAML-D columns) | **NO** — different task; label “SAML-D native model”, not champion transfer |

Naive `reindex` of raw SAML-D columns onto the champion is **invalid**. That is why AP is forbidden until the adapter exists.

### SECONDARY — Xente (Zindi DSN 2019)

- Real payments, **smaller**, **bipartite** (customer–merchant), **not** A2A UPI.
- **Verify login and license** before download or citation. If the competition terms block the write-up, **omit scores** and keep a one-line “license unverified / not used” — do not pirate.
- `account_age` (or tenure analogue) is **left-censored** — state it; do not treat as full history.
- Never claim Xente is a UPI A2A holdout. Never replace SAML-D as primary Cat 1.

### Generator peer — IBM HI-Small only

- **HI-Small** only. **Not** IBM AML Large.
- Job: PSI of amounts / 1h-degree vs generate-dataset train; **optional** TPR@FPR if a replay adapter exists.
- CDLA-Sharing-1.0 (confirm on the Kaggle card the day you write).
- Story: peer synthetic world, not production AML. Do not “we beat IBM”.

PSI does **not** require FeatureComputer replay. Champion TPR@FPR on IBM **does**.

### Mapping only — BAF (Feedzai, NeurIPS 2022)

- License: **CC BY-NC-ND** — no champion transfer, no redistributing a scored dump as a product artifact.
- Feature-overlap matrix only (e.g. tenure ↔ `account_age_days`). Account-opening fraud; no India Stack; no UPI session flags.
- Optional **separate** model trained on BAF is a different paper-task. Do not put its AP in the champion transfer column.

---

## Omit from .docx unless live fetch on the write day

| Dataset | Rule |
|---|---|
| TransXion | Dead-link risk. Fetch the paper/GitHub **the day you write**; else omit entirely |
| SynthFin-AML | Same |

Silence is better than a 404 citation.

---

## Do not score (named gaps, not transfer)

Do not put AP / TPR / “transfer AUC” on:

| Dataset | Why |
|---|---|
| Elliptic | Bitcoin graph / illicit addresses — not AuthGate ledger rows |
| PaySim | Mobile-money sim; not our schema; not this champion’s X |
| IEEE-CIS | Card / Kaggle fraud; not UPI A2A |
| Sparkov | Generated card stream; not our allowlist |
| MoMTSim | Toy fraud **rate** (~53%) — metric theatre |
| TalkingData | No `amount`; clicks, not payments |
| BitcoinHeist | Pre-aggregated address/window features |
| LANL / CERT | Insider / auth logs; **no amount** |
| Invoice / BEC public tables | Not a linked UPI invoice graph we can score |
| UCI SMS | SMS spam, not payment-time |

[`VALIDATION.md`](../../VALIDATION.md) §6.6 also names FinCEN Files (SAR-level, not rail events). Same rule: **not scored**.

---

## APP / invoice public gap

**Confirmed:** no India-relevant public table with UPI-linked APP session stamps or GST invoice-fraud at authorization time.

- Do **not** invent a SAML-D → `app_fraud` map.
- Native-speaker / LLM-as-judge on **our** transcripts remains generate-dataset / Identify eval ([`VALIDATION.md`](../../VALIDATION.md) §6.3) — not Stage 4 transfer.
- **ETH phishing** (public Ethereum phishing accounts / graphs): **structural analogue only** (graph victim → sink). Not APP, not UPI, not a champion score. One paragraph max if used.

---

## SAML-D mapping table (required even when `blocked_no_adapter`)

Frozen for the write-up. Adjust cells only with a citation to typology names in `Laundering_type` **as they appear in the CSV**, not marketing copy.

| `Laundering_type` / structure class | Our `label_family` | In family AP? |
|---|---|---|
| Smurfing / structuring / fan-in / fan-out / layering / deposit-send / dust-like | `mule` | Yes if n_pos allows |
| Over-invoicing (if present in CSV types) | `invoice_fraud` | Weak analog; report separately |
| Behavioral-change / single-large with no graph motif | `unmapped` | In **binary** suspicious label only; **out** of family AP |
| Normal / non-laundering (`Is_laundering=0`) | `normal` | Genuine FPR / TPR@FPR negatives |
| Anything implying ATO or APP | **Do not map** | — |

Fill the live distinct `Laundering_type` values from the CSV (28 typologies) into this table when you have the file. Until download: publish the **rule** above plus “types not yet enumerated from live CSV”.

**Never** `app_fraud`. **Never** `ato`.

---

## SAML-D scoring procedure (adapter exists — future code plan)

Not implemented here. When it does:

1. **Ingest:** Kaggle slug above; gitignore the ~1 GB CSV; never commit it.
2. **Split analog to G2:** sort `Date`+`Time`; last 1/3 calendar = eval; entity-disjoint mule sinks on `Receiver_account` for types mapped to `mule`.
3. **Negatives:** score **full eval negatives** if compute allows. AP is **not** invariant to class balance. Subsampling negatives **inflates AP**. If you must subsample: record `negative_subsample_ratio`; **lead TPR@FPR**; AP secondary with prevalence; **never** compare that AP to generate-dataset G-test AP; **never** apply “AP < lab/2” on subsampled AP.
4. **Features:** replay `FeatureComputer`; collapse payment types to a rail analogue (`upi_like` or stated mapping); `kyc_tier` default; APP/invoice/device flags false.
5. **Threshold:** frozen generate-dataset Stage 3b inner-val `op_threshold`. Ranking TPR@FPR is the robust comparison under prevalence shift (lab ~0.5–3.5% vs SAML-D **0.1039%**).
6. **Report:** generate-dataset G-test TPR@FPR vs SAML-D TPR@FPR; mapping table + `n_pos`; prevalence both sides. Loop F “AP halved” **only** on full negatives.

Until step 4 exists in-repo: **stop after mapping + citations.** No invented AP.

---

## Xente procedure (when licensed)

1. Confirm Zindi DSN 2019 access/license in the lab notebook (date, account, terms URL).
2. Schema: merchant × customer; not A2A. Map what overlaps (`Amount`, time, account age **left-censored**).
3. Do not force TRAIN_ALLOWLIST columns that do not exist.
4. Secondary table only. Lead TPR@FPR if scored with a honest feature map; otherwise mapping-only.

---

## IBM HI-Small procedure

1. Download **Small** only.
2. PSI vs generate-dataset train amounts / hour / degree. Thresholds: document whether you use [`packages/sim/fidelity.py`](../../packages/sim/fidelity.py) `PSI_AMOUNT_MAX=0.25` / `PSI_HOUR_MAX=0.35` (code) vs VALIDATION.md 0.2 — **do not silently mix**.
3. Optional TPR@FPR only with replay adapter.
4. Pattern map → `mule` / unmapped. No `app_fraud` / `ato`.

---

## BAF procedure

Overlap matrix. Sentence: “BAF is account-opening fraud under CC BY-NC-ND; we do not transfer the UPI champion.” Optional native BAF model = appendix, different task.

---

## Write-up block (required deliverable)

| Row | Content |
|---|---|
| SAML-D | Citations (Kaggle + ICEBE DOI) + header truth (`Is_laundering` / `Laundering_type`) + mapping table + prevalence 0.1039% + `blocked_no_adapter` **or** TPR@FPR if adapter |
| Xente | License verification result; bipartite/merchant; left-censored age; no AP unless licensed **and** honest map |
| IBM HI-Small | PSI (± TPR@FPR); not Large |
| BAF | Overlap only |
| APP/invoice | Public gap; ETH phishing analogue optional |
| Omit list | TransXion/SynthFin omitted unless fetched; do-not-score list named |

**Forbidden:** subsampled AP vs lab AP; “real UPI”; scoring Elliptic/PaySim/IEEE-CIS as this champion’s holdout; mapping SAML-D to APP/ATO; quoting champion AP without FeatureComputer replay.

**Gate:** [`Docs/validation/stage4-external-block.md`](../validation/stage4-external-block.md) complete (scored **or** `blocked_no_adapter` with mapping + citations). Citations SSOT: [`CITATIONS.md`](../../CITATIONS.md). Typology template: [`saml-d-typology-map.template.md`](saml-d-typology-map.template.md). No `holdout_metrics.json` until adapter exists.
