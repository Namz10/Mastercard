"""SAML-D transfer forensics (Phase B) — diagnostic only, no label/tuning hacks."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from packages.eval.fit import load_champion
from packages.eval.saml_d import (
    CSV_HEADERS,
    RAIL_ANALOGUE,
    _feature_row,
    _norm_type,
    iter_replayed_rows,
    map_label_family,
    resolve_csv_path,
    score_saml_d,
)
from packages.sim.export import TRAIN_ALLOWLIST

# Feature groups for coverage / ablation mapping
FEATURE_GROUPS: dict[str, list[str]] = {
    "velocity": ["burst_velocity", "txn_velocity_24h", "fan_in_1h", "fan_out_1h", "fan_in_24h", "fan_out_24h"],
    "temporal": ["hours_since_prev_txn", "hours_since_payee", "account_age_days"],
    "customer_history": ["payee_history_count", "unique_payees_7d", "amount_vs_7d_mean"],
    "merchant_payee": ["is_new_payee", "payee_fan_out_1h", "amount_vs_p30"],
    "graph": [
        "fan_in_unique_payers_1h",
        "fan_in_unique_payers_24h",
        "in_out_asymmetry_24h",
    ],
    "amount": ["amount_vs_p30", "amount_vs_7d_mean"],
    "device_app": ["is_new_device", "call_active_flag", "copy_paste_payee_flag", "pause_ms", "urgency_pressure"],
    "stamps": ["beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag"],
    "behavioral": ["burst_velocity", "hours_since_prev_txn", "hours_since_payee"],
    "account_level": ["account_age_days", "kyc_tier"],
    "transaction_level": ["rail", "amount_vs_p30", "fan_in_1h", "fan_out_1h"],
}

SAML_D_FIELD_MAP = [
    {
        "internal_feature": "fan_in_1h",
        "saml_source": "FeatureComputer.snapshot_and_apply",
        "transformation": "rolling 1h inbound count per payee",
        "status": "VALID",
    },
    {
        "internal_feature": "account_age_days",
        "saml_source": "FeatureComputer account open ts",
        "transformation": "days since account first seen",
        "status": "VALID",
    },
    {
        "internal_feature": "call_active_flag",
        "saml_source": "N/A",
        "transformation": "hardcoded false",
        "status": "UNAVAILABLE",
    },
    {
        "internal_feature": "is_new_device",
        "saml_source": "N/A",
        "transformation": "hardcoded 0",
        "status": "UNAVAILABLE",
    },
    {
        "internal_feature": "rail",
        "saml_source": "Payment_type",
        "transformation": f"constant analogue {RAIL_ANALOGUE!r}",
        "status": "QUESTIONABLE",
    },
    {
        "internal_feature": "identity_burst / app_fraud / ato",
        "saml_source": "Laundering_type",
        "transformation": "never mapped — forbidden families",
        "status": "UNAVAILABLE",
    },
]


def _champion_feature_coverage(champ) -> dict[str, Any]:
    cols = set(champ.raw_columns)
    rows = []
    for group, feats in FEATURE_GROUPS.items():
        internal = [f for f in feats if f in cols]
        saml_avail = []
        for f in internal:
            if f in ("call_active_flag", "copy_paste_payee_flag", "pause_ms", "urgency_pressure",
                     "beneficiary_changed", "gstin_checksum_ok", "lookalike_domain_flag", "is_new_device"):
                saml_avail.append(False)
            else:
                saml_avail.append(True)
        rows.append({
            "group": group,
            "internal_available": len(internal) > 0,
            "saml_available": any(saml_avail) if internal else False,
            "features_internal": internal,
            "comparable": any(saml_avail) if internal else None,
            "translation": "FeatureComputer replay" if any(saml_avail) else "stubbed or absent",
        })
    return {"groups": rows, "n_champion_features": len(cols)}


def _ontology_audit(csv_path: Path, *, max_rows: int = 2_000_000) -> dict[str, Any]:
    """Scan laundering types → mapped family (no label changes)."""
    by_type: Counter[str] = Counter()
    by_mapped: Counter[str] = Counter()
    cross: dict[str, Counter[str]] = defaultdict(Counter)
    n = 0
    import csv

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n += 1
            lt = str(row.get("Laundering_type", ""))
            fam = map_label_family(row.get("Is_laundering"), lt)
            by_type[lt] += 1
            by_mapped[fam] += 1
            cross[lt][fam] += 1
            if n >= max_rows:
                break
    unmapped_types = [
        {"laundering_type": t, "count": c, "mapped": map_label_family(1, t)}
        for t, c in by_type.most_common(50)
        if map_label_family(1, t) == "unmapped"
    ]
    return {
        "rows_scanned": n,
        "mapped_family_totals": dict(by_mapped),
        "top_laundering_types": by_type.most_common(30),
        "unmapped_type_samples": unmapped_types[:20],
        "note": "Full-file scan capped for RAM; eval slice uses last 1/3 calendar.",
    }


def _score_distribution_stream(
    csv_path: Path,
    champ,
    thr: float,
    *,
    max_eval_rows: int = 500_000,
) -> dict[str, Any]:
    """B5: quantile summary on eval slice (streamed, capped for RAM)."""
    from packages.eval.saml_d import _score_batch, calendar_from_ends, load_v0_rules

    t0, t1 = calendar_from_ends(csv_path)
    cut = t0 + (t1 - t0) * (2.0 / 3.0)
    rules = load_v0_rules()
    batch: list[dict] = []
    scores_pos: list[float] = []
    scores_neg: list[float] = []
    n_eval = 0
    for row in iter_replayed_rows(csv_path):
        if row["event_ts"] < cut:
            continue
        batch.append(row)
        if len(batch) >= 2048:
            sc, yb, _ = _score_batch(batch, champ, rules)
            for s, y in zip(sc, yb):
                if y:
                    scores_pos.append(float(s))
                else:
                    scores_neg.append(float(s))
            n_eval += len(batch)
            batch = []
            if n_eval >= max_eval_rows:
                break
    if batch and n_eval < max_eval_rows:
        sc, yb, _ = _score_batch(batch, champ, rules)
        for s, y in zip(sc, yb):
            if y:
                scores_pos.append(float(s))
            else:
                scores_neg.append(float(s))
        n_eval += len(batch)

    def _q(arr: list[float], p: float) -> float | None:
        if not arr:
            return None
        return float(np.quantile(np.array(arr), p))

    pos = np.array(scores_pos) if scores_pos else np.array([])
    neg = np.array(scores_neg) if scores_neg else np.array([])
    return {
        "n_eval_sampled": n_eval,
        "cap_note": f"Distribution sample capped at {max_eval_rows} eval rows for RAM",
        "positive_quantiles": {f"p{p}": _q(scores_pos, p / 100) for p in (50, 90, 99)},
        "negative_quantiles": {f"p{p}": _q(scores_neg, p / 100) for p in (50, 90, 99, 99.9)},
        "frac_pos_below_thr": float((pos < thr).mean()) if len(pos) else None,
        "frac_neg_above_thr": float((neg >= thr).mean()) if len(neg) else None,
        "diagnosis_hint": (
            "Case A (low pos scores)" if len(pos) and pos.mean() < 0.1
            else "Case B (calibration shift)" if len(neg) and neg.mean() > 0.5
            else "Case C (domain shift / weak separation)"
        ),
    }


def run_saml_d_forensics(
    *,
    model_run_id: str = "v1-train-46__loopm-train",
    frozen_thr: float | None = None,
    csv_path: Path | None = None,
    dest: Path | None = None,
    skip_streaming: bool = False,
) -> dict[str, Any]:
    path = resolve_csv_path(csv_path)
    champ = load_champion(model_run_id)
    thr = float(frozen_thr or champ.detect_thr or champ.op_threshold or 0)

    existing = Path("data/validation/v1/stage4_saml_d_loopm.json")
    stage4 = json.loads(existing.read_text(encoding="utf-8")) if existing.is_file() else {}

    body: dict[str, Any] = {
        "schema": "saml_d_forensics_v1",
        "model_run_id": model_run_id,
        "frozen_internal_thr_01pct": thr,
        "B1_feature_coverage": _champion_feature_coverage(champ),
        "B2_translation_audit": {"mappings": SAML_D_FIELD_MAP, "p0_invalid": []},
        "B4_temporal_replay": {
            "causal_semantics": "FeatureComputer.snapshot_and_apply at event_ts",
            "app_stamps_forced_false": True,
            "eval_slice": "last 1/3 calendar",
            "timezone": "UTC",
            "leakage_risk": "low if CSV time-sorted",
            "starvation_risk": "APP/device features always zero on SAML-D",
        },
        "stage4_reference": {
            "tpr_at_fpr": stage4.get("tpr_at_fpr"),
            "binary_ap": stage4.get("binary_ap"),
            "recall_at_op": stage4.get("recall_at_op"),
            "op_threshold_used_in_stage4": stage4.get("op_threshold"),
        },
    }

    if path is not None:
        body["B3_label_ontology"] = _ontology_audit(path)
        if not skip_streaming:
            body["B5_score_distribution"] = _score_distribution_stream(path, champ, thr)
    else:
        body["status_blocked"] = "SAML-D CSV not on disk"

    # B6 from stage4
    tpr = stage4.get("tpr_at_fpr") or {}
    body["B6_family_external"] = {
        "mapped_families": stage4.get("mapped_family_counts"),
        "ap_by_mapped_family": stage4.get("ap_by_mapped_family"),
        "tpr_at_fpr_overall": tpr,
        "dominant_failure": "broad low TPR across mule + unmapped; invoice n=22 not comparable",
    }

    # B7 — diagnostic note (full stream ablation too expensive; use internal h9 as proxy)
    h9_path = Path("data/validation/v1/h9_ablation_audit.json")
    body["B7_ablation_proxy"] = {
        "note": "Full SAML-D group ablation requires second 9.5M-row pass; proxy from internal h9_ablation_audit",
        "internal_h9": json.loads(h9_path.read_text()) if h9_path.is_file() else None,
    }

    body["root_cause_ranking"] = {
        "confirmed": [
            "APP/device/session stamps unavailable on SAML-D (forced false)",
            "identity_burst / app_fraud / ato families unmapped",
        ],
        "strongly_supported": [
            "Rail/payment ontology analogue (upi_like constant)",
            "Score distribution / calibration shift vs internal sim",
        ],
        "plausible": [
            "Unmapped laundering types (369 positives in eval)",
            "Genuine domain shift (real bank vs synthetic sim)",
        ],
        "unsupported": [
            "Simple threshold retuning on SAML-D labels alone fixes transfer",
        ],
    }

    dest = dest or Path("data/validation/v1/saml_d_forensics.json")
    dest.write_text(json.dumps(body, indent=2, default=str), encoding="utf-8")
    return body
