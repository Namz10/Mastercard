# Phase 1a evidence (2026-08-27)

## Commands run

- `uv lock` / `uv sync --extra dev`
- `docker compose up -d postgres --wait` (`pgvector/pgvector:pg16`)
- `pytest tests/ -q -m "not live_llm"` → **65 passed**, 1 skipped (`live_llm`), 1 deselected
- `python apps/api/seed.py --reset` → **29** atlas rows
- Identify after seed (unmocked Librarian): `identify OK validate-all` **2** proposed specs

## Product path

- Datastore is Postgres + pgvector only (no Qdrant).
- Librarian persists proposed rows; `make validate-all` does not patch `merge_proposed_spec`.
- Default LLM profile is OmniRoute; without `AEGIS_LLM_API_KEY`, fixture rules or abstain.
- Weak articles abstain. RBI fixture is not FinCEN body.
- `./run.sh` / `./run.sh --validate` is the end-to-end entrypoint.

## Deferred (1b)

- `kb_search` / `kb_get_chunk` / `upsert_taxonomy`
- LangGraph checkpoint / interrupt HITL
- Frozen Identify eval corpus
- Coverage/mutation score blockers
