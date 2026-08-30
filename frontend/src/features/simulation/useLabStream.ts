import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api-client";
import { useLatestRun } from "@/lib/latest-run-context";
import {
  DEFAULT_THREAD_ID,
  MACRO_PHASES,
  type LabCounters,
  type LabEvent,
  type LabPhase,
  type LedgerSnippet,
  type LoopMarker,
  type PhaseStatus,
  type PhaseStatusMap,
  type StreamMode,
} from "./lab-types";

function isLabEvent(raw: unknown): raw is LabEvent {
  if (!raw || typeof raw !== "object") return false;
  const o = raw as Record<string, unknown>;
  return typeof o.ts === "string" && typeof o.phase === "string" && typeof o.message === "string";
}

function normalizeEvent(raw: LabEvent): LabEvent {
  return {
    ts: raw.ts,
    phase: (raw.phase as LabPhase) || "system",
    stage: String(raw.stage ?? ""),
    level: raw.level || "info",
    message: String(raw.message ?? ""),
    loop: raw.loop ?? null,
    tech: Array.isArray(raw.tech) ? raw.tech.map(String) : [],
    payload: raw.payload && typeof raw.payload === "object" ? (raw.payload as Record<string, unknown>) : {},
    thread_id: String(raw.thread_id || DEFAULT_THREAD_ID),
  };
}

function num(v: unknown): number | null {
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && !Number.isNaN(Number(v))) return Number(v);
  return null;
}

function bool(v: unknown): boolean | null {
  if (typeof v === "boolean") return v;
  return null;
}

export function derivePhaseStatus(events: LabEvent[]): PhaseStatusMap {
  const base: PhaseStatusMap = {
    identify: "pending",
    generate: "pending",
    defend: "pending",
    evolve: "pending",
  };

  const failed = new Set<Exclude<LabPhase, "system">>();
  const started = new Set<Exclude<LabPhase, "system">>();
  let current: Exclude<LabPhase, "system"> | null = null;
  let demoEnded = false;

  for (const ev of events) {
    if (ev.stage === "demo_end" || ev.stage === "demo_error") demoEnded = true;
    if (ev.phase === "system") continue;
    if (!MACRO_PHASES.includes(ev.phase as (typeof MACRO_PHASES)[number])) continue;
    const p = ev.phase as Exclude<LabPhase, "system">;
    started.add(p);
    current = p;
    if (ev.level === "error") failed.add(p);
  }

  const currentIdx = current ? MACRO_PHASES.indexOf(current) : -1;

  for (const phase of MACRO_PHASES) {
    const idx = MACRO_PHASES.indexOf(phase);
    if (failed.has(phase)) {
      base[phase] = "failed";
    } else if (!started.has(phase)) {
      base[phase] = "pending";
    } else if (demoEnded) {
      base[phase] = "completed";
    } else if (phase === current) {
      base[phase] = "active";
    } else if (idx < currentIdx) {
      base[phase] = "completed";
    } else {
      base[phase] = "pending";
    }
  }

  return base;
}

export function deriveLoopMarkers(events: LabEvent[]): LoopMarker[] {
  const out: LoopMarker[] = [];
  events.forEach((ev, index) => {
    if (ev.level !== "loop" && !ev.stage.startsWith("loop_")) return;
    const stage = ev.stage.toLowerCase();
    const msg = ev.message.toUpperCase();
    const loop = (ev.loop || stage.match(/loop_([a-z])/i)?.[1]?.toUpperCase() || "?").toString();

    if (stage.includes("_start") || (msg.includes("LOOP") && msg.includes("START"))) {
      out.push({ loop, kind: "open", ts: ev.ts, phase: ev.phase, index });
      return;
    }
    if (stage.includes("_end") || (msg.includes("LOOP") && msg.includes("END"))) {
      out.push({
        loop,
        kind: "close",
        ts: ev.ts,
        phase: ev.phase,
        pass: bool(ev.payload.pass) ?? undefined,
        index,
      });
    }
  });
  return out;
}

