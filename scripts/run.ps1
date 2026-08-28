# Single end-to-end AegisLoop entrypoint (Windows). Same stages as ./run.sh.
# Usage:
#   pwsh -File scripts/run.ps1              live e2e, then leave the API running
#   pwsh -File scripts/run.ps1 --check      live e2e, then exit
#   pwsh -File scripts/run.ps1 --down       stop compose

param(
    [Parameter(Position = 0)]
    [string]$Mode = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$env:PYTHONPATH = "$Root"

if ($Mode -eq "--down") {
    docker compose down
    exit 0
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "docker is required"
}

$Py = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "Missing $Py — create the venv (uv sync --extra dev) first"
}

Write-Host "==> Configuration"
& $Py -c @'
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
'@
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Postgres (pgvector)"
docker compose up -d postgres --wait
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Live end-to-end gates"
& $Py (Join-Path $Root "scripts\validate_all_live.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Telemetry corroboration gate (live Tavily + GreyNoise)"
& $Py (Join-Path $Root "scripts\validate_telemetry.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Mode -eq "--check") {
    Write-Host "=== AEGISLOOP LIVE E2E PASSED ==="
    exit 0
}

Write-Host "==> API on http://127.0.0.1:8000"
& $Py -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
