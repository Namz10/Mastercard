"""TierScorer node."""

from packages.agents.state import IdentifyState
from packages.agents.tier_scorer import score_spec_sources


def tier_scorer(state: IdentifyState) -> IdentifyState:
    scored = [score_spec_sources(dict(s)) for s in state.get("proposed_specs") or []]
    state["proposed_specs"] = scored
    return state
