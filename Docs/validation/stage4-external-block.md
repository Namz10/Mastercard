# Stage 4 — external-dataset write-up block

**Status:** SAML-D **scored** 2026-08-29 via FeatureComputer replay (`packages/eval/saml_d.py`). Lead metric is **TPR@FPR**, not AP vs lab G-test. Artifacts: `data/validation/v1/holdout_metrics.json`.

Filled after generate-dataset Photography Day (seed 48). Do **not** quote lab-champion AP (0.879 on seed 48) as a SAML-D transfer number.

## SAML-D (primary)

| Field | Value |
|---|---|
| Citations | [CITATIONS.md](../../CITATIONS.md) — Kaggle + ICEBE DOI 10.1109/ICEBE59045.2023.00028 |
| License recorded | Kaggle dataset card (CC / terms on card). Write-day: 2026-08-29. |
| CSV on disk | `data/externals/SAML-D.csv` (951 MB, gitignored). Also accepted at `data/external/SAML-D.csv`. |
| Adapter | `packages/eval/saml_d.py` — streamed FeatureComputer G(t−); APP/invoice/device stamps **false**; rail analogue `upi_like`; `kyc_tier=tier2`; calendar from file ends; eval last ⅓ scored in batches of 2048 |
| CSV headers | `Time`, `Date`, `Sender_account`, `Receiver_account`, `Amount`, `Payment_currency`, `Received_currency`, `Sender_bank_location`, `Receiver_bank_location`, `Payment_type`, **`Is_laundering`**, **`Laundering_type`** |
| Prevalence | 0.1039% (authors); 9,504,852 rows. Eval slice 3,144,540 rows, prevalence 0.1105%. |
| Mapping table | [saml-d-typology-map.template.md](../plans/saml-d-typology-map.template.md) |
| Champion | frozen Stage 1 `v1-train-46`, `detect_thr` ≈ 3.91×10⁻⁴ |
| Champion metrics | **TPR@FPR 0.1% / 0.5% / 1% = 1.09% / 1.47% / 2.27%**. `binary_ap` 0.0021 (lift ~1.9× over 0.1105% prevalence — **not** comparable to lab G-test). Eval n_pos: mule 3084, invoice 22, unmapped 369. |
| Authors’ limit | Will not fully capture real-world transaction unpredictability (quote) |
| Forbidden | Naive CSV-column reindex onto champion; map to `app_fraud` / `ato`; subsampled AP vs lab AP |

**Run:** `make stage4-saml-d` (nice −15, one OpenMP thread). Wall ~22.6 min, peak RSS ~4.1 GB.

## Xente (secondary)

| Field | Value |
|---|---|
| License check | **unverified** 2026-08-29 — no Zindi login in this environment |
| Schema note | Bipartite merchant×customer; not A2A UPI; `account_age` left-censored |
| Champion metrics | **omitted** (license unverified; not used) |

## IBM HI-Small

| Field | Value |
|---|---|
| License | CDLA-Sharing-1.0 (confirm on [ealtman2019/ibm-aml-small](https://www.kaggle.com/datasets/ealtman2019/ibm-aml-small) on write day) |
| PSI | **not run** — CSV not on disk. Code thresholds if scored: `packages/sim/fidelity.py` `PSI_AMOUNT_MAX=0.25` / `PSI_HOUR_MAX=0.35` (not VALIDATION.md 0.2) |
| Champion TPR@FPR | `blocked_no_adapter` for IBM (SAML-D adapter is A2A-shaped; IBM is a peer synthetic, optional later) |

## BAF

Overlap matrix only. **BAF is account-opening fraud under CC BY-NC-ND; we do not transfer the UPI champion.**

| BAF-ish | Our champion X | Overlap? |
|---|---|---|
| tenure / account age | `account_age_days` | analog only (BAF is application-time) |
| income / housing | — | no |
| UPI session stamps | APP×4 | **none** |
| graph fan-in/out | — | **none** on BAF |
| invoice GST flags | invoice×3 | **none** |

Optional native BAF model = different task; do not put its AP in the transfer column.

## APP / invoice public gap

No India-relevant public table with UPI session stamps or GST invoice-fraud at authorization time. SAML-D Over-Invoicing is a **weak** analog (`invoice_fraud` n=22 in eval — family AP withheld). **Never** map SAML-D to `app_fraud`. ETH phishing graphs are structural analogue only — not scored.

## Omit list

TransXion, SynthFin-AML omitted (not live-fetched on write day).

Do not score: Elliptic, PaySim, IEEE-CIS, Sparkov, MoMTSim, TalkingData, BitcoinHeist, LANL/CERT, UCI SMS, FinCEN Files.

## Tests

`tests/test_eval_saml_d.py` — headers, mapping never APP/ATO, causal fan-in, stamps false, missing CSV → `blocked_no_csv`, subsample forbidden, calendar-from-ends.
