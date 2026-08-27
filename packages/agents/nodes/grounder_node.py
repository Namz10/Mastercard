"""Grounder node — filter proposed specs."""

from packages.agents.grounder import filter_proposed_specs
from packages.agents.state import IdentifyState


def grounder(state: IdentifyState) -> IdentifyState:
    specs = state.get("proposed_specs") or []
    body_by_url: dict[str, str] = {}
    for doc in state.get("extracted_docs") or []:
        url = doc.get("url", "")
        if url:
            body_by_url[url] = doc.get("text", "") or ""

    for c in state.get("candidate_urls") or []:
        url = c.get("url", "")
        if url and url not in body_by_url:
            body_by_url[url] = c.get("snippet", "")

    kept, errors = filter_proposed_specs(specs, body_by_url)
    state["proposed_specs"] = kept
    state.setdefault("errors", []).extend(errors)
    return state
