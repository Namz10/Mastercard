"""Load project .env into os.environ for API and scripts."""

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


def load_project_env() -> None:
    """Parse .env into os.environ (does not override existing vars)."""
    if not _ENV_FILE.is_file():
        return
    for raw_line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_configured(key: str) -> bool:
    load_project_env()
    return bool(os.getenv(key, "").strip())
