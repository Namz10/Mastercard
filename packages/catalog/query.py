"""Atlas query helpers for Generate and Defend consumers."""

from typing import Any

from sqlalchemy.orm import Session

from apps.api.models import AtlasRow
from packages.catalog.models import AttackSpec, GenerateMode, Status

GENERATE_STATUSES = frozenset({Status.open.value, Status.generating.value})


def atlas_row_to_spec(row: AtlasRow) -> AttackSpec:
    payload = dict(row.spec or {})
    payload.setdefault("vector_id", row.vector_id)
    return AttackSpec.model_validate(payload)


def list_generate_eligible(
    db: Session,
    statuses: frozenset[str] = GENERATE_STATUSES,
    limit: int = 50,
) -> list[AttackSpec]:
    """Rows Generate population mode may sample."""
    rows = (
        db.query(AtlasRow)
        .filter(AtlasRow.status.in_(sorted(statuses)))
        .filter(AtlasRow.generate_mode == GenerateMode.generate.value)
        .order_by(AtlasRow.technique_id, AtlasRow.vector_id)
        .limit(limit)
        .all()
    )
    return [atlas_row_to_spec(r) for r in rows]


def get_spec_by_vector_id(db: Session, vector_id: str) -> AttackSpec | None:
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
    if not row:
        return None
    return atlas_row_to_spec(row)


def list_canary_eligible(db: Session, limit: int = 20) -> list[AttackSpec]:
    specs = list_generate_eligible(db, limit=limit)
    return [s for s in specs if s.canary_eligible]


def list_open_specs(db: Session, limit: int = 100) -> list[AttackSpec]:
    rows = (
        db.query(AtlasRow)
        .filter(AtlasRow.status == Status.open.value)
        .order_by(AtlasRow.technique_id)
        .limit(limit)
        .all()
    )
    return [atlas_row_to_spec(r) for r in rows]


def specs_by_technique(db: Session) -> dict[str, list[AttackSpec]]:
    rows = db.query(AtlasRow).order_by(AtlasRow.technique_id, AtlasRow.vector_id).all()
    out: dict[str, list[AttackSpec]] = {}
    for row in rows:
        out.setdefault(row.technique_id, []).append(atlas_row_to_spec(row))
    return out


def set_atlas_status(db: Session, vector_id: str, status: str) -> AtlasRow:
    row = db.query(AtlasRow).filter(AtlasRow.vector_id == vector_id).one_or_none()
    if not row:
        raise KeyError(f"vector_id not found: {vector_id}")
    row.status = status
    merged = dict(row.spec or {})
    merged["status"] = status
    row.spec = merged
    db.commit()
    db.refresh(row)
    return row
