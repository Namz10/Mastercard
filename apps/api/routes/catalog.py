"""Catalog / KillChain Atlas routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from apps.api.db import get_db
from apps.api.models import AtlasRow

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("")
def list_catalog(
    db: Annotated[Session, Depends(get_db)],
    status: str | None = Query(None),
    technique_id: str | None = Query(None),
) -> dict:
    q = db.query(AtlasRow)
    if status:
        q = q.filter(AtlasRow.status == status)
    if technique_id:
        q = q.filter(AtlasRow.technique_id == technique_id)
    rows = q.order_by(AtlasRow.technique_id, AtlasRow.vector_id).all()
    return {
        "count": len(rows),
        "items": [row.spec for row in rows],
    }


@router.get("/threat-map")
def threat_map(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Technique chips grouped by category (API for future threat-map UI)."""
    rows = db.query(AtlasRow).order_by(AtlasRow.technique_id).all()
    by_technique: dict[str, list] = {}
    for row in rows:
        by_technique.setdefault(row.technique_id, []).append(
            {
                "vector_id": row.vector_id,
                "technique_id": row.technique_id,
                "name": row.name,
                "status": row.status,
                "confidence_level": row.confidence_level,
                "source_tier": row.source_tier,
                "generate_mode": row.generate_mode,
                "category": row.category,
            }
        )

    categories = {1: [], 2: [], 3: [], 4: [], 5: []}
    for technique_id in sorted(by_technique.keys()):
        chips = by_technique[technique_id]
        primary = chips[0]
        cat = primary["category"]
        categories[cat].append(
            {
                "technique_id": technique_id,
                "name": primary["name"],
                "status": primary["status"],
                "confidence_level": primary["confidence_level"],
                "source_tier": primary["source_tier"],
                "generate_mode": primary["generate_mode"],
                "variants": len(chips),
                "chips": chips,
            }
        )

    return {"categories": categories, "technique_count": len(by_technique)}
