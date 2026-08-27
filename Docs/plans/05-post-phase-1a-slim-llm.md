# Post–Phase 1a — Agnostic LLM, slim install, then 1b

**Parent:** Phase 1 child plan (`04-phase-1-provider-baseline-identify.md`)

**Do not start Generate, Defend scoring, or the web app here.**

## Status

**1a is done.** Identify runs against real Postgres + pgvector; Librarian is unmocked; OmniRoute is the default LLM *profile*; `./run.sh` exists.

**Entire Phase 1 is not done.** 1b remains: knowledge-base tools, LangGraph interrupt/checkpoint HITL, frozen Identify eval corpus.

**venv:** `.venv` at repo root (`uv sync --extra dev`). `./run.sh` and `make` use `.venv/bin/python`.

## User verification (1a)

1. `cp .env.example .env`
2. `./run.sh --check` (live Tavily + OmniRoute + pgvector + product handoffs)
3. `./run.sh` then:
   - `curl -s localhost:8000/ready`
   - `curl -s -X POST localhost:8000/identify/run -H 'content-type: application/json' -d '{}'`
   - `curl -s localhost:8000/identify/hitl`
4. Optional live LLM: fill OmniRoute (or any OpenAI-compatible) fields in `.env`, restart API, run Identify again.

---

## Why install is heavy

Not Postgres. Not FastAPI.

[`packages/agents/embeddings.py`](../../packages/agents/embeddings.py) depends on **`sentence-transformers`**, which pulls **`torch`** and **NVIDIA CUDA wheels** (hundreds of MB to >1 GB). That stack encodes 384-dim vectors for ~29 catalog keys and a few OSINT chunks. Exact-key dedup already works with hash vectors in pgvector. Paraphrase matching is the only reason to keep a real encoder.

**Cut:** default extra without torch; optional `embeddings` extra; `AEGIS_EMBEDDINGS=hash|onnx|st`.

---

## LLM: OmniRoute *or* any OpenAI-compatible key

Today [`packages/agents/llm/config.py`](../../packages/agents/llm/config.py) **errors** if `GROQ_API_KEY` is set while profile is `omniroute`. That blocks “I have some other key in .env.”

**Target:** one client, OpenAI chat completions, no silent 404 model fallback.

| Intent | Env |
|--------|-----|
| OmniRoute | `AEGIS_LLM_PROFILE=omniroute` `AEGIS_LLM_BASE_URL=http://127.0.0.1:20128/v1` `AEGIS_LLM_MODEL=auto` `AEGIS_LLM_API_KEY=...` |
| Any compatible API | `AEGIS_LLM_PROFILE=openai` or `generic_openai` + `AEGIS_LLM_BASE_URL` + `AEGIS_LLM_MODEL` + `AEGIS_LLM_API_KEY` |
| Groq | `AEGIS_LLM_PROFILE=groq` or `GROQ_API_KEY` as alias |

- Canonical key: `AEGIS_LLM_API_KEY`. Aliases `OPENAI_API_KEY` / `GROQ_API_KEY` only fill when the matching profile is active and the canonical key is empty.
- Unused alias keys must **not** crash OmniRoute.
- No key: fixture rules or abstain (already).

**`.env.example`:** commented OmniRoute block with host/port/model placeholders, plus commented OpenAI/Groq stanzas. Copy to `.env`; never commit secrets.

---

## Execution order (next implementation pass)

1. **Agnostic LLM + `.env.example` recipes** (small).
2. **Slim embeddings** (largest disk/RAM win). Default CI and `./run.sh` without CUDA.
3. **Phase 1b:** `kb_search` / `kb_get_chunk` / `upsert_taxonomy` on existing pgvector tables; LangGraph Postgres checkpointer + interrupt; frozen eval corpus (coverage/mutation remain targets).

Defer: payment sim, fraud scoring, Redis/ARQ, web UI, Qdrant.
