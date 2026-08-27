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

_SCHEMAS = {"AttackExtract": ATTACK_EXTRACT_SCHEMA, "CuratorRank": CURATOR_RANK_SCHEMA}


def get_json_schema(schema_name: str) -> dict:
    if schema_name not in _SCHEMAS:
        raise LlmConfigurationError(f"Unknown schema name: {schema_name!r}")
    return dict(_SCHEMAS[schema_name])
