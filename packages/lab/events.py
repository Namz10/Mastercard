"""In-process lab event bus for Simulation Console SSE."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Iterator, Literal

Phase = Literal["identify", "generate", "defend", "evolve", "system"]
Level = Literal["info", "stage", "loop", "warn", "error", "hitl"]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACE = PROJECT_ROOT / "data" / "demo" / "lab_trace.jsonl"


@dataclass
class LabEvent:
    ts: str
    phase: Phase
    stage: str
    level: Level
    message: str
    loop: str | None = None
    tech: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    thread_id: str = "demo-1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_sse(self) -> str:
        return f"data: {json.dumps(self.to_dict(), default=str)}\n\n"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LabBus:
    """Thread-safe pub/sub for lab events. Keeps a ring buffer per thread_id."""

    def __init__(self, history: int = 500) -> None:
        self._lock = threading.Lock()
        self._subs: dict[str, list[Queue[LabEvent | None]]] = defaultdict(list)
        self._history: dict[str, deque[LabEvent]] = defaultdict(lambda: deque(maxlen=history))
        self._active_thread = "demo-1"

    @property
    def active_thread(self) -> str:
        return self._active_thread

    def set_active_thread(self, thread_id: str) -> None:
        with self._lock:
            self._active_thread = thread_id or "demo-1"

    def emit(self, event: LabEvent) -> LabEvent:
        tid = event.thread_id or self._active_thread
        event.thread_id = tid
        with self._lock:
            self._history[tid].append(event)
            for q in list(self._subs.get(tid, [])):
                try:
                    q.put_nowait(event)
                except Exception:
                    pass
        return event

    def subscribe(self, thread_id: str, *, replay_history: bool = True) -> Queue[LabEvent | None]:
        q: Queue[LabEvent | None] = Queue(maxsize=2000)
        with self._lock:
            if replay_history:
                for ev in self._history.get(thread_id, []):
                    q.put_nowait(ev)
            self._subs[thread_id].append(q)
        return q

    def unsubscribe(self, thread_id: str, q: Queue[LabEvent | None]) -> None:
        with self._lock:
            subs = self._subs.get(thread_id, [])
            if q in subs:
                subs.remove(q)

    def history(self, thread_id: str) -> list[LabEvent]:
        with self._lock:
            return list(self._history.get(thread_id, []))

    def clear(self, thread_id: str) -> None:
        with self._lock:
            self._history[thread_id].clear()
            # Drop buffered events for live subscribers so a fresh run is clean
            for q in list(self._subs.get(thread_id, [])):
                try:
                    while True:
                        q.get_nowait()
                except Empty:
                    pass
                except Exception:
                    pass


_BUS = LabBus()


def get_lab_bus() -> LabBus:
    return _BUS


def emit_lab(
    phase: Phase,
    stage: str,
    message: str,
    *,
    level: Level = "info",
    loop: str | None = None,
    tech: list[str] | None = None,
    payload: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> LabEvent:
    bus = get_lab_bus()
    event = LabEvent(
        ts=_now(),
        phase=phase,
        stage=stage,
        level=level,
        message=message,
        loop=loop,
        tech=list(tech or []),
        payload=dict(payload or {}),
        thread_id=thread_id or bus.active_thread,
    )
    return bus.emit(event)


def lab_event(
    phase: Phase,
    stage: str,
    message: str,
    **kwargs: Any,
) -> LabEvent:
    return emit_lab(phase, stage, message, **kwargs)


@contextmanager
def lab_stage(
    phase: Phase,
    stage: str,
    message: str,
    *,
    loop: str | None = None,
    tech: list[str] | None = None,
    payload: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Emit STAGE start/end with elapsed_ms."""
    t0 = time.perf_counter()
    body = dict(payload or {})
    emit_lab(
        phase,
        stage,
        message,
        level="stage",
        loop=loop,
        tech=tech,
        payload=body,
        thread_id=thread_id,
    )
    try:
        yield body
    except Exception as exc:
        emit_lab(
            phase,
            stage,
            f"{stage} failed: {exc}",
            level="error",
            loop=loop,
            tech=tech,
            payload={**body, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
            thread_id=thread_id,
        )
        raise
    else:
        emit_lab(
            phase,
            stage,
            f"{stage} done",
            level="stage",
            loop=loop,
            tech=tech,
            payload={**body, "elapsed_ms": int((time.perf_counter() - t0) * 1000)},
            thread_id=thread_id,
        )


def emit_loop_start(loop: str, trigger: str, *, phase: Phase = "evolve", thread_id: str | None = None) -> None:
    emit_lab(
        phase,
        f"loop_{loop.lower()}_start",
        f"━━━ LOOP {loop} START ━━━ trigger={trigger}",
        level="loop",
        loop=loop,
        payload={"trigger": trigger},
        thread_id=thread_id,
    )


def emit_loop_end(
    loop: str,
    *,
    phase: Phase = "evolve",
    pass_: bool | None = None,
    payload: dict[str, Any] | None = None,
    thread_id: str | None = None,
) -> None:
    bits = []
    body = dict(payload or {})
    if pass_ is not None:
        bits.append(f"pass={str(pass_).lower()}")
        body["pass"] = pass_
    if "ap_delta" in body:
        bits.append(f"ap_delta={body['ap_delta']:+.4f}" if isinstance(body["ap_delta"], (int, float)) else f"ap_delta={body['ap_delta']}")
    if "catalog_solved" in body:
        bits.append(f"catalog_solved={body['catalog_solved']}")
    suffix = " · ".join(bits) if bits else "complete"
    emit_lab(
        phase,
        f"loop_{loop.lower()}_end",
        f"━━━ LOOP {loop} END ━━━ {suffix}",
        level="loop",
        loop=loop,
        payload=body,
        thread_id=thread_id,
    )


def load_replay_trace(path: Path | None = None) -> list[LabEvent]:
    p = path or DEFAULT_TRACE
    if not p.is_file():
        return []
    out: list[LabEvent] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        raw = json.loads(line)
        out.append(
            LabEvent(
                ts=str(raw.get("ts") or _now()),
                phase=raw.get("phase") or "system",
                stage=str(raw.get("stage") or "replay"),
                level=raw.get("level") or "info",
                message=str(raw.get("message") or ""),
                loop=raw.get("loop"),
                tech=list(raw.get("tech") or []),
                payload=dict(raw.get("payload") or {}),
                thread_id=str(raw.get("thread_id") or "demo-1"),
            )
        )
    return out


def iter_sse(thread_id: str, *, timeout_sec: float = 30.0) -> Iterator[str]:
    """Yield SSE chunks for subscribers. Ends on sentinel None or idle timeout."""
    bus = get_lab_bus()
    q = bus.subscribe(thread_id, replay_history=True)
    idle = 0.0
    try:
        yield ": connected\n\n"
        while True:
            try:
                ev = q.get(timeout=1.0)
            except Empty:
                idle += 1.0
                if idle >= timeout_sec:
                    yield ": keepalive\n\n"
                    idle = 0.0
                continue
            idle = 0.0
            if ev is None:
                break
            yield ev.to_sse()
    finally:
        bus.unsubscribe(thread_id, q)
