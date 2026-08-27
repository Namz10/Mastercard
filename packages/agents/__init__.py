"""LangGraph agent graphs — import submodules directly (e.g. identify_graph)."""

__all__ = ["compile_identify_graph", "identify_graph", "run_identify_graph"]


def __getattr__(name: str):
    if name in __all__:
        from packages.agents.identify_graph import compile_identify_graph, identify_graph, run_identify_graph

        return {
            "compile_identify_graph": compile_identify_graph,
            "identify_graph": identify_graph,
            "run_identify_graph": run_identify_graph,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
