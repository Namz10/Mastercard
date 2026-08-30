import { Link } from "react-router-dom";
import clsx from "clsx";
import type { CommandCenterLabEvent } from "./command-types";

function shortTs(ts: string): string {
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts.slice(11, 19) || ts;
    return d.toLocaleTimeString(undefined, { hour12: false });
  } catch {
    return ts;
  }
}

const LEVEL: Record<string, string> = {
  info: "text-ink-muted",
  stage: "text-signal-info",
  loop: "text-[#166534]",
  warn: "text-signal-watch",
  error: "text-signal-block",
  hitl: "text-ink",
};

export function LabPulse({ events }: { events: CommandCenterLabEvent[] }) {
  const rows = events.slice(-8).reverse();

  return (
    <section className="bg-white border border-border rounded-xl p-5 mb-8">
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="font-mono uppercase text-ink-faint text-xs tracking-wide">Lab pulse</div>
        <Link
          to="/simulation"
          className="font-mono text-[11px] text-[#166534] hover:underline underline-offset-2"
        >
          Open simulation →
        </Link>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-ink-muted">No recent lab events.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((ev, i) => (
            <li
              key={`${ev.ts}-${ev.stage}-${i}`}
              className="flex gap-3 text-sm border-b border-border/60 last:border-0 pb-2 last:pb-0"
            >
              <span className="font-mono text-[11px] text-ink-faint shrink-0 w-[72px]">
                {shortTs(ev.ts)}
              </span>
              <span className="font-mono text-[10px] uppercase text-ink-faint shrink-0 w-16">
                {ev.phase}
              </span>
              <span className={clsx("font-mono text-[11px] shrink-0 w-12", LEVEL[ev.level] ?? "text-ink-muted")}>
                {ev.level}
              </span>
              <span className="text-ink-muted truncate min-w-0">{ev.message}</span>
              {ev.loop ? (
                <span className="font-mono text-[10px] text-[#166534] shrink-0">L{ev.loop}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
