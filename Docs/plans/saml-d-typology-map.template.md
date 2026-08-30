# SAML-D typology → `label_family` mapping

Filled from ICEBE 2023 prose (17 suspicious + 11 normal). **Never** map to `app_fraud` or `ato`.
Live `Laundering_type` strings are enumerated on CSV download (underscores/casing may differ; adapter `_norm_type` matches).

## Suspicious (`Is_laundering=1`)

| `Laundering_type` (paper) | `label_family` | In family AP? | Notes |
|---|---|---|---|
| Fan-In | `mule` | if n_pos ≥ 30 | graph |
| Fan-Out | `mule` | if n_pos ≥ 30 | graph |
| Cycle | `mule` | if n_pos ≥ 30 | graph |
| Bipartite | `mule` | if n_pos ≥ 30 | graph |
| Stacked Bipartite | `mule` | if n_pos ≥ 30 | graph |
| Scatter-Gather | `mule` | if n_pos ≥ 30 | graph |
| Gather-Scatter | `mule` | if n_pos ≥ 30 | graph |
| Layered Fan-In | `mule` | if n_pos ≥ 30 | layering |
| Layered Fan-Out | `mule` | if n_pos ≥ 30 | layering |
| Structuring | `mule` | if n_pos ≥ 30 | placement |
| Smurfing | `mule` | if n_pos ≥ 30 | placement |
| Deposit-Send | `mule` | if n_pos ≥ 30 | rapid cash then send |
| Cash Withdrawal | `mule` | if n_pos ≥ 30 | interview typology |
| Over-Invoicing | `invoice_fraud` | weak analog | not GST UPI invoice |
| Single Large Transaction | `unmapped` | binary only | no graph motif |
| Behaviour Change 1 | `unmapped` | binary only | new counterparties |
| Behavioural Change 2 | `unmapped` | binary only | high-risk locations |

## Normal (`Is_laundering=0`)

| `Laundering_type` (paper) | `label_family` | In family AP? |
|---|---|---|
| Single Transaction, Fan-Out, Fan-In, Mutual, Forward, Periodical, Cash Withdrawal, Cash Deposit, Small Fan-out, Mutual Plus, Normal Group | `normal` | negatives |

Adapter always maps `Is_laundering=0` → `normal` regardless of the type string.

## Live CSV strings (2026-08-29)

Exact `Laundering_type` values on `data/externals/SAML-D.csv` (adapter `_norm_type` matches these to the table above):

**Suspicious:** `Behavioural_Change_1`, `Behavioural_Change_2`, `Bipartite`, `Cash_Withdrawal`, `Cycle`, `Deposit-Send`, `Fan_In`, `Fan_Out`, `Gather-Scatter`, `Layered_Fan_In`, `Layered_Fan_Out`, `Over-Invoicing`, `Scatter-Gather`, `Single_large`, `Smurfing`, `Stacked Bipartite`, `Structuring`.

**Normal (always `normal` when `Is_laundering=0`):** `Normal_Cash_Deposits`, `Normal_Cash_Withdrawal`, `Normal_Fan_In`, `Normal_Fan_Out`, `Normal_Foward`, `Normal_Group`, `Normal_Mutual`, `Normal_Periodical`, `Normal_Plus_Mutual`, `Normal_Small_Fan_Out`, `Normal_single_large`.
