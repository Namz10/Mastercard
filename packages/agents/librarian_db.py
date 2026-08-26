"""Postgres Atlas merge for proposed / open rows."""

from typing import Any

from sqlalchemy.orm import Session

from apps.api.models import AtlasRow
from packages.catalog.models import AttackSpec


def merge_proposed_spec(
    db: Session,
    spec_dict: dict[str, Any],
    depth_bump: bool = False,
    target_vector_id: str | None = None,
) -> AtlasRow:
    """Upsert atlas row; default status proposed."""
    if target_vector_id:
        spec_dict = {**spec_dict, "vector_id": target_vector_id}

    spec = AttackSpec.model_validate(spec_dict)
    if spec.status.value != "proposed":
        spec_dict = {**spec_dict, "status": "proposed"}
        spec = AttackSpec.model_validate(spec_dict)

    row = db.query(AtlasRow).filter(AtlasRow.vector_id == spec.vector_id).one_or_none()
    if row and depth_bump:
        existing = row.spec or {}
        notes = existing.get("novelty_notes") or ""
        spec_dict = {**spec_dict, "novelty_notes": (notes + " | depth_bump").strip()}
        spec = AttackSpec.model_validate(spec_dict)

    payload = spec.model_dump(mode="json")
    if row:
        row.technique_id = spec.technique_id.value
        row.name = spec.name
        row.status = spec.status.value
        row.confidence_level = spec.confidence_level.value
        row.source_tier = spec.source_tier
        row.generate_mode = spec.generate_mode.value
        row.category = spec.category
        row.spec = payload
    else:
        row = AtlasRow(
            vector_id=spec.vector_id,
            technique_id=spec.technique_id.value,
            name=spec.name,
            status=spec.status.value,
            confidence_level=spec.confidence_level.value,
            source_tier=spec.source_tier,
            generate_mode=spec.generate_mode.value,
            category=spec.category,
            spec=payload,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_atlas_status(db: Session, vector_id: str, status: str, spec_patch: dict | None = None) -> AtlasRow:
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
    if not row:
        raise KeyError(f"vector_id not found: {vector_id}")
    row.status = status
    merged = dict(row.spec or {})
    merged["status"] = status
    if spec_patch:
        merged.update(spec_patch)
    row.spec = merged
    if "name" in merged:
        row.name = merged["name"]
    if "confidence_level" in merged:
        row.confidence_level = merged["confidence_level"]
    db.commit()
    db.refresh(row)
    return row


def find_merge_target(db: Session, technique_id: str) -> AtlasRow | None:
    """Prefer merging new OSINT evidence into an existing catalog row (depth bump)."""
    rows = (
        db.query(AtlasRow)
        .filter(AtlasRow.technique_id == technique_id)
        .order_by(AtlasRow.status)
        .all()
    )
    if not rows:
        return None
    for row in rows:
        if row.status == "open":
            return row
    return rows[0]


def hitl_payload_for_spec(spec: dict[str, Any], nearest_technique: str | None = None) -> dict[str, Any]:
    return {
        "vector_id": spec.get("vector_id"),
        "technique_id": spec.get("technique_id"),
        "nearest_technique_id": nearest_technique or spec.get("technique_id"),
        "tier_badges": [spec.get("source_tier")],
        "source_urls": spec.get("source_urls"),
        "vector_class": spec.get("vector_class"),
        "generate_mode": spec.get("generate_mode"),
        "simulatable_signals_preview": spec.get("simulatable_signals"),
        "confidence_level": spec.get("confidence_level"),
        "corroboration_type": spec.get("corroboration_type"),
        "name": spec.get("name"),
    }
