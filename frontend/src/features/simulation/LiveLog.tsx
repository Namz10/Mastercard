import { useEffect, useRef } from "react";
import clsx from "clsx";
import type { LabEvent, LabLevel } from "./lab-types";

const LEVEL_COLOR: Record<LabLevel, string> = {
  info: "text-ink-muted",
  stage: "text-signal-info",
  loop: "text-[#166534]",
  warn: "text-signal-watch",
  error: "text-signal-block",
  hitl: "text-purple-700",
};

function formatTs(ts: string): string {
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts.slice(11, 23) || ts;
    const hh = String(d.getUTCHours()).padStart(2, "0");
    const mm = String(d.getUTCMinutes()).padStart(2, "0");
    const ss = String(d.getUTCSeconds()).padStart(2, "0");
    const ms = String(d.getUTCMilliseconds()).padStart(3, "0");
    return `${hh}:${mm}:${ss}.${ms}`;
  } catch {
    return ts;
  }
}

function payloadBits(payload: Record<string, unknown>): string {
  const keys = ["run_id", "world_seed", "row_count", "event_count", "pass", "ap_delta", "trigger", "node", "family"];
  const parts: string[] = [];
  for (const k of keys) {
    if (!(k in payload)) continue;
    const v = payload[k];
    if (v == null || typeof v === "object") continue;
    parts.push(`${k}=${String(v)}`);
  }
  if (payload.fidelity && typeof payload.fidelity === "object") {
    const f = payload.fidelity as Record<string, unknown>;
    if ("pass" in f) parts.push(`fidelity.pass=${String(f.pass)}`);
  }
  return parts.slice(0, 4).join(" · ");
}

export function LiveLog({
  events,
  paused,
  metaChips,
}: {
  events: LabEvent[];
  paused: boolean;
  metaChips: { label: string; value: string }[];
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length, paused]);

  return (
    <div className="bg-surface border border-border rounded p-5 h-full min-h-[280px] flex flex-col">
      <div className="flex items-center justify-between mb-3 gap-2">
        <div className="font-mono uppercase text-ink-faint text-xs tracking-wide">Live log</div>
        <div className="flex items-center gap-2">
          {paused ? (
            <span className="font-mono text-[10px] text-signal-watch uppercase">paused</span>
          ) : (
            <span className="font-mono text-[10px] text-[#166534] uppercase flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[#166534] animate-pulse" />
              streaming
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-3">
        {metaChips.map((c) => (
          <span
            key={c.label}
            className="font-mono text-[10px] px-2 py-0.5 rounded-sm border border-border bg-surface-sunken text-ink-muted"
          >
            {c.label}={c.value}
          </span>
        ))}
      </div>

      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto max-h-[420px] font-mono text-[11px] leading-relaxed space-y-0.5 pr-1"
      >
        {events.length === 0 ? (
          <div className="text-ink-faint py-8 text-center">No events yet — run the demo or switch to REPLAY.</div>
        ) : (
          events.map((ev, i) => {
            const bits = payloadBits(ev.payload);
            return (
              <div
                key={`${ev.ts}-${i}`}
                id={`lab-event-${i}`}
                data-phase={ev.phase}
                className={clsx("whitespace-pre-wrap break-words", LEVEL_COLOR[ev.level] ?? "text-ink-muted")}
              >
                <span className="text-ink-faint">[{formatTs(ev.ts)}]</span>{" "}
                <span>[{ev.phase.toUpperCase()}]</span>{" "}
                {ev.loop ? <span>[Loop {ev.loop}] </span> : null}
                <span>[{ev.level.toUpperCase()}]</span> {ev.message}
                {bits ? <span className="text-ink-faint"> · {bits}</span> : null}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

/** Scroll the live log to the first event for a macro phase. */
export function scrollLogToPhase(phase: string) {
  const el = document.querySelector(`[data-phase="${phase}"]`);
  el?.scrollIntoView({ behavior: "smooth", block: "center" });
}
