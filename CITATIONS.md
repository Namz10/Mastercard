# External-dataset citations (Stage 4)

Canonical citations for the validation write-up. Do not copy HoldoutVault / vault terminology into the .docx.

## SAML-D (primary Cat 1)

- Kaggle: [berkanoztas/synthetic-transaction-monitoring-dataset-aml](https://www.kaggle.com/datasets/berkanoztas/synthetic-transaction-monitoring-dataset-aml)
- Paper: ICEBE 2023, [10.1109/ICEBE59045.2023.00028](https://doi.org/10.1109/ICEBE59045.2023.00028)
- CSV label columns: `Is_laundering`, `Laundering_type` (not paper prose "Is Suspicious" / "Type")
- Prevalence: 0.1039% suspicious; 28 typologies (17 suspicious / 11 normal per ICEBE 2023). Live `Laundering_type` strings (2026-08-29): Behavioural_Change_1/2, Bipartite, Cash_Withdrawal, Cycle, Deposit-Send, Fan_In, Fan_Out, Gather-Scatter, Layered_Fan_In/Out, Over-Invoicing, Scatter-Gather, Single_large, Smurfing, Stacked Bipartite, Structuring, plus 11 `Normal_*` types including typo `Normal_Foward`.
- Adapter: `packages/eval/saml_d.py` (streamed FeatureComputer replay). Write-day 2026-08-29: scored last-⅓ calendar; lead TPR@FPR 1.09% / 1.47% / 2.27% at 0.1% / 0.5% / 1% FPR. Do not compare `binary_ap` 0.0021 to lab G-test.

## Xente (secondary)

- Zindi DSN 2019 — verify login/license before download; record terms URL and date in `Docs/validation/stage4-external-block.md`

## IBM HI-Small (generator peer)

- Kaggle: [ealtman2019/ibm-aml-small](https://www.kaggle.com/datasets/ealtman2019/ibm-aml-small) — confirm card on write day
- License: CDLA-Sharing-1.0 (confirm on card)
- **Not** IBM AML Large

## BAF (mapping only)

- Feedzai NeurIPS 2022; CC BY-NC-ND — overlap matrix only; no champion transfer
