"""SSE progress hook for generate / fit / loop-m / tune jobs (mirror identify progress)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Callable

ProgressCallback = Callable[[str, str, dict[str, Any] | None], None]

_job_progress: ContextVar[ProgressCallback | None] = ContextVar("_job_progress", default=None)


def set_job_progress_hook(cb: ProgressCallback | None) -> object:
    return _job_progress.set(cb)


def reset_job_progress_hook(token: object) -> None:
    _job_progress.reset(token)


def emit_job_progress(
    verb: str,
    body: str,
    artifacts: dict[str, Any] | None = None,
) -> None:
    cb = _job_progress.get()
    if cb is not None:
        cb(verb, body, artifacts)
