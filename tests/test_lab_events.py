"""Lab event bus unit tests (offline, no Postgres)."""

from packages.lab.events import (
    emit_lab,
    emit_loop_end,
    emit_loop_start,
    get_lab_bus,
    load_replay_trace,
)


def test_emit_and_history():
    bus = get_lab_bus()
    bus.set_active_thread("test-unit")
    emit_lab("system", "ping", "hello", thread_id="test-unit")
    hist = bus.history("test-unit")
    assert hist
    assert hist[-1].message == "hello"
    assert hist[-1].phase == "system"


def test_loop_brackets():
    emit_loop_start("M", "miss_family:mule", thread_id="test-loop")
    emit_loop_end("M", pass_=True, payload={"ap_delta": 0.01, "catalog_solved": False}, thread_id="test-loop")
    hist = get_lab_bus().history("test-loop")
    msgs = [e.message for e in hist]
    assert any("LOOP M START" in m for m in msgs)
    assert any("LOOP M END" in m for m in msgs)
    assert any("catalog_solved=False" in m or "catalog_solved=false" in m for m in msgs)


def test_replay_fixture_loads():
    events = load_replay_trace()
    assert len(events) >= 10
    phases = {e.phase for e in events}
    assert "identify" in phases
    assert "generate" in phases
    assert "defend" in phases
    assert "evolve" in phases
    assert any(e.loop == "M" for e in events)
