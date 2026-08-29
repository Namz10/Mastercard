"""JSON schema for Identify extraction."""

from __future__ import annotations

from packages.agents.llm.errors import LlmConfigurationError

ATTACK_EXTRACT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
    "required": ["technique_id", "name"],
    "properties": {
        "vector_id": {"type": "string"},
        "technique_id": {"type": "string"},
        "name": {"type": "string"},
        "one_liner": {"type": "string"},
        "category": {"type": "integer"},
        "rail": {"type": "string"},
        "lifecycle_stage": {"type": "string"},
        "genai_modality": {"type": "string"},
        "social_surface": {"type": "string"},
        "control_bypassed": {"type": "array", "items": {"type": "string"}},
        "actor_type": {"type": "string"},
        "economic_class": {"type": "string"},
        "is_authorized_push": {"type": "boolean"},
        "generate_mode": {"type": "string"},
        "source_urls": {"type": "array", "items": {"type": "string"}},
        "simulatable_signals": {"type": "object"},
        "simulator": {"type": "object"},
    },
}

CURATOR_RANK_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": True,
    "required": ["rankings"],
    "properties": {
        "rankings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "url": {"type": "string"},
                    "relevance_score": {"type": "integer"},
                    "predicted_technique_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
}

# Phase 8 — Loop T remediation-cycle decision (one review pass, fail-closed).
REMEDIATION_DECISION_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "reason", "items", "in_focus_families", "error"],
    "properties": {
        "verdict": {"type": "string", "enum": ["stop", "defer", "submit"]},
        "reason": {"type": "string"},
        "items": {
            "type": "array",
            "maxItems": 7,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action", "rule_id", "kind", "applies_to", "family", "when", "reason"],
                "properties": {
                    "action": {"type": "string", "enum": ["press", "calm_down", "fn"]},
                    "rule_id": {"type": "string"},
                    "kind": {"type": "string", "enum": ["hard_flag", "calm_down"]},
                    "applies_to": {"type": "string"},
                    "family": {"type": ["string", "null"]},
                    "when": {"type": ["array", "null"], "items": {"type": "string"}},
                    "reason": {"type": "string"},
                },
            },
        },
        "in_focus_families": {
            "type": "array",
            "items": {"type": "string"},
        },
        "reviewer_capacity_hint": {"type": "integer"},
        "error": {"type": ["string", "null"]},
    },
}

_SCHEMAS = {
    "AttackExtract": ATTACK_EXTRACT_SCHEMA,
    "CuratorRank": CURATOR_RANK_SCHEMA,
    "RemediationDecision": REMEDIATION_DECISION_SCHEMA,
}


def get_json_schema(schema_name: str) -> dict:
    if schema_name not in _SCHEMAS:
        raise LlmConfigurationError(f"Unknown schema name: {schema_name!r}")
    return dict(_SCHEMAS[schema_name])
