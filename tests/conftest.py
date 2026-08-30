"""Shared pytest setup — real Postgres, no Librarian mocks."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from apps.api.env import load_project_env

load_project_env()


@pytest.fixture(autouse=True)
def _zero_fold_floor_for_fit_unit_tests(request, monkeypatch):
    """Small synthetic populations cannot meet v1 fold_floor_min=15."""
    nodeid = request.node.nodeid
    if not any(
        token in nodeid
        for token in ("test_eval_fit", "test_ml_validation", "test_post_g43_protocol")
    ):
        return
    from packages.eval import fit as fit_mod

    original = fit_mod.load_recipe

    def patched(path=None):
        recipe = dict(original(path))
        recipe["fold_floor_min"] = 0
        return recipe

    monkeypatch.setattr(fit_mod, "load_recipe", patched)


@pytest.fixture(autouse=True)
def _isolate_llm_env(request, monkeypatch):
    """Offline tests cannot see the operator's Groq/OmniRoute keys.

    Tests marked live_llm / live_identify keep the process .env so a configured
    provider actually runs (Plan 12 Phase 0.6).
    """
    markers = {m.name for m in request.node.iter_markers()}
    if markers & {"live_llm", "live_identify"}:
        return
    monkeypatch.setenv("IDENTIFY_LIVE_SEARCH", "false")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("AEGIS_LLM_API_KEY", raising=False)
    monkeypatch.setenv("AEGIS_LLM_PROFILE", "omniroute")
    monkeypatch.setenv("AEGIS_LLM_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("AEGIS_LLM_MODEL", "auto")
    monkeypatch.setenv("AEGIS_LLM_ALLOW_LOOPBACK_HTTP", "true")


@pytest.fixture(scope="session")
def postgres_required():
    from apps.api.db import engine, init_db

    try:
        init_db()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            ext = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
            if ext is None:
                pytest.fail("pgvector extension is not installed")
    except Exception as exc:
        pytest.fail(f"Postgres+pgvector is required for this suite: {exc}")
    return True
