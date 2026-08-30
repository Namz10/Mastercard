import { useEffect, useState } from "react";
import type { LabEvent } from "./lab-types";

function formatElapsed(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  const frac = Math.floor((ms % 1000) / 10);
  if (m > 0) return `${m}:${String(rem).padStart(2, "0")}.${String(frac).padStart(2, "0")}`;
  return `${rem}.${String(frac).padStart(2, "0")}s`;
}

export function StageCard({
  current,
  progress,
  elapsedMs,
}: {
  current: LabEvent | null;
  progress: number;
  elapsedMs: number;
}) {
  const [tick, setTick] = useState(elapsedMs);
  useEffect(() => {
    setTick(elapsedMs);
  }, [elapsedMs]);

  const stageName = current?.stage ?? "idle";
  const phase = current?.phase?.toUpperCase() ?? "—";
  const loop = current?.loop;
  const tech = current?.tech ?? [];

  return (
    <div className="bg-surface border border-border rounded p-5 h-full min-h-[280px] flex flex-col">
      <div className="font-mono uppercase text-ink-faint text-xs mb-3 tracking-wide">Current stage</div>

      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="font-mono text-[11px] text-ink-muted mb-1">{phase}</div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink break-all">{stageName}</h2>
        </div>
        {loop ? (
          <span className="shrink-0 font-mono text-xs px-2.5 py-1 rounded border border-[#166534] text-[#166534] bg-green-50">
            Loop {loop}
          </span>
        ) : null}
      </div>

      {current?.message ? (
        <p className="text-sm text-ink-muted mb-4 line-clamp-3">{current.message}</p>
      ) : (
        <p className="text-sm text-ink-faint mb-4">Waiting for lab events…</p>
      )}

      <div className="flex flex-wrap gap-1.5 mb-4">
        {tech.length === 0 ? (
          <span className="font-mono text-[11px] text-ink-faint">no tech chips yet</span>
        ) : (
          tech.map((t) => (
            <span
              key={t}
              className="font-mono text-[11px] px-2 py-0.5 rounded-sm border border-border bg-surface-sunken text-ink-muted"
            >
              {t}
            </span>
          ))
        )}
      </div>

      <div className="mt-auto space-y-2">
        <div className="flex justify-between font-mono text-[11px] text-ink-muted">
          <span>progress</span>
          <span>{Math.round(progress * 100)}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-surface-sunken overflow-hidden">
          <div
            className="h-full rounded-full bg-[#166534] transition-[width] duration-300"
            style={{ width: `${Math.round(progress * 100)}%` }}
          />
        </div>
        <div className="font-mono text-sm text-ink tabular-nums">
          elapsed <span className="text-[#166534]">{formatElapsed(tick)}</span>
        </div>
      </div>
    </div>
  );
}
