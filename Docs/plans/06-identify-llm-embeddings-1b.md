# Identify after 1a — malleable LLM, embeddings, then 1b

**This is the plan for the next implementation pass.** It does not start Generate, Defend scoring, or the web app.

Honest status first, then what Identify actually does, then the three workstreams.

---

## 1. What is true today

### Tested end-to-end (no paid APIs)

- Docker **Postgres + pgvector**
- Seed **29** `AttackSpec` rows (T01–T24)
- Identify on **fixtures** (FinCEN + RBI lab texts)
- Extractor → grounder → tier → corroborator → **Librarian writes Postgres**
- HITL REST (`/identify/hitl`, approve/reject/edit with Pydantic)
- `./run.sh` / pytest (65 passed last green run)

That is a real product path. It is **not** live OSINT research and **not** a live LLM extraction.

### Not tested yet (needs your `.env`)

| Piece | Code | Live proof |
|-------|------|------------|
| OmniRoute HTTP client (`:20128/v1`, Bearer, JSON object) | **Yes** | **No** — no dashboard key / no running router in CI |
| Tavily allowlisted search | **Yes** | **No** — needs `TAVILY_API_KEY` + `IDENTIFY_LIVE_SEARCH=true` |
| Any other OpenAI-compatible API | **Partial** — `generic_openai` / `groq` profiles exist; Groq leftover key currently **errors** if profile is still OmniRoute | **No** |

**OmniRoute integration:** the **client and default profile are done**. The **live round-trip is not**. When you have env: start OmniRoute, copy `.env.example` → `.env`, set `AEGIS_LLM_API_KEY`, `IDENTIFY_LIVE_SEARCH` as you wish, restart API, `POST /identify/run`. `extraction_source` should be `llm` when the router answers valid JSON.

**Entire Phase 1:** **1a done, 1b not done.** Do not call Identify “finished” until 1b (or you explicitly drop 1b from the phase). Getting env lets you **test live 1a**, not auto-complete 1b.

---

## 2. What we built (rough map)

```
Scout (URLs) → Extractor (body + AttackSpec draft + pgvector chunk)
  → Grounder (reject junk / in-batch clones)
  → TierScorer (source_tier, confirmed vs reported-unverified)
  → Corroborator (vector_class, documentary vs telemetry)
  → Librarian (Postgres HITL queue, catalog cosine for nearest-row diff)
```

Around that:

- **Catalog** YAML → `killchain_atlas` (system of record)
- **pgvector** `osint_chunks` + `catalog_embeddings` (same Postgres)
- **API:** `/identify/run`, `/identify/hitl`, `/catalog`, generate/defend **stubs**, `/ready`
- **LLM module:** OpenAI-compatible POST `/chat/completions` only (no Gemini/Anthropic native)

Offline without keys: Scout uses fixtures; Extractor uses **keyword rules** on known patterns or **abstains** (no invented T13).

---

## 2b. After Tavily + chunk — then what? (this is Identify)

Tavily is **not** the product. pgvector is **not** the product.

```
allowlisted URLs
    → article body
    → (side) embed 384-d → osint_chunks in the SAME Postgres
    → LLM/rules → AttackSpec (technique T01–T24, rail, signals, generate_mode)
    → grounder / tier / corroboration
    → killchain_atlas status=proposed
    → human approve → open  → later Generate/Defend consume the card
```

The vector table is a **helper**: nearest-neighbor for “is this the same attack we already have?” and future `kb_search`. The **Identify output** is a typed catalog row Generate can simulate and Defend can cover — not a pile of chunks.

If we only searched and stored embeddings, that would **fail** [`MC_PS.md`](../../MC_PS.md): Identify must surface **distinct, grounded GenAI payment-fraud vectors** with breadth across lifecycle × rail × economic class (Plan 01: 24 techniques, 5 categories). Chunks without `AttackSpec` do not score “diversity of attacks identified.”

### Is Identify “good enough” vs MC_PS?

