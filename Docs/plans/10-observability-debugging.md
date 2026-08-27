# Plan 10 — Product logging and debugging

**Status:** PROPOSED  
**Goal:** after one `./run.sh`, show what each stage attempted, what it produced,
where it stopped, and why—without printing secrets or full sensitive documents.

## What exists now

`run.sh` prints eight named e2e stages and each stage duration. Tavily prints the
sanitized query, hit count, selected domain/URL, extractor, and document size.
Identify prints Tavily/RSS URL counts, extracted documents, proposal candidates,
HITL rows, and the first five pipeline errors. Generate/Defend/API print compact
counts.

This is enough for terminal debugging now. It is not yet durable: output
disappears when the terminal closes, and node-level work inside LangGraph is not
timed.

## Logging contract

Every event is one JSON object:

```json
{
  "ts": "ISO-8601 UTC",
  "level": "INFO",
  "run_id": "identify-...",
  "stage": "scout",
  "event": "query_finished",
  "duration_ms": 842,
  "counts": {"hits": 3},
  "source": {"query_id": "identity-fincen-1", "domain_group": "us_regulators"}
}
```

Required fields: `ts`, `level`, `run_id`, `stage`, `event`, `duration_ms` when a
step ends. Counts are numbers, not prose.

Never log: API keys, Authorization headers, DATABASE_URL passwords, complete
article bodies, complete LLM prompts/responses, transcripts, embeddings.
Log URLs and short redacted errors. Reuse the existing secret redactor.

## Events by stage

### Startup
- effective non-secret config: live search, LLM profile/model, embedding backend,
  database host only
- Postgres/pgvector health and seed row count

### Scout
- query id and sanitized query
- source group, Tavily status (`ok | empty | error`), hit count, latency
- RSS status separately
- why each candidate was kept/dropped (allowlist, duplicate, low relevance)

### Extractor and vector store
- URL, extractor used, character count, chunk id
- embedding model/backend, dimension, insert/update
- LLM result: `llm | abstain | rules_fallback`; validation failure category

### Grounder through Librarian
- input/output count and duration per LangGraph node
- duplicates removed and the matching existing vector id
- candidate proposals vs rows actually persisted to HITL
- database commit success/failure

### Generate and Defend
- selected recipe ids in **run metadata only**, event counts, verifier rejects
- model/version/feature-view, score latency, action counts
- never place recipe ids in the training feature file

### HTTP
- request id, route, status, latency; no request body by default

## Storage and viewing

1. Terminal: concise human lines (what `run.sh` already starts doing).
2. JSONL: `logs/runs/{run_id}.jsonl`, ignored by git.
3. Postgres summary: later add `pipeline_runs` with start/end, status, stage
   counts, and artifact paths—not every debug event.
4. API: `GET /runs/{run_id}` returns the summary and failed-stage reason.

No ELK/OpenTelemetry/Datadog for the prototype. JSONL plus one summary table is
enough.

## Failure behavior

- A stage logs `stage_failed` once with error type and redacted message.
- `run.sh` exits non-zero and prints the run id plus JSONL path.
- Search `empty` is different from network `error`.
- `no_new_attack` is success when documents were processed but deduplicated or
  explicitly abstained; silent output is failure.
- Later stages do not run after a required-stage failure.

## Build order

1. Add a small `packages/observability.py` JSON logger with secret redaction.
2. Wrap each Identify node with start/end/count/error events.
3. Give API requests and product runs one shared `run_id`.
4. Write JSONL and final terminal summary.
5. Add `pipeline_runs` summary model and `GET /runs/{run_id}`.
6. Add tests proving keys/prompts/bodies are redacted and empty/error/no-new are
   distinguishable.

## Done when

- One failed run identifies the exact stage, query id, duration, and reason.
- One successful run shows counts from Scout through HITL and handoff.
- Searching logs for known dummy API keys returns no matches.
- Tavily-empty, RSS-only, LLM-abstain, duplicate-only, DB-failure, and success
  each have distinct terminal states.
