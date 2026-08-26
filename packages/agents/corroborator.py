"""Corroboration rules (Plan 01 §5)."""

import os
from typing import Any

import httpx

from packages.catalog.schemas import validate_simulatable_signals

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


def _greynoise_lookup(ip_hint: str | None = None) -> bool:
    """Optional GreyNoise — network footprint only. No fake hits on miss."""
    api_key = os.getenv("GREYNOISE_API_KEY", "")
    if not api_key:
        return False
    # v1: no IP from OSINT text; skip live call unless configured for demo IP
    demo_ip = os.getenv("GREYNOISE_DEMO_IP", "")
    if not demo_ip:
        return False
    try:
        url = f"https://api.greynoise.io/v3/community/{demo_ip}"
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url, headers={"key": api_key})
            return r.status_code == 200 and (r.json().get("seen") or False)
    except httpx.HTTPError:
        return False


def apply_corroboration(spec: dict[str, Any]) -> dict[str, Any]:
    vector_class = classify_vector(spec)
    spec["vector_class"] = vector_class
    confidence = spec.get("confidence_level", "reported-unverified")

    if vector_class == "human_social":
        if confidence == "confirmed":
            spec["corroboration_type"] = "documentary-case"
        else:
            spec["corroboration_type"] = "not-yet-corroborated"
    else:
        if _greynoise_lookup():
            spec["corroboration_type"] = "network-telemetry"
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
