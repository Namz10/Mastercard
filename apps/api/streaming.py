"""Shared SSE worker-queue streaming for long-running booth jobs."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import threading
import time
from collections.abc import AsyncIterator, Callable

logger = logging.getLogger(__name__)


def sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def log_stream_event(job: str, run_id: str | None, payload: dict) -> None:
    """Structured log line for booth stream progress (mirror identify)."""
    status = payload.get("status")
    verb = payload.get("verb")
    body = payload.get("body")
    elapsed = payload.get("t")
    if status == "error":
        logger.error(
            "%s stream error run_id=%s reason=%s elapsed_ms=%s",
            job,
            run_id,
            payload.get("reason"),
            elapsed,
        )
        return
    if status == "done" and payload.get("result"):
        result = payload["result"]
        logger.info(
            "%s stream complete run_id=%s event_count=%s fidelity_pass=%s elapsed_ms=%s",
            job,
            result.get("run_id", run_id),
            result.get("event_count"),
            (result.get("fidelity") or {}).get("pass"),
            elapsed,
        )
        return
    if verb and body:
        logger.info(
            "%s stream progress run_id=%s verb=%s elapsed_ms=%s body=%s",
            job,
            run_id,
            verb,
            elapsed,
            body[:120],
        )


async def async_stream_worker(
    worker: Callable[[queue.SimpleQueue[str | None], float], None],
) -> AsyncIterator[str]:
    """Drain SSE chunks from a worker thread so progress events flush during long jobs."""
    t0 = time.time()
    event_q: queue.SimpleQueue[str | None] = queue.SimpleQueue()
    threading.Thread(target=worker, args=(event_q, t0), daemon=True).start()

    while True:
        drained = False
        while True:
            try:
                item = event_q.get_nowait()
            except queue.Empty:
                break
            drained = True
            if item is None:
                return
            yield item
            await asyncio.sleep(0)
        if not drained:
            await asyncio.sleep(0.05)
