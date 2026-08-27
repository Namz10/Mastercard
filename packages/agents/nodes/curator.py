"""Curator node — rank candidates before expensive extract."""

from packages.agents.limits import resolve_limit, take
from packages.agents.llm.curator import rank_candidates
from packages.agents.settings import get_identify_settings
from packages.agents.state import IdentifyState


def curator(state: IdentifyState) -> IdentifyState:
    settings = get_identify_settings()
    candidates = list(state.get("candidate_urls") or [])
    errors = list(state.get("errors") or [])

    state["scout_candidate_count"] = len(candidates)

    if not candidates:
        state["candidate_urls"] = []
        state["curator_kept_count"] = 0
        state["errors"] = errors
        return state

    ranked, fallback = rank_candidates(candidates, topic=(state.get("topic") or ""))
    if fallback:
        errors.append(fallback)

    max_docs = resolve_limit(settings.identify_max_docs)
    kept = take(ranked, max_docs)

    state["candidate_urls"] = kept
    state["curator_kept_count"] = len(kept)
    state["errors"] = errors
    return state
