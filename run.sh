#!/usr/bin/env bash
# Single end-to-end AegisLoop entrypoint:
# Postgres+pgvector → seed → Tavily → embeddings/RAG → OmniRoute →
# Identify graph/Librarian → Generate/Defend handoff → FastAPI.
# Usage:
#   ./run.sh              run live e2e, then leave the API running
#   ./run.sh --check      run live e2e, then exit
#   ./run.sh --down       stop compose

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}"

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

echo "==> Configuration"
"${PY}" - <<'PY'
from apps.api.env import load_project_env
from packages.agents.llm.config import is_llm_configured, public_llm_status
from packages.agents.settings import get_identify_settings
from packages.osint.settings import get_osint_settings

load_project_env()
osint = get_osint_settings()
identify = get_identify_settings()
missing = []
if not osint.identify_live_search:
    missing.append("IDENTIFY_LIVE_SEARCH=true")
if identify.identify_tavily_enabled and not osint.tavily_api_key:
    missing.append("TAVILY_API_KEY (or set IDENTIFY_TAVILY_ENABLED=false)")
if not is_llm_configured():
    missing.append("AEGIS_LLM_API_KEY (or active-profile alias)")
if missing:
    raise SystemExit("Live e2e requires these .env settings: " + ", ".join(missing))

llm = public_llm_status()
print(
    "config OK",
    f"live_search={osint.identify_live_search}",
    f"llm_profile={llm.get('profile')}",
    f"llm_model={llm.get('model')}",
)
PY

echo "==> Postgres (pgvector)"
docker compose up -d postgres --wait

echo "==> Live end-to-end gates"
"${PY}" scripts/validate_all_live.py

if [[ "${1:-}" == "--check" ]]; then
  echo "=== AEGISLOOP LIVE E2E PASSED ==="
  exit 0
fi

echo "==> API on http://127.0.0.1:8000"
exec "${PY}" -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
