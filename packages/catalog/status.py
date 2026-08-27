"""Single Atlas status authority."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from apps.api.models import AtlasRow
from packages.catalog.models import AttackSpec, Status

LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    Status.proposed.value: frozenset(
        {Status.open.value, Status.rejected.value, Status.rejected_unsafe.value}
    ),
    Status.open.value: frozenset(
        {Status.generating.value, Status.defending.value, Status.rejected.value}
    ),
    Status.generating.value: frozenset({Status.defending.value, Status.open.value}),
    Status.defending.value: frozenset(
        {Status.open.value, Status.solved.value, Status.generating.value}
    ),
    Status.solved.value: frozenset(),
    Status.rejected.value: frozenset(),
    Status.rejected_unsafe.value: frozenset(),
}


class IllegalStatusTransition(ValueError):
    """Raised when an Atlas row would jump to a disallowed status."""


def assert_legal_transition(current: str, target: str) -> None:
    if current == target:
        return
    allowed = LEGAL_TRANSITIONS.get(current)
    if allowed is None:
        raise IllegalStatusTransition(f"unknown current status: {current}")
    if target not in allowed:
        raise IllegalStatusTransition(f"illegal status transition: {current} -> {target}")


def transition_atlas_status(
    db: Session,
    vector_id: str,
    status: str,
    spec_patch: dict[str, Any] | None = None,
    *,
    validate_spec: bool = True,
) -> AtlasRow:
    """Apply a legal status change; optionally merge and Pydantic-validate the spec."""
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
    if not row:
        raise KeyError(f"vector_id not found: {vector_id}")

    Status(status)
    assert_legal_transition(row.status, status)

    merged = dict(row.spec or {})
    if spec_patch:
        merged.update(spec_patch)
    merged["status"] = status
    merged.setdefault("vector_id", row.vector_id)

    if validate_spec:
        spec = AttackSpec.model_validate(merged)
        payload = spec.model_dump(mode="json")
        row.technique_id = spec.technique_id.value
        row.name = spec.name
        row.status = spec.status.value
        row.confidence_level = spec.confidence_level.value
        row.source_tier = spec.source_tier
        row.generate_mode = spec.generate_mode.value
        row.category = spec.category
        row.spec = payload
    else:
        row.status = status
        row.spec = merged
        if "name" in merged:
            row.name = merged["name"]
        if "confidence_level" in merged:
            row.confidence_level = merged["confidence_level"]

    db.commit()
    db.refresh(row)
    return row
