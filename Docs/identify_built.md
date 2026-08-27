# Identify — what is built

Code as of Phase 1a. This file describes implemented behavior, not the rest of Generate/Defend.

## System

- **Process:** LangGraph state machine `identify_graph` (`packages/agents/identify_graph.py`).
- **Node order (fixed):** `scout` → `extractor` → `grounder` → `tier_scorer` → `corroborator` → `librarian`.
- **HTTP:** FastAPI `POST /identify/run`, `GET /identify/hitl`, `POST /identify/decision/{vector_id}`, `GET /ready`.
- **Postgres:** `killchain_atlas` (catalog rows), `osint_chunks` (`vector(384)`), `catalog_embeddings` (`vector(384)`). Extension: `vector` (pgvector).
- **Seed:** `data/catalog/seed.yaml` → 29 `AttackSpec` rows, techniques T01–T24.

## Configuration for a live run

| Variable | Role |
|----------|------|
| `DATABASE_URL` | Postgres |
| `IDENTIFY_LIVE_SEARCH=true` | Scout uses Tavily + RSS instead of fixture files |
| `TAVILY_API_KEY` | Search and optional article extract |
| `AEGIS_LLM_PROFILE` / `AEGIS_LLM_BASE_URL` / `AEGIS_LLM_MODEL` / `AEGIS_LLM_API_KEY` | Chat Completions (default profile `omniroute`, `http://127.0.0.1:20128/v1`, model `auto`) |
| `AEGIS_EMBEDDINGS` | `fastembed` (ONNX BGE-small, 384-d) or `hash` (CI) |
| `IDENTIFY_MAX_DOCS` | Max URLs the extractor processes (default 3, cap 8) |

If LLM is not configured: extractor uses deterministic keyword rules or returns `extraction_source=abstain`. If `IDENTIFY_LIVE_SEARCH=false`: Scout loads `data/osint/fixtures/` (FinCEN + RBI texts).

Domain allowlist (search + fetch): `packages/osint/allowlist.py` (`fincen.gov`, `rbi.org.in`, `ftc.gov`, …). Queries containing exploit/dark-web terms are rejected.

## Live workflow (all of the above set)

1. **Scout**  
   Expand `topic` into search queries. `POST https://api.tavily.com/search` with `include_domains` = allowlist. Keep URL, domain, snippet. Append RSS hits. Dedupe URLs, cap 8. Output: `candidate_urls`.

2. **Extractor** (per URL, sorted by source tier, up to `IDENTIFY_MAX_DOCS`)  
   Drop non-allowlisted URLs. Fetch body (`extract_url`: Tavily Extract then trafilatura).  
   `embed_text` → insert `osint_chunks` (url, domain, text, `embedding vector(384)`).  
   `extract_from_document`: Chat Completions JSON → coerce enums → `AttackSpec.model_validate`, or abstain. `source_urls` = this URL. `status=proposed`.  
   Output: `extracted_docs` (includes `chunk_id`), `proposed_specs`.

3. **Grounder**  
   Drop specs with no payment `rail`, buzzword-only names, exploit-pattern text, or cosine > 0.92 vs another spec in the same run (`name|rail|technique_id`). Does not delete existing `open` seed rows.

4. **TierScorer**  
   `source_tier` = min allowlist tier of `source_urls`.  
   `confidence_level=confirmed` iff best tier ≤ 2, or ≥ 2 organizations each have a source with tier ≤ 3; else `reported-unverified`.

5. **Corroborator**  
   `vector_class` = `network_footprint` or `human_social`.  
   `corroboration_type` = `documentary-case` / `not-yet-corroborated` / `network-telemetry` (GreyNoise only if key + demo IP).  
   `canary_eligible` if confirmed, tier ≤ 2, `generate_mode=generate`, signals validate.

6. **Librarian**  
   Cosine vs `catalog_embeddings`. Merge only into another row with `status=proposed`. Insert/update `killchain_atlas`. Re-embed catalog key. Build HITL payload (field diff vs nearest row).  
   Output: `hitl_queue`, `hitl_required`.

7. **HITL (HTTP, not a graph interrupt)**  
   `GET /identify/hitl` lists `status=proposed`.  
   `approve` → `open` (legal transition matrix in `packages/catalog/status.py`). `reject` / `reject_unsafe` / `edit` (edit runs `AttackSpec.model_validate`).

Generate and Defend read `open` rows later. They are not executed inside this graph.

## Data contracts

- **AttackSpec** (`packages/catalog/models.py`): `vector_id`, `technique_id` (T01–T24), `category` 1–5, `rail`, `lifecycle_stage`, `genai_modality`, `social_surface`, `economic_class`, `generate_mode` (`generate` | `name_only`), `simulatable_signals` + `simulator.injector_id`, `source_urls`, `source_tier`, `confidence_level`, `status`.
- **Embeddings:** same 384-d column whether encoder is fastembed or hash. Hash is not a semantic model.

## Tests

- Offline (no keys): `pytest tests/ -m "not live_llm and not live_identify"`.
- Live (keys + Postgres): `pytest tests/test_identify_live_e2e.py -m live_identify -v`.

## Not built here

Knowledge-base search APIs, LangGraph checkpoint/interrupt, payment simulator, fraud classifier, web UI.
