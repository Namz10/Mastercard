"""identify_graph tests."""

import os
from unittest.mock import patch

import pytest

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


def test_run_on_fixtures(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    monkeypatch.setenv("QDRANT_DISABLED", "true")
    monkeypatch.setenv("EMBEDDINGS_DISABLED", "true")
    with patch("packages.agents.nodes.librarian.merge_proposed_spec"):
        result = run_identify_graph(run_id="batch2-test")
    assert result["run_id"] == "batch2-test"
    assert isinstance(result.get("candidate_urls", []), list)
    assert isinstance(result.get("proposed_specs", []), list)


def test_invoke_with_empty_state(monkeypatch):
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    monkeypatch.setenv("QDRANT_DISABLED", "true")
    monkeypatch.setenv("EMBEDDINGS_DISABLED", "true")
    state = empty_identify_state("invoke-test")
    with patch("packages.agents.nodes.librarian.merge_proposed_spec"):
        out = identify_graph.invoke(state)
    assert out["run_id"] == "invoke-test"


def test_node_order_locked():
    assert NODE_ORDER == (
        "scout",
        "extractor",
        "grounder",
        "tier_scorer",
        "corroborator",
        "librarian",
    )
