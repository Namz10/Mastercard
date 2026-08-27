"""Loop C — coverage map: 24 techniques × rule coverage status."""

from typing import Any

from sqlalchemy.orm import Session

from packages.catalog.features import normalize_feature_names
from packages.catalog.models import AttackSpec, GenerateMode, TechniqueId
from packages.catalog.query import specs_by_technique
from packages.policy.loop_i import draft_rule_from_spec
from packages.policy.rules import load_v0_rules, match_rules_to_features

CoverageStatus = str  # live_rule | draft_rule | named_gap | case_only | empty


def _primary_spec(specs: list[AttackSpec]) -> AttackSpec | None:
    """Prefer canary-eligible / richest open row when a technique has variants."""
    if not specs:
        return None
    pool = [s for s in specs if s.status.value == "open"] or list(specs)
    return max(
        pool,
        key=lambda s: (
            s.canary_eligible,
            len(normalize_feature_names(list(s.features_expected or []))),
            s.confidence_level.value == "confirmed",
            s.vector_id,
        ),
    )


def _coverage_for_spec(spec: AttackSpec, v0_rules: list) -> dict[str, Any]:
    features = normalize_feature_names(list(spec.features_expected or []))
    live_matches = match_rules_to_features(features, v0_rules)
    loop_i = draft_rule_from_spec(spec)

    if live_matches:
        status: CoverageStatus = "live_rule"
        rule_ids = [r.id for r in live_matches]
        gap_reason = None
    elif loop_i["coverage_status"] == "draft_rule":
        status = "draft_rule"
        rule_ids = [loop_i["draft_rule"]["id"]]
        gap_reason = None
    elif loop_i["coverage_status"] == "named_gap":
        status = "named_gap"
        rule_ids = []
        gap_reason = loop_i["named_gap_reason"]
    elif loop_i["coverage_status"] == "case_only":
        status = "case_only"
        rule_ids = []
        gap_reason = loop_i["named_gap_reason"]
    else:
        status = "empty"
        rule_ids = []
        gap_reason = None

    return {
        "technique_id": spec.technique_id.value,
        "vector_id": spec.vector_id,
        "name": spec.name,
        "status": spec.status.value,
        "generate_mode": spec.generate_mode.value,
        "coverage_status": status,
        "live_rule_ids": rule_ids,
        "named_gap_reason": gap_reason,
        "draft_rule": loop_i.get("draft_rule"),
        "features_expected": features,
        "scout_topic_hint": _scout_hint(spec, status, gap_reason),
    }


def _scout_hint(spec: AttackSpec, status: str, gap_reason: str | None) -> str | None:
    if status in {"live_rule", "draft_rule"}:
        return None
    if gap_reason == "merchant_collusion_requires_merchant_nodes":
        return "synthetic merchant collusion payment fraud"
    if spec.technique_id.value in {"T07", "T22", "T23"}:
        return f"card fraud {spec.name} regulator alert"
    if status in {"named_gap", "case_only", "empty"}:
        return f"{spec.name} payment fraud India regulator"
    return None


def build_coverage_map(db: Session) -> dict[str, Any]:
    """24 techniques × coverage cell for Loop C UI."""
    by_technique = specs_by_technique(db)
    v0_rules = load_v0_rules()
    cells: list[dict[str, Any]] = []
    gap_topics: list[str] = []

    for tid in sorted(TechniqueId, key=lambda t: t.value):
        specs = by_technique.get(tid.value, [])
        if not specs:
            cells.append(
                {
                    "technique_id": tid.value,
                    "vector_id": None,
                    "name": None,
                    "status": None,
                    "generate_mode": None,
                    "coverage_status": "empty",
                    "live_rule_ids": [],
                    "named_gap_reason": "no_catalog_row",
                    "draft_rule": None,
                    "features_expected": [],
                    "scout_topic_hint": f"{tid.value} payment fraud typology",
                }
            )
            gap_topics.append(f"{tid.value} payment fraud typology")
            continue

        spec = _primary_spec(specs)
        if not spec:
            continue
        cell = _coverage_for_spec(spec, v0_rules)
        cells.append(cell)
        if cell["scout_topic_hint"]:
            gap_topics.append(cell["scout_topic_hint"])

    status_counts: dict[str, int] = {}
    for cell in cells:
        st = cell["coverage_status"]
        status_counts[st] = status_counts.get(st, 0) + 1

    return {
        "technique_count": len(cells),
        "cells": cells,
        "status_counts": status_counts,
        "scout_topics_for_gaps": list(dict.fromkeys(gap_topics)),
    }


def scout_topics_from_gaps(db: Session, max_topics: int = 5) -> list[str]:
    return build_coverage_map(db)["scout_topics_for_gaps"][:max_topics]
