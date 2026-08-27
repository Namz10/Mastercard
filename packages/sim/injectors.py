"""Injector stubs — read simulatable_signals from AttackSpec; perturb ledger envelope."""

import uuid
from datetime import datetime, timezone
from typing import Any

from packages.catalog.models import AttackSpec


def _event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:16]}"


def _base_envelope(spec: AttackSpec, lifecycle_stage: str | None = None) -> dict[str, Any]:
    stage = lifecycle_stage or spec.lifecycle_stage.value
    return {
        "schema": "gff.txn.v1",
        "event_id": _event_id(),
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "rail": spec.rail.value,
        "currency": "INR",
        "amount_minor": 2500000,
        "label_class": spec.economic_class.value,
        "label_family": spec.technique_id.value,
        "lifecycle_stage": stage,
        "attack_id": spec.vector_id,
        "generation": 0,
        "is_authorized_push": spec.is_authorized_push,
    }


def _auth_features(spec: AttackSpec, signals: dict[str, Any]) -> dict[str, Any]:
    """Map simulatable_signals into features_auth columns."""
    features: dict[str, Any] = {
        "device_hash": f"dev-{spec.vector_id[:8]}",
        "is_new_device": signals.get("device_hash_shift", False),
        "is_new_payee": signals.get("new_payee", False),
        "account_age_days": signals.get("mule_account_age_days", signals.get("seasoning_days", 30)),
        "seasoning_txn_count": signals.get("seasoning_txn_count", 0),
        "fan_in_1h": signals.get("fan_in_1h", 0),
        "call_active_flag": signals.get("call_active_flag", False),
        "copy_paste_payee_flag": signals.get("copy_paste_payee_flag", False),
        "pause_ms": signals.get("pause_ms", 0),
        "urgency_pressure": signals.get("urgency_pressure", 0.0),
        "liveness_score": signals.get("liveness_score", 1.0),
        "doc_consistency": signals.get("doc_consistency", 1.0),
        "beneficiary_changed": signals.get("beneficiary_changed", False),
        "gstin_checksum_ok": signals.get("gstin_checksum_ok", True),
        "lookalike_domain_flag": signals.get("lookalike_domain_flag", False),
    }
    return features


def run_injector(spec: AttackSpec, lifecycle_stage: str | None = None) -> dict[str, Any]:
    """
    Apply one catalog row to a minimal synthetic ledger event.
    Injector id is source of truth; signals come from catalog only.
    """
    if spec.generate_mode.value != "generate" or not spec.simulator:
        raise ValueError(f"vector {spec.vector_id} is not generate-eligible")

    injector_id = spec.simulator.injector_id
    signals = dict(spec.simulatable_signals or {})
    envelope = _base_envelope(spec, lifecycle_stage)
    envelope["features_auth"] = _auth_features(spec, signals)
    envelope["injector_id"] = injector_id
    envelope["simulatable_signals"] = signals

    perturbation: dict[str, Any] = {"injector_id": injector_id}
    if injector_id == "graph_mule":
        perturbation["graph"] = {
            "fan_in_1h": signals.get("fan_in_1h"),
            "fan_out_ttl_hours": signals.get("fan_out_ttl_hours"),
            "hop_rails": signals.get("hop_rails"),
            "cashout_sink": signals.get("cashout_mcc_or_sink"),
        }
    elif injector_id == "identity_trajectory":
        perturbation["identity"] = {
            "seasoning_days": signals.get("seasoning_days"),
            "liveness_score": signals.get("liveness_score"),
            "kyc_tier": signals.get("kyc_tier"),
        }
    elif injector_id == "app_session":
        perturbation["session"] = {
            "persuasion_labels": signals.get("persuasion_labels"),
            "call_active": signals.get("call_active_flag"),
            "copy_paste_payee": signals.get("copy_paste_payee_flag"),
        }
    elif injector_id == "doc_beneficiary":
        perturbation["invoice"] = {
            "beneficiary_changed": signals.get("beneficiary_changed"),
            "gstin_checksum_ok": signals.get("gstin_checksum_ok"),
        }

    return {
        "vector_id": spec.vector_id,
        "technique_id": spec.technique_id.value,
        "injector_id": injector_id,
        "lifecycle_stage": envelope["lifecycle_stage"],
        "ledger_event": envelope,
        "perturbation": perturbation,
    }