export function deriveCounters(events: LabEvent[]): LabCounters {
  const counters: LabCounters = {
    events: events.length,
    rowsExported: null,
    fraudRate: null,
    fidelityPass: null,
    genuineFpr: null,
    authgateMsP50: null,
    modelFreezeId: null,
  };

  for (const ev of events) {
    const p = ev.payload;
    const row = num(p.row_count) ?? num(p.event_count);
    if (row != null) counters.rowsExported = row;

    const fid = p.fidelity;
    if (fid && typeof fid === "object") {
      const f = fid as Record<string, unknown>;
      const fr = num(f.fraud_rate);
      if (fr != null) counters.fraudRate = fr;
      const fp = bool(f.pass);
      if (fp != null) counters.fidelityPass = fp;
    }
    const frDirect = num(p.fraud_rate);
    if (frDirect != null) counters.fraudRate = frDirect;
    const passDirect = bool(p.pass);
    if (ev.stage.includes("fidelity") && passDirect != null) counters.fidelityPass = passDirect;

    const gfp = num(p.genuine_fp) ?? num(p.genuine_FPR) ?? num(p.genuine_fpr);
    if (gfp != null) counters.genuineFpr = gfp;

    const ag = num(p.authgate_ms_p50);
    if (ag != null) counters.authgateMsP50 = ag;

    if (typeof p.model_freeze_id === "string") counters.modelFreezeId = p.model_freeze_id;
  }

  return counters;
}

export function deriveLedgerSnippets(events: LabEvent[]): LedgerSnippet[] {
  for (let i = events.length - 1; i >= 0; i--) {
    const raw = events[i].payload.lifecycle_stages_logged;
    if (!Array.isArray(raw) || raw.length === 0) continue;
    return raw
      .filter((x): x is Record<string, unknown> => !!x && typeof x === "object")
      .slice(-5)
      .map((x) => ({
        lifecycle_stage: String(x.lifecycle_stage ?? x.stage ?? "—"),
        party_id: String(x.party_id ?? x.party ?? "—"),
      }));
  }
  return [];
}

export function extractMeta(events: LabEvent[]) {
  let runId: string | null = null;
  let worldSeed: number | null = null;
  let rowCount: number | null = null;
  let fidelityPass: boolean | null = null;
  let apDelta: number | null = null;
  let generation = "G0";
  let threadId = DEFAULT_THREAD_ID;

  for (const ev of events) {
    if (ev.thread_id) threadId = ev.thread_id;
    const p = ev.payload;
    if (typeof p.run_id === "string") runId = p.run_id;
    const ws = num(p.world_seed);
    if (ws != null) worldSeed = ws;
    const rc = num(p.row_count) ?? num(p.event_count);
    if (rc != null) rowCount = rc;
    const fid = p.fidelity;
    if (fid && typeof fid === "object") {
      const fp = bool((fid as Record<string, unknown>).pass);
      if (fp != null) fidelityPass = fp;
    }
    const ad = num(p.ap_delta);
    if (ad != null) apDelta = ad;
    if (typeof p.generation === "string") generation = p.generation;
    if (ev.loop === "M" && ev.stage.includes("loop_m")) generation = "G1";
  }

  return { runId, worldSeed, rowCount, fidelityPass, apDelta, generation, threadId };
}

export function currentStageEvent(events: LabEvent[]): LabEvent | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const ev = events[i];
    if (ev.phase === "system") continue;
    if (ev.level === "stage" || ev.level === "loop" || ev.level === "hitl") return ev;
  }
  return events.length ? events[events.length - 1] : null;
}

interface UseLabStreamOptions {
  threadId?: string;
  enabled?: boolean;
}

