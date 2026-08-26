"""Corroborator node."""

from packages.agents.corroborator import apply_corroboration
from packages.agents.state import IdentifyState


def corroborator(state: IdentifyState) -> IdentifyState:
    updated = [apply_corroboration(dict(s)) for s in state.get("proposed_specs") or []]
    state["proposed_specs"] = updated
    return state
