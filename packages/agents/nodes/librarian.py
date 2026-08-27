"""Librarian node — stage proposed rows in Postgres for HITL."""

from apps.api.db import SessionLocal, init_db
from packages.agents.limits import resolve_limit, take
from packages.agents.librarian_db import find_merge_target, hitl_payload_for_spec, merge_proposed_spec
from packages.agents.settings import get_identify_settings
from packages.agents.state import IdentifyState
from packages.osint.vector_store import nearest_catalog_row


def librarian(state: IdentifyState) -> IdentifyState:
    init_db()
    settings = get_identify_settings()
    specs = state.get("proposed_specs") or []
    hitl_limit = resolve_limit(settings.identify_max_hitl)
    specs_to_stage = take(specs, hitl_limit)
    hitl_queue: list[dict] = []
    errors = list(state.get("errors") or [])
    db = SessionLocal()
    try:
        for spec in specs_to_stage:
            nearest = nearest_catalog_row(
                str(spec.get("name") or ""),
                str(spec.get("rail") or ""),
                str(spec.get("technique_id") or ""),
            )
            target = find_merge_target(db, spec)
            # Only merge into an existing *proposed* row. Never demote open catalog cards.
            depth_bump = target is not None and target.status == "proposed"
            target_id = target.vector_id if depth_bump else None
            nearest_spec = None
            if target and target.spec:
                nearest_spec = dict(target.spec)
            elif nearest:
                from apps.api.models import AtlasRow

                nrow = db.query(AtlasRow).filter(AtlasRow.vector_id == nearest["vector_id"]).one_or_none()
                if nrow:
                    nearest_spec = dict(nrow.spec or {})

            if depth_bump and target:
                urls = list(spec.get("source_urls") or [])
                existing_urls = (target.spec or {}).get("source_urls") or []
                merged_urls = list(dict.fromkeys([*existing_urls, *urls]))
                spec = {**spec, "source_urls": merged_urls}

            row = merge_proposed_spec(
                db,
                spec,
                depth_bump=depth_bump,
                target_vector_id=target_id,
            )
            hitl_queue.append(
                hitl_payload_for_spec(
                    {**spec, "vector_id": row.vector_id},
                    nearest_technique=str((nearest_spec or spec).get("technique_id", "")),
                    nearest_spec=nearest_spec,
                )
            )
    finally:
        db.close()

    state["errors"] = errors
    state["hitl_required"] = len(hitl_queue) > 0
    state["hitl_queue"] = hitl_queue
    return state
