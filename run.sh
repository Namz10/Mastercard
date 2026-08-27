#!/usr/bin/env bash
# End-to-end AegisLoop: Postgres+pgvector, seed, Identify, API.
# Usage:
#   ./run.sh              start stack and leave the API running
#   ./run.sh --validate   start stack, run gates, then exit
#   ./run.sh --down       stop compose

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}"
export IDENTIFY_LIVE_SEARCH="${IDENTIFY_LIVE_SEARCH:-false}"

if [[ "${1:-}" == "--down" ]]; then
  docker compose down
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if [[ -x "${ROOT}/.venv/bin/python" ]]; then
  PY="${ROOT}/.venv/bin/python"
else
  if command -v uv >/dev/null 2>&1; then
    uv sync --extra dev
    PY="${ROOT}/.venv/bin/python"
  else
    python3 -m venv .venv
    PY="${ROOT}/.venv/bin/python"
    "${PY}" -m pip install -U pip
    "${PY}" -m pip install -e ".[dev]"
  fi
fi

echo "==> Postgres (pgvector)"
docker compose up -d postgres --wait

echo "==> Seed KillChain Atlas + catalog embeddings"
"${PY}" apps/api/seed.py --reset

echo "==> Identify (fixtures, real Librarian / pgvector)"
"${PY}" - <<'PY'
from apps.api.db import init_db
from packages.agents.identify_graph import run_identify_graph

init_db()
result = run_identify_graph(run_id="run-sh")
print(
    "identify",
    result["run_id"],
    "urls",
    len(result.get("candidate_urls") or []),
    "proposed",
    len(result.get("proposed_specs") or []),
    "hitl",
    result.get("hitl_required"),
)
assert len(result.get("candidate_urls") or []) >= 1
assert len(result.get("proposed_specs") or []) >= 1
PY

if [[ "${1:-}" == "--validate" ]]; then
  echo "==> pytest"
  "${PY}" -m pytest tests/ -q -m "not live_llm"
  echo "==> validate-all remainder"
  make catalog-validate osint-validate handoff-validate
  echo "=== RUN.SH VALIDATE PASSED ==="
  exit 0
fi

echo "==> API on http://127.0.0.1:8000"
exec "${PY}" -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
