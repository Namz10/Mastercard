"""Shared pytest setup — real Postgres, no Librarian mocks."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from apps.api.env import load_project_env

load_project_env()


@pytest.fixture(autouse=True)
def _isolate_llm_env(monkeypatch):
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