export function useLabStream({ threadId = DEFAULT_THREAD_ID, enabled = true }: UseLabStreamOptions = {}) {
  const { setRunId } = useLatestRun();
  const [events, setEvents] = useState<LabEvent[]>([]);
  const [paused, setPaused] = useState(false);
  const [mode, setMode] = useState<StreamMode>("live");
  const [connected, setConnected] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  const pausedRef = useRef(paused);
  const bufferRef = useRef<LabEvent[]>([]);
  const seenKeysRef = useRef(new Set<string>());
  const setRunIdRef = useRef(setRunId);

  pausedRef.current = paused;
  setRunIdRef.current = setRunId;

  const eventKey = (ev: LabEvent) => `${ev.ts}|${ev.phase}|${ev.stage}|${ev.message}|${ev.level}`;

  const ingest = useCallback((ev: LabEvent) => {
    const key = eventKey(ev);
    if (seenKeysRef.current.has(key)) return;
    seenKeysRef.current.add(key);

    const runId = ev.payload?.run_id;
    if (typeof runId === "string" && runId) {
      setRunIdRef.current(runId);
    }

    if (pausedRef.current) {
      bufferRef.current.push(ev);
      return;
    }
    setEvents((prev) => [...prev, ev]);
    setStartedAt((s) => s ?? Date.now());
  }, []);

  const replaceEvents = useCallback((list: LabEvent[]) => {
    const normalized = list.map(normalizeEvent);
    seenKeysRef.current = new Set(normalized.map(eventKey));
    bufferRef.current = [];
    setEvents(normalized);
    setStartedAt(normalized.length ? Date.now() : null);
    for (const ev of normalized) {
      const runId = ev.payload?.run_id;
      if (typeof runId === "string" && runId) setRunIdRef.current(runId);
    }
  }, []);

  const hydrateFromHistory = useCallback(async () => {
    const res = await api.get<{ count: number; events: LabEvent[] }>(
      `/lab/history?thread_id=${encodeURIComponent(threadId)}`,
    );
    replaceEvents(res.events ?? []);
    return res.events?.length ?? 0;
  }, [replaceEvents, threadId]);

  const flushBuffer = useCallback(() => {
    if (!bufferRef.current.length) return;
    const chunk = bufferRef.current;
    bufferRef.current = [];
    setEvents((prev) => [...prev, ...chunk]);
    setStartedAt((s) => s ?? Date.now());
  }, []);

  const clearEvents = useCallback(() => {
    seenKeysRef.current.clear();
    bufferRef.current = [];
    setEvents([]);
    setStartedAt(null);
    setStreamError(null);
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const url = `/api/lab/stream?thread_id=${encodeURIComponent(threadId)}`;
    let es: EventSource | null = null;
    let closed = false;

    try {
      es = new EventSource(url);
    } catch {
      setStreamError("Failed to open SSE stream");
      setConnected(false);
      return;
    }

    es.onopen = () => {
      if (closed) return;
      setConnected(true);
      setStreamError(null);
    };

    es.onmessage = (msg) => {
      if (closed) return;
      try {
        const raw = JSON.parse(msg.data) as unknown;
        if (!isLabEvent(raw)) return;
        ingest(normalizeEvent(raw));
      } catch {
        // ignore malformed frames
      }
    };

    es.onerror = () => {
      if (closed) return;
      setConnected(false);
      // Don't spam — SSE is best-effort; history hydrate is the reliable path.
    };

    return () => {
      closed = true;
      es?.close();
      setConnected(false);
    };
  }, [threadId, enabled, ingest]);

  useEffect(() => {
    if (paused) return;
    flushBuffer();
  }, [paused, flushBuffer]);

  useEffect(() => {
    if (paused || !startedAt) return;
    const id = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(id);
  }, [paused, startedAt]);

  const phaseStatus = useMemo(() => derivePhaseStatus(events), [events]);
  const loopMarkers = useMemo(() => deriveLoopMarkers(events), [events]);
  const counters = useMemo(() => deriveCounters(events), [events]);
  const ledgerSnippets = useMemo(() => deriveLedgerSnippets(events), [events]);
  const meta = useMemo(() => extractMeta(events), [events]);
  const current = useMemo(() => currentStageEvent(events), [events]);

  const elapsedMs = startedAt != null ? Math.max(0, now - startedAt) : 0;

  const progress = useMemo(() => {
    const statuses = MACRO_PHASES.map((p) => phaseStatus[p]);
    const done = statuses.filter((s) => s === "completed").length;
    const active = statuses.some((s) => s === "active") ? 0.5 : 0;
    return Math.min(1, (done + active) / MACRO_PHASES.length);
  }, [phaseStatus]);

  const nextPhase = useMemo((): Exclude<LabPhase, "system"> | null => {
    for (const p of MACRO_PHASES) {
      const s: PhaseStatus = phaseStatus[p];
      if (s === "pending" || s === "failed") return p;
    }
    return null;
  }, [phaseStatus]);

  const setPausedSafe = useCallback(
    (v: boolean) => {
      setPaused(v);
      if (!v) flushBuffer();
    },
    [flushBuffer],
  );

  return {
    events,
    paused,
    setPaused: setPausedSafe,
    mode,
    setMode,
    connected,
    streamError,
    clearEvents,
    hydrateFromHistory,
    replaceEvents,
    phaseStatus,
    loopMarkers,
    counters,
    ledgerSnippets,
    meta,
    current,
    elapsedMs,
    progress,
    nextPhase,
    threadId,
  };
}
