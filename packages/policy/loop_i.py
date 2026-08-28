"""Loop I — draft v0 rules from catalog AttackSpec cards."""

from typing import Any

from packages.catalog.models import AttackSpec, GenerateMode
from packages.catalog.features import normalize_feature_names

# Techniques that cannot be observed at payment auth time (FinalIdentify §11)
_NAMED_GAP_TECHNIQUES = frozenset({"T06", "T07", "T20", "T21", "T22", "T23"})
_NAMED_GAP_CONTROLS = frozenset({"deepfake_video", "bin_testing", "live_crypto_cashout"})


def _is_named_gap(spec: AttackSpec) -> tuple[bool, str]:
    if spec.generate_mode == GenerateMode.name_only:
        return True, "name_only_catalog_row"
    if spec.technique_id.value in _NAMED_GAP_TECHNIQUES:
        return True, f"technique_{spec.technique_id.value}_not_observable_at_auth"
    if spec.dual_use_rating.value == "high":
        return True, "high_dual_use_name_only_expected"
    if spec.category == 4:
        return True, "cat4_loop_a_offline_until_authgate"
    controls = set(spec.control_bypassed or [])
    if controls & _NAMED_GAP_CONTROLS:
        return True, "control_not_observable_at_payment_time"
    # Deepfake KYC video at auth — onboarding plane, case tab for live video
    if spec.technique_id.value == "T09" and spec.lifecycle_stage.value == "onboarding_kyc":
        return True, "deepfake_kyc_onboarding_case_plane"
    if spec.technique_id.value == "T06":
        return True, "merchant_collusion_requires_merchant_nodes"
    return False, ""


def draft_rule_from_spec(spec: AttackSpec) -> dict[str, Any]:
    """
    Loop I: translate one catalog card into a draft rule or explicit named gap.
    T13 APP → call-and-paste-new-payee style hard flag.
    """
    is_gap, gap_reason = _is_named_gap(spec)
    if is_gap:
        return {
            "vector_id": spec.vector_id,
            "technique_id": spec.technique_id.value,
            "coverage_status": "named_gap",
            "named_gap_reason": gap_reason,
            "draft_rule": None,
            "features_expected": list(spec.features_expected),
        }

    features = set(normalize_feature_names(list(spec.features_expected or [])))
    economic = spec.economic_class.value

    # Cat 3 coercion / APP session shape
    if (
        spec.technique_id.value in {"T13", "T14", "T15", "T16", "T17", "T18", "T19"}
        and "call_active_flag" in features
        and "copy_paste_payee_flag" in features
        and "is_new_payee" in features
    ):
        return {
            "vector_id": spec.vector_id,
            "technique_id": spec.technique_id.value,
            "coverage_status": "draft_rule",
            "named_gap_reason": None,
            "draft_rule": {
                "id": "call-and-paste-new-payee",
                "kind": "hard_flag",
                "applies_to": economic,
                "when": [
                    "call_active_flag == true",
                    "copy_paste_payee_flag == true",
                    "is_new_payee == true",
                ],
                "min_score": 0.72,
                "reason": "Possible coercion: call active + payee pasted + new payee",
                "technique_ids": [spec.technique_id.value],
                "status": "draft",
            },
            "features_expected": list(spec.features_expected),
        }

    # Mule fan-in
    if spec.economic_class.value == "mule" and "fan_in_1h" in features:
        return {
            "vector_id": spec.vector_id,
            "technique_id": spec.technique_id.value,
            "coverage_status": "draft_rule",
            "named_gap_reason": None,
            "draft_rule": {
                "id": "mule-fan-in-burst",
                "kind": "hard_flag",
                "applies_to": "mule",
                "when": [
                    "fan_in_1h >= 6",
                ],
                "min_score": 0.65,
                "reason": "Mule receiving burst: high fan-in on young account",
                "technique_ids": [spec.technique_id.value],
                "status": "draft",
            },
            "features_expected": list(spec.features_expected),
        }

    # Invoice / beneficiary (Cat 5)
    if "beneficiary_changed" in features:
        return {
            "vector_id": spec.vector_id,
            "technique_id": spec.technique_id.value,
            "coverage_status": "draft_rule",
            "named_gap_reason": None,
            "draft_rule": {
                "id": "invoice-beneficiary-swap",
                "kind": "hard_flag",
                "applies_to": "BEC",
                "when": [
                    "beneficiary_changed == true",
                    "gstin_checksum_ok == true",
                ],
                "min_score": 0.7,
                "reason": "Invoice tax ID valid but beneficiary account changed",
                "technique_ids": [spec.technique_id.value],
                "status": "draft",
            },
            "features_expected": list(spec.features_expected),
        }

    # Observable features but no template — case-only until Loop R/T proposes
    if features:
        return {
            "vector_id": spec.vector_id,
            "technique_id": spec.technique_id.value,
            "coverage_status": "case_only",
            "named_gap_reason": "observable_features_no_v0_template",
            "draft_rule": None,
            "features_expected": list(spec.features_expected),
        }

    return {
        "vector_id": spec.vector_id,
        "technique_id": spec.technique_id.value,
        "coverage_status": "named_gap",
        "named_gap_reason": "no_observable_auth_features",
        "draft_rule": None,
        "features_expected": list(spec.features_expected),
    }