| MC_PS ask | What 1a actually is |
|-----------|---------------------|
| Exhaustive landscape of novel GenAI payment fraud | **Partial.** Allowlisted OSINT + fixtures + seed YAML (29 rows, T01–T24). Not an open-web crawl. Diversity today is mostly **the seed census**, plus new proposed cards from articles. |
| Grounded in real rails / fraud | **Yes, structurally.** `AttackSpec` + allowlist tiers + abstain on weak text. |
| Closed loop Identify → Generate → Defend | **Identify slice only.** Generate/Defend are stubs. No classifier, no sim fidelity, no web prototype. |
| “Just an API + vector DB?” | **No.** API is the lab surface. Vector DB is storage for chunks/dedup. The graph **classifies into the atlas**. That is Identify-the-component. It is **not** the whole challenge. |

**Good enough as the Identify pillar of the loop (1a).** Not good enough as the Mastercard submission until Generate, Defend, eval, and UI exist.

---

## 3. Identify workflow (detail)

### 3.1 Scout

- `IDENTIFY_LIVE_SEARCH=false` (default): two fixture URLs (FinCEN deepfake KYC, RBI UPI/APP note).
- `true`: Tavily on allowlisted domains, plus RSS. Topic string from `POST /identify/run`.
- Output: `candidate_urls` (url, domain, snippet, fetched_at). Cap 8.

### 3.2 Extractor

For each URL (tier-sorted, max `IDENTIFY_MAX_DOCS`):

1. **Body:** fixture keyed **only by URL**; live fetch via Tavily/trafilatura. Unknown offline URL → fail that doc, no FinCEN substitution.
2. **Chunk:** embed text, upsert `osint_chunks`.
3. **Spec:** if LLM configured → chat completions JSON → validate into `AttackSpec` or abstain. Else rules (deepfake+KYC → T09, UPI/impersonation → T13, mule → T01) or abstain.
4. Scout URL stays authoritative on `source_urls`.

### 3.3 Grounder

Drop: no payment rail, buzzword-only, exploit/how-to patterns, near-duplicate **inside this run** (cosine > 0.92 on name|rail|technique).

Does **not** drop “looks like seed T13” — those become new `proposed` rows for HITL, with a field diff vs nearest catalog card. Open seed rows are not demoted.

### 3.4 TierScorer

Best `source_tier` from allowlist. **Confirmed** iff one source tier 1–2, **or** ≥2 independent orgs each with a source tier ≤3.

### 3.5 Corroborator

Sets `vector_class`, `corroboration_type` (documentary vs not-yet-corroborated). GreyNoise remains optional stub.

### 3.6 Librarian

Writes `status=proposed`. Merge only into another **proposed** row (exact / vector). HITL payload includes nearest catalog field diff.

### 3.7 Human

`POST /identify/decision/{vector_id}` approve → `open` (Generate may use it later). Reject / reject_unsafe / edit (Pydantic on every patch). Legal status matrix in `packages/catalog/status.py`.

---

## 4. Workstream 1 — Malleable LLM (not fully agnostic)

**Goal:** OmniRoute **and** “paste an OpenAI-compatible base URL + key.” Not a marketplace of Gemini/Anthropic protocols.

### Keep

- One transport: OpenAI `chat/completions`
- No silent 404 model fallback
- Loopback HTTP only for localhost (OmniRoute)
- Secrets redacted in errors
- Offline: rules/abstain

### Change

[`packages/agents/llm/config.py`](../../packages/agents/llm/config.py) today raises if `GROQ_API_KEY` is set while profile is OmniRoute. That is too strict.

**Resolution order:**

1. `AEGIS_LLM_PROFILE` (default `omniroute`)
2. `AEGIS_LLM_BASE_URL` overrides the profile’s default host
3. `AEGIS_LLM_MODEL` (OmniRoute default `auto`; other profiles require an explicit model)
4. Key: `AEGIS_LLM_API_KEY` if set; else alias **only for the active profile** (`GROQ_API_KEY` if profile=groq, `OPENAI_API_KEY` if profile=openai)
5. Unused alias keys are **ignored** (log nothing with secret values)

**Profiles (enough, not many):**

