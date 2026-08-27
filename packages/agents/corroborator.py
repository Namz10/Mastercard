"""Corroboration rules (Plan 01 §5)."""

import os
from datetime import UTC, datetime
from typing import Any

from packages.catalog.schemas import validate_simulatable_signals
from packages.osint.telemetry.greynoise import check_ip, qualifies_for_corroboration
from packages.osint.telemetry.indicators import indicator_lookup_ip

NETWORK_TECHNIQUES = {"T01", "T02", "T03", "T04", "T05", "T07"}
CARD_TESTING_CONTROLS = {"card-testing", "stuffing", "scanning"}


def classify_vector(spec: dict[str, Any]) -> str:
    modality = spec.get("genai_modality", "")
    technique_id = spec.get("technique_id", "")
    controls = set(spec.get("control_bypassed") or [])

    if modality == "bot" or technique_id in NETWORK_TECHNIQUES:
        return "network_footprint"
    if controls & CARD_TESTING_CONTROLS:
        return "network_footprint"
    return "human_social"


def _max_greynoise_lookups_per_spec() -> int:
    raw = os.getenv("GREYNOISE_MAX_LOOKUPS_PER_SPEC", "3")
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def _telemetry_corroborate(spec: dict[str, Any]) -> dict[str, Any] | None:
    """GreyNoise lookup on sanitized network_indicators. No fake hits on miss."""
    indicators = spec.get("network_indicators") or []
    if not indicators or not os.getenv("GREYNOISE_API_KEY", ""):
        return None

    checked = 0
    limit = _max_greynoise_lookups_per_spec()
    seen_ips: set[str] = set()

    for indicator in indicators:
        if checked >= limit:
            break
        if not isinstance(indicator, dict):
            continue
        ip = indicator_lookup_ip(indicator)
        if not ip or ip in seen_ips:
            continue
        seen_ips.add(ip)
        checked += 1

        result = check_ip(ip)
        if result is None or not qualifies_for_corroboration(result):
            continue

        qualifier = "tags" if result.tags else "seen_only"
        return {
            "provider": "greynoise",
            "matched_indicator": {
                "type": indicator.get("type"),
                "value": indicator.get("value"),
                "role": indicator.get("role"),
            },
            "lookup_ip": ip,
            "greynoise_seen": result.seen,
            "greynoise_noise": result.noise,
            "greynoise_tags": result.tags,
            "greynoise_classification": result.classification,
            "qualifier": qualifier,
            "lookup_at": datetime.now(UTC).isoformat(),
            "indicators_checked": checked,
            "indicators_eligible": len(indicators),
        }
    return None


def apply_corroboration(spec: dict[str, Any]) -> dict[str, Any]:
    vector_class = classify_vector(spec)
    spec["vector_class"] = vector_class
    confidence = spec.get("confidence_level", "reported-unverified")

    if vector_class == "human_social":
        spec.pop("network_indicators", None)
        if confidence == "confirmed":
            spec["corroboration_type"] = "documentary-case"
        else:
            spec["corroboration_type"] = "not-yet-corroborated"
    else:
        evidence = _telemetry_corroborate(spec)
        if evidence:
            spec["corroboration_type"] = "network-telemetry"
            spec["corroboration_evidence"] = evidence
        elif confidence == "confirmed":
            spec["corroboration_type"] = "documentary-case"
        else:
            spec["corroboration_type"] = "not-yet-corroborated"

    canary = (
        confidence == "confirmed"
        and int(spec.get("source_tier", 5)) <= 2
        and spec.get("generate_mode") == "generate"
    )
    if canary and spec.get("simulator") and spec.get("simulatable_signals"):
        try:
            injector_id = spec["simulator"].get("injector_id", "")
            validate_simulatable_signals(injector_id, spec["simulatable_signals"])
            spec["canary_eligible"] = True
        except (ValueError, KeyError):
            spec["canary_eligible"] = False
    else:
        spec["canary_eligible"] = False

    return spec
