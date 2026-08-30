"""Postgres Atlas merge for proposed / open rows."""

from typing import Any

from sqlalchemy.orm import Session

from apps.api.models import AtlasRow
from packages.catalog.models import AttackSpec
from packages.catalog.status import transition_atlas_status
from packages.osint.vector_store import DEDUP_THRESHOLD, nearest_catalog_row, register_catalog_embedding


def proposal_dedupe_key(spec: dict[str, Any]) -> tuple[str, str, str]:
    """Stable identity for HITL rows — technique, normalized name, rail."""
    return (
        str(spec.get("technique_id") or "").strip().upper(),
        str(spec.get("name") or "").strip().lower(),
        str(spec.get("rail") or "").strip().lower(),
    )


def dedupe_atlas_rows(rows: list[AtlasRow]) -> list[AtlasRow]:
    """Keep the first row per proposal identity (caller should pass newest-first)."""
    seen: set[tuple[str, str, str]] = set()
    out: list[AtlasRow] = []
    for row in rows:
        key = proposal_dedupe_key(row.spec or {})
        if not key[0] or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def merge_proposed_spec(
    db: Session,
    spec_dict: dict[str, Any],
    depth_bump: bool = False,
    target_vector_id: str | None = None,
) -> AtlasRow:
    """Upsert atlas row; default status proposed."""
    if target_vector_id:
        spec_dict = {**spec_dict, "vector_id": target_vector_id}

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
    register_catalog_embedding(
        spec.name,
        spec.rail.value,
        spec.technique_id.value,
        vector_id=spec.vector_id,
    )
    return row


def set_atlas_status(db: Session, vector_id: str, status: str, spec_patch: dict | None = None) -> AtlasRow:
    return transition_atlas_status(db, vector_id, status, spec_patch, validate_spec=True)


def find_merge_target(
    db: Session,
    spec: dict[str, Any],
) -> AtlasRow | None:
    """Exact vector_id / dedupe key / name+rail+technique, then pgvector cosine ≥ 0.92."""
    vector_id = spec.get("vector_id")
    if vector_id:
        row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
        if row:
            return row

    key = proposal_dedupe_key(spec)
    if key[0]:
        for row in db.query(AtlasRow).filter(AtlasRow.technique_id == key[0]).all():
            if proposal_dedupe_key(row.spec or {}) == key:
                return row

    name = str(spec.get("name") or "")
    rail = str(spec.get("rail") or "")
    technique_id = str(spec.get("technique_id") or "")
    if name and rail and technique_id:
        exact = (
            db.query(AtlasRow)
            .filter(AtlasRow.technique_id == technique_id)
            .all()
        )
        for row in exact:
            payload = row.spec or {}
            if payload.get("name") == name and str(payload.get("rail")) == rail:
                return row

    nearest = nearest_catalog_row(name, rail, technique_id)
    if nearest and nearest["similarity"] >= DEDUP_THRESHOLD:
        return db.query(AtlasRow).filter(AtlasRow.vector_id == nearest["vector_id"]).one_or_none()
    return None


def spec_field_diff(proposed: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    if not existing:
        return {}
    keys = (
        "name",
        "technique_id",
        "rail",
        "generate_mode",
        "confidence_level",
        "source_tier",
        "one_liner",
    )
    diff: dict[str, Any] = {}
    for key in keys:
        left, right = proposed.get(key), existing.get(key)
        if left != right:
            diff[key] = {"existing": right, "proposed": left}
    return diff


def hitl_payload_for_spec(
    spec: dict[str, Any],
    nearest_technique: str | None = None,
    nearest_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "field_diff": spec_field_diff(spec, nearest_spec),
    }
