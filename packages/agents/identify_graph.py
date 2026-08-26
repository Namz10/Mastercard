"""Linear identify_graph with full Identify pipeline nodes."""

import uuid

from langgraph.graph import END, START, StateGraph

from packages.agents.nodes import (
    corroborator,
    extractor,
    grounder,
    librarian,
    scout,
    tier_scorer,
)
from packages.agents.state import IdentifyState, empty_identify_state

NODE_ORDER = (
    "scout",
    "extractor",
    "grounder",
    "tier_scorer",
    "corroborator",
    "librarian",
)


def build_identify_graph() -> StateGraph:
    graph = StateGraph(IdentifyState)
    graph.add_node("scout", scout)
    graph.add_node("extractor", extractor)
    graph.add_node("grounder", grounder)
    graph.add_node("tier_scorer", tier_scorer)
    graph.add_node("corroborator", corroborator)
    graph.add_node("librarian", librarian)

    graph.add_edge(START, "scout")
    graph.add_edge("scout", "extractor")
    graph.add_edge("extractor", "grounder")
    graph.add_edge("grounder", "tier_scorer")
    graph.add_edge("tier_scorer", "corroborator")
    graph.add_edge("corroborator", "librarian")
    graph.add_edge("librarian", END)
    return graph


def compile_identify_graph():
    return build_identify_graph().compile()


identify_graph = compile_identify_graph()


def run_identify_graph(run_id: str | None = None, topic: str = "") -> IdentifyState:
    """Run full Identify pipeline (airplane or live per env)."""
    rid = run_id or f"identify-{uuid.uuid4().hex[:12]}"
    return identify_graph.invoke(empty_identify_state(run_id=rid, topic=topic))
