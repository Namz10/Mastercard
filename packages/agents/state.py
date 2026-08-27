"""Shared state for identify_graph."""

from typing import Any, TypedDict


class IdentifyState(TypedDict, total=False):
    run_id: str
    topic: str
    candidate_urls: list[dict[str, Any]]
    extracted_docs: list[dict[str, Any]]
    proposed_specs: list[dict[str, Any]]
    hitl_required: bool
    hitl_queue: list[dict[str, Any]]
    errors: list[str]


def empty_identify_state(run_id: str = "local-run", topic: str = "") -> IdentifyState:
    return {
        "run_id": run_id,
        "topic": topic,
        "candidate_urls": [],
        "extracted_docs": [],
        "proposed_specs": [],
        "hitl_required": False,
        "hitl_queue": [],
        "errors": [],
    }
