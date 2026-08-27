"""identify_graph tests against real Postgres (no Librarian mocks)."""

from packages.agents.identify_graph import (
    NODE_ORDER,
    build_identify_graph,
    identify_graph,
    run_identify_graph,
)
from packages.agents.state import empty_identify_state


def test_identify_graph_compiles():
    graph = build_identify_graph()
    compiled = graph.compile()
    assert compiled is not None


def test_module_level_graph_compiles():
    assert identify_graph is not None


def test_run_on_fixtures(postgres_required):
    result = run_identify_graph(run_id="batch2-test")
    assert result["run_id"] == "batch2-test"
    assert isinstance(result.get("candidate_urls", []), list)
    assert isinstance(result.get("proposed_specs", []), list)
    assert len(result["candidate_urls"]) >= 2
    assert len(result["proposed_specs"]) >= 1


def test_invoke_with_empty_state(postgres_required):
    state = empty_identify_state("invoke-test")
    out = identify_graph.invoke(state)
    assert out["run_id"] == "invoke-test"
    assert len(out.get("proposed_specs") or []) >= 1


def test_node_order_locked():
    assert NODE_ORDER == (
        "scout",
        "curator",
        "extractor",
        "grounder",
        "tier_scorer",
        "corroborator",
        "librarian",
    )
