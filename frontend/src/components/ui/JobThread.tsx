import { useRef, useEffect } from "react";
import {
  Activity,
  BarChart3,
  Database,
  GitBranch,
  Layers3,
  RefreshCw,
  Shield,
  SlidersHorizontal,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import clsx from "clsx";
import type { OpsTapeLine } from "@/lib/ops-tape-types";

const VERB_META: Record<string, { icon: LucideIcon; label: string }> = {
  COLLECT: { icon: Database, label: "Collect" },
  COMMIT: { icon: Database, label: "Commit" },
  INJECT: { icon: GitBranch, label: "Inject" },
  FIDELITY: { icon: Shield, label: "Fidelity" },
  FIT: { icon: Activity, label: "Fit" },
  SCORE: { icon: BarChart3, label: "Score" },
  RETRAIN: { icon: RefreshCw, label: "Retrain" },
  TUNE: { icon: SlidersHorizontal, label: "Tune" },
  EXTRACT: { icon: Layers3, label: "Extract" },
  RANK: { icon: Layers3, label: "Rank" },
  GROUND: { icon: Sparkles, label: "Ground" },
  PROPOSE: { icon: Sparkles, label: "Propose" },
  REPLAY: { icon: Sparkles, label: "Replay" },
};

function ThreadIcon({ verb }: { verb: string }) {
  const meta = VERB_META[verb.toUpperCase()] ?? VERB_META.FIT;
  const Icon = meta.icon;
  return (
    <span className="catalog-thread-icon shrink-0" aria-hidden>
      <Icon className="w-4 h-4 text-sage-700" strokeWidth={1.75} />
    </span>
  );
}

export function JobThread({
  lines,
  running = false,
  title = "Simulating payment traffic",
  emptyLabel = "Starting…",
}: {
  lines: OpsTapeLine[];
  running?: boolean;
  title?: string;
  emptyLabel?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines.length, lines.map((l) => l.body).join("|")]);

  return (
    <div className="catalog-thread panel flex flex-col h-full min-h-0" data-demo="job-thread">
      <div className="h-9 px-3 border-b border-border flex items-center justify-between shrink-0">
        <span className="font-mono text-[11px] uppercase text-ink-faint">{title}</span>
        {running ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
      </div>
      <div ref={ref} className="flex-1 overflow-y-auto px-2 py-2">
        {lines.length === 0 ? (
          <div className="px-2 py-4 flex items-center gap-2 text-[12px] text-ink-faint">
            {running ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
            <span>{emptyLabel}</span>
          </div>
        ) : (
          <ol className="relative space-y-0">
            {lines.map((line, i) => {
              const isLast = i === lines.length - 1;
              const active = running && isLast;
              const done = !active && (line.status === "done" || line.status === "ok" || !running);
              return (
                <li
                  key={line.id}
                  className={clsx(
                    "catalog-thread-row row-insert relative flex gap-3 pl-1 pr-2 py-2.5 rounded-lg",
                    active && "bg-sage-100/50",
                    done && "opacity-90",
                  )}
                >
                  {i < lines.length - 1 ? (
                    <span className="catalog-thread-spine absolute left-[18px] top-9 bottom-0 w-px bg-border" aria-hidden />
                  ) : null}
                  <ThreadIcon verb={line.verb} />
                  <div className="min-w-0 flex-1 pt-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-[10px] uppercase tracking-wide text-sage-700 border border-sage-600/25 rounded px-1.5 py-px bg-sage-100/40">
                        {line.verb}
                      </span>
                      {line.clock ? (
                        <span className="font-mono text-[10px] text-ink-faint tabular-nums">{line.clock}</span>
                      ) : null}
                      {active ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
                    </div>
                    <p className={clsx("text-[13px] mt-1 leading-snug", active ? "text-ink" : "text-ink-muted")}>
                      {line.body}
                    </p>
                  </div>
                  <span className="font-mono text-[10px] uppercase text-ink-faint shrink-0 pt-1">
                    {done ? "ok" : active ? "…" : ""}
                  </span>
                </li>
              );
            })}
          </ol>
        )}
      </div>
      {!running && lines.length > 0 ? (
        <div className="h-8 px-3 border-t border-border flex items-center font-mono text-[10px] text-ink-faint uppercase">
          Thread complete
        </div>
      ) : null}
    </div>
  );
}