| Profile | Default base | Typical key |
|---------|--------------|-------------|
| `omniroute` | `http://127.0.0.1:20128/v1` | OmniRoute dashboard Bearer |
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` or `AEGIS_LLM_API_KEY` |
| `groq` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` or `AEGIS_LLM_API_KEY` |
| `generic_openai` | none — **must** set `AEGIS_LLM_BASE_URL` | `AEGIS_LLM_API_KEY` |

OpenRouter / Together / vLLM / Ollama: use `generic_openai` + their `/v1` URL. Do not add a profile per vendor unless we hit a real header quirk.

### `.env.example`

Commented blocks:

```
# --- OmniRoute (default) ---
AEGIS_LLM_PROFILE=omniroute
AEGIS_LLM_BASE_URL=http://127.0.0.1:20128/v1
AEGIS_LLM_MODEL=auto
AEGIS_LLM_API_KEY=

# --- Or any OpenAI-compatible API (comment OmniRoute, uncomment) ---
# AEGIS_LLM_PROFILE=generic_openai
# AEGIS_LLM_BASE_URL=https://api.example.com/v1
# AEGIS_LLM_MODEL=your-model-id
# AEGIS_LLM_API_KEY=
```

### Tests (in-process HTTP + env matrix)

- OmniRoute + key → configured
- generic_openai + base + key → configured
- OmniRoute + leftover `GROQ_API_KEY` → **still OmniRoute**, no error
- No key → `is_llm_configured()` false; Identify still proposes from fixtures

### Live check (you, when env exists)

`GET /ready` → `llm.configured: true`. Identify `extracted_docs[].extraction_source == llm` (or abstain if the model returns junk — that is correct, not a crash).

---

## 5. Workstream 2 — fastembed, same pgvector (in progress in repo)

**Decision:** keep **Postgres `vector(384)`**. Swap the **encoder**, not the database. No Qdrant.

| `AEGIS_EMBEDDINGS` | Encoder | When |
|--------------------|---------|------|
| `fastembed` (default local) | ONNX `BAAI/bge-small-en-v1.5`, 384-d | Demo paraphrase / HITL nearest |
| `hash` | SHA256 dummy unit vector | CI / `make validate-all` (no model download) |
| `st` | optional extra `embeddings-st` (torch) | Only if we must match old ST numbers |

**Verify (offline, no Tavily):** `tests/test_fastembed_pgvector.py`

- dim == 384, L2-normalized (fits existing columns)
- paraphrase cosine > unrelated (skipped on CI hash)
- `register_catalog_embedding` + `upsert_chunk` round-trip in Postgres

**Live Identify e2e (when APIs are back):** `tests/test_identify_live_e2e.py` marker `live_identify`

```
pytest tests/test_identify_live_e2e.py -m live_identify
```

Requires `TAVILY_API_KEY` + configured LLM. Asserts: allowlisted URLs, chunks written, proposed specs with `technique_id`/`rail`/`status=proposed` **or** explicit abstain (never silent empty).

Do not run `live_identify` in GitHub Actions.

---

## 6. Workstream 3 — Phase 1b (only after 1+2 or explicit skip of 2)

Still the original 1b:

- `kb_search` / `kb_get_chunk` / `upsert_taxonomy` on **existing** pgvector tables (bounded results, provenance)
- LangGraph **interrupt** before approve + Postgres checkpointer (`thread_id` resume). REST HITL stays; interrupt is extra, not a rewrite of `/identify/decision`
- Frozen Identify eval set (small, reviewed): schema 100%, unsafe 100% reject, no source substitution. Coverage/mutation **targets**, not blockers

Live OmniRoute **variance** (`auto` routing) is not a reproducibility claim — pin a model id for eval runs.

---

## 7. Suggested sequence

```
1. Malleable LLM + .env.example
2. fastembed default + hash in CI  ← encoder swap; same pgvector
3. You: pytest -m live_identify when Tavily + OmniRoute keys exist
4. 1b KB + checkpoint + tiny eval corpus
```

**NO-GO for calling Phase 1 complete:** 1b still open; live LLM unproven; mix-error still in config until workstream 1.

**GO for “ready for your keys”:** after workstream 1. You can already *try* keys today if you only use OmniRoute and **do not** also set `GROQ_API_KEY` in `.env`.
