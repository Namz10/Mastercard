"""Librarian node — stage proposed rows in Postgres for HITL."""

from packages.agents.librarian_db import find_merge_target, hitl_payload_for_spec, merge_proposed_spec
from packages.agents.state import IdentifyState
from apps.api.db import SessionLocal


def librarian(state: IdentifyState) -> IdentifyState:
    specs = state.get("proposed_specs") or []
    hitl_queue: list[dict] = []
    db = SessionLocal()
    try:
        for spec in specs[:3]:
            technique_id = str(spec.get("technique_id", ""))
            target = find_merge_target(db, technique_id)
            depth_bump = target is not None
            target_id = target.vector_id if target else None

            if depth_bump and target:
                urls = list(spec.get("source_urls") or [])
                existing_urls = (target.spec or {}).get("source_urls") or []
                merged_urls = list(dict.fromkeys([*existing_urls, *urls]))
                spec = {**spec, "source_urls": merged_urls}

            merge_proposed_spec(
                db,
                spec,
                depth_bump=depth_bump,
                target_vector_id=target_id,
            )
            hitl_queue.append(
                hitl_payload_for_spec(
                    {**spec, "vector_id": target_id or spec.get("vector_id")},
                    nearest_technique=technique_id,
                )
            )
    finally:
        db.close()

    state["hitl_required"] = len(hitl_queue) > 0
    state["hitl_queue"] = hitl_queue
    return state
