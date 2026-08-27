"""Map AttackSpec fields to PulseFeatures / features_auth column names."""

from typing import Any

# simulatable_signals key → ledger auth feature column
_SIGNAL_FEATURE_MAP: dict[str, str] = {
    "fan_in_1h": "fan_in_1h",
    "fan_out_ttl_hours": "fan_out_ttl_hours",
    "smurf_cap_ratio": "smurf_cap_ratio",
    "mule_account_age_days": "mule_account_age_days",
    "cashout_mcc_or_sink": "cashout_mcc_or_sink",
    "seasoning_days": "seasoning_days",
    "seasoning_txn_count": "seasoning_txn_count",
    "liveness_score": "liveness_score",
    "doc_consistency": "doc_consistency",
    "device_hash_shift": "is_new_device",
    "kyc_tier": "kyc_tier",
    "call_active_flag": "call_active_flag",
    "copy_paste_payee_flag": "copy_paste_payee_flag",
    "pause_ms": "pause_ms",
    "new_payee": "is_new_payee",
    "urgency_pressure": "urgency_pressure",
    "beneficiary_changed": "beneficiary_changed",
    "gstin_checksum_ok": "gstin_checksum_ok",
    "amount_vs_invoice_delta": "amount_vs_invoice_delta",
    "lookalike_domain_flag": "lookalike_domain_flag",
}

_INJECTOR_EXTRA_FEATURES: dict[str, list[str]] = {
    "graph_mule": ["windowed_fan_in", "burst_velocity"],
    "identity_trajectory": ["account_age_days", "velocity_jump"],
    "app_session": ["persuasion_labels"],
    "doc_beneficiary": ["invoice_amount_mismatch"],
}

_CONTROL_FEATURES: dict[str, str] = {
    "velocity_rule": "burst_velocity",
    "static_kyc": "kyc_tier",
    "liveness": "liveness_score",
    "human_callback": "call_active_flag",
    "otp": "otp_bypass_flag",
    "voice_bio": "voice_match_score",
}

# Catalog YAML may use signal names in features_expected; rules use auth column names.
FEATURE_ALIASES: dict[str, str] = {
    "new_payee": "is_new_payee",
}


def normalize_feature_names(features: list[str]) -> list[str]:
    """Align catalog aliases with features_auth column names."""
    seen: set[str] = set()
    out: list[str] = []
    for name in features:
        canonical = FEATURE_ALIASES.get(name, name)
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out


def derive_features_expected(
    injector_id: str | None,
    simulatable_signals: dict[str, Any] | None,
    control_bypassed: list[str] | None = None,
    economic_class: str | None = None,
) -> list[str]:
    """Derive features_expected for Defend handoff from catalog row fields."""
    features: list[str] = []
    signals = simulatable_signals or {}

    for key, col in _SIGNAL_FEATURE_MAP.items():
        if key in signals:
            features.append(col)

    if injector_id:
        for col in _INJECTOR_EXTRA_FEATURES.get(injector_id, []):
            features.append(col)

    for control in control_bypassed or []:
        col = _CONTROL_FEATURES.get(control)
        if col:
            features.append(col)

    if economic_class == "APP":
        features.append("is_authorized_push")
    if economic_class in {"ATO", "CNP"}:
        features.append("is_new_device")

    seen: set[str] = set()
    out: list[str] = []
    for f in features:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def enrich_spec_features(spec: dict[str, Any]) -> dict[str, Any]:
    """Attach or normalize features_expected on a spec dict."""
    existing = normalize_feature_names(list(spec.get("features_expected") or []))
    if existing:
        return {**spec, "features_expected": existing}
    simulator = spec.get("simulator") or {}
    injector_id = simulator.get("injector_id")
    derived = derive_features_expected(
        injector_id,
        spec.get("simulatable_signals"),
        spec.get("control_bypassed"),
        spec.get("economic_class"),
    )
    if derived:
        spec = {**spec, "features_expected": derived}
    return spec
