import { useState } from "react";
import clsx from "clsx";
import { Button } from "@/components/ui/Button";
import { ApiError, api } from "@/lib/api-client";
import {
  DEFAULT_THREAD_ID,
  DEMO_BODY,
  MACRO_PHASES,
  type DemoRunResponse,
  type LabEvent,
  type LabPhase,
  type StreamMode,
} from "./lab-types";

function downloadJsonl(events: LabEvent[], filename: string) {
  const body = events.map((e) => JSON.stringify(e)).join("\n") + (events.length ? "\n" : "");
  const blob = new Blob([body], { type: "application/x-ndjson" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function errMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 404) {
      return "API missing /lab routes (404). Restart uvicorn from the repo root so it loads apps.api.routes.lab.";
    }
    return `API ${e.status}: ${e.message.slice(0, 180)}`;
  }
  if (e instanceof TypeError) {
    return "Cannot reach API — start uvicorn on :8000 (and Vite proxy /api → :8000).";
  }
  if (e instanceof Error) return e.message;
  return String(e);
}

async function sleep(ms: number) {
  await new Promise((r) => setTimeout(r, ms));
}

export function LabControls({
  mode,
  onModeChange,
  paused,
  onPausedChange,
  events,
  nextPhase,
  onBeforeRun,
  hydrateFromHistory,
  busy,
  setBusy,
  streamError,
  onActionError,
}: {
  mode: StreamMode;
  onModeChange: (m: StreamMode) => void;
  paused: boolean;
  onPausedChange: (p: boolean) => void;
  events: LabEvent[];
  nextPhase: Exclude<LabPhase, "system"> | null;
  onBeforeRun: () => void;
  hydrateFromHistory: () => Promise<number>;
  busy: boolean;
  setBusy: (b: boolean) => void;
  streamError: string | null;
  onActionError: (msg: string | null) => void;
}) {
  const [localBusy, setLocalBusy] = useState(false);
  const isBusy = busy || localBusy;

  const setAllBusy = (v: boolean) => {
    setLocalBusy(v);
    setBusy(v);
  };

  const pollHistoryUntilSettled = async (opts?: { maxMs?: number; intervalMs?: number }) => {
    const maxMs = opts?.maxMs ?? 180_000;
    const intervalMs = opts?.intervalMs ?? 1000;
    const t0 = Date.now();
    let lastCount = 0;
    while (Date.now() - t0 < maxMs) {
      const n = await hydrateFromHistory();
      lastCount = n;
      // Stop early once demo_end / demo_error appears in fetched history
      // (hydrate updates parent state asynchronously; re-fetch via API for check)
      const snap = await api.get<{ events: LabEvent[] }>(
        `/lab/history?thread_id=${encodeURIComponent(DEFAULT_THREAD_ID)}`,
      );
      const stages = (snap.events ?? []).map((e) => e.stage);
      if (stages.includes("demo_end") || stages.includes("demo_error")) {
        await hydrateFromHistory();
        return lastCount;
      }
      await sleep(intervalMs);
    }
    await hydrateFromHistory();
    return lastCount;
  };

  const runDemo = async () => {
    onActionError(null);
    setAllBusy(true);
    try {
      onBeforeRun();
      if (mode === "replay") {
        await api.post<DemoRunResponse>("/lab/replay", { thread_id: DEFAULT_THREAD_ID });
        const n = await hydrateFromHistory();
        if (!n) throw new Error("Replay returned 0 events — check data/demo/lab_trace.jsonl");
      } else {
        await api.post<DemoRunResponse>("/lab/demo", { ...DEMO_BODY });
        await pollHistoryUntilSettled({ maxMs: 240_000, intervalMs: 1200 });
      }
    } catch (e) {
      console.error(e);
      onActionError(errMessage(e));
    } finally {
      setAllBusy(false);
    }
  };

  const runStep = async () => {
    onActionError(null);
    const phase = nextPhase ?? "identify";
    setAllBusy(true);
    try {
      onBeforeRun();
      await api.post<DemoRunResponse>("/lab/demo", {
        ...DEMO_BODY,
        skip_identify: phase !== "identify",
        skip_generate: phase !== "generate",
        skip_defend: phase !== "defend",
        skip_evolve: true,
      });
      await pollHistoryUntilSettled({ maxMs: 180_000, intervalMs: 1000 });
    } catch (e) {
      console.error(e);
      onActionError(errMessage(e));
    } finally {
      setAllBusy(false);
    }
  };

  const switchMode = async (next: StreamMode) => {
    onModeChange(next);
    onActionError(null);
    if (next === "replay") {
      setAllBusy(true);
      try {
        onBeforeRun();
        await api.post<DemoRunResponse>("/lab/replay", { thread_id: DEFAULT_THREAD_ID });
        const n = await hydrateFromHistory();
        if (!n) throw new Error("Replay returned 0 events");
      } catch (e) {
        console.error(e);
        onActionError(errMessage(e));
      } finally {
        setAllBusy(false);
      }
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 justify-end">
      <div className="inline-flex rounded border border-border overflow-hidden mr-1">
        {(["live", "replay"] as const).map((m) => (
          <button
            key={m}
            type="button"
            disabled={isBusy}
            onClick={() => void switchMode(m)}
            className={clsx(
              "px-2.5 py-1.5 font-mono text-[11px] uppercase tracking-wide transition-colors",
              mode === m ? "bg-[#166534] text-white" : "bg-surface text-ink-muted hover:bg-surface-sunken",
            )}
          >
            {m}
          </button>
        ))}
      </div>

      <Button variant="primary" disabled={isBusy} onClick={() => void runDemo()} data-demo="run-lab-demo">
        {isBusy ? "Running…" : mode === "replay" ? "Replay fixture" : "Run full demo"}
      </Button>
      <Button variant="secondary" disabled={isBusy || mode === "replay"} onClick={() => void runStep()}>
        Run step{nextPhase ? ` (${nextPhase})` : ""}
      </Button>
      <Button variant="secondary" onClick={() => onPausedChange(!paused)}>
        {paused ? "Resume log" : "Pause log"}
      </Button>
      <Button
        variant="secondary"
        disabled={events.length === 0}
        onClick={() => downloadJsonl(events, `lab-trace-${DEFAULT_THREAD_ID}.jsonl`)}
      >
        Export JSONL
      </Button>

      {streamError ? (
        <button
          type="button"
          className="font-mono text-[11px] text-signal-watch underline"
          onClick={() => void switchMode("replay")}
        >
          SSE flaky — use REPLAY
        </button>
      ) : null}

      <span className="sr-only">phases: {MACRO_PHASES.join(",")}</span>
    </div>
  );
}
