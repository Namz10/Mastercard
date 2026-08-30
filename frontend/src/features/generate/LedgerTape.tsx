import { useRef, useEffect, useState } from "react";
import { Activity } from "lucide-react";
import type { GenerateRunResponse } from "@/lib/api-types";
import { Button } from "@/components/ui/Button";
import { COPY } from "@/lib/copy";
import { formatInr, formatInt } from "@/lib/format";
import { buildLedgerTape } from "@/lib/ledger-tape";
import clsx from "clsx";

const FAMILY_CHIP: Record<string, string> = {
  normal: "family-chip-quiet",
  mule: "family-chip-mule",
  identity_burst: "family-chip-identity",
  ato: "family-chip-ato",
  app_fraud: "family-chip-app",
  invoice_fraud: "family-chip-invoice",
};

const STATUS_CHIP: Record<string, string> = {
  Allow: "status-allow",
  Restrict: "status-restrict",
  Hold: "status-hold",
  Notify: "status-notify",
};

export function LedgerTape({
  run,
  running,
  seed,
  onSimulate,
  simulateDisabled,
}: {
  run: GenerateRunResponse | null;
  running: boolean;
  seed: number;
  onSimulate?: () => void;
  simulateDisabled?: boolean;
}) {
  const rows = buildLedgerTape(run?.counts_by_label_family, seed, 40);
  const ref = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);
  const [newCount, setNewCount] = useState(0);
  const prevLen = useRef(0);
  const [displayCount, setDisplayCount] = useState(0);

  useEffect(() => {
    if (rows.length > prevLen.current && !follow) setNewCount((n) => n + (rows.length - prevLen.current));
    prevLen.current = rows.length;
    const el = ref.current;
    if (follow && el) el.scrollTop = el.scrollHeight;
  }, [rows.length, follow]);

  useEffect(() => {
    const target = run?.event_count ?? rows.length;
    if (target === 0) {
      setDisplayCount(0);
      return;
    }
    const step = Math.max(1, Math.ceil(target / 14));
    const id = window.setInterval(() => {
      setDisplayCount((current) => {
        if (current >= target) {
          window.clearInterval(id);
          return target;
        }
        return Math.min(target, current + step);
      });
    }, 45);
    return () => window.clearInterval(id);
  }, [run?.event_count, rows.length]);

  const onScroll = () => {
    const el = ref.current;
    if (!el) return;
    if (el.scrollHeight - el.scrollTop - el.clientHeight > 40) setFollow(false);
  };

  const empty = rows.length === 0;

  return (
    <div
      className={clsx(
        "bento-panel tape-theater flex flex-col h-full min-h-[440px] lg:min-h-0 overflow-hidden",
        running && "tape-running",
      )}
      data-demo="ledger-tape"
    >
      <div className="px-4 h-10 border-b border-border/60 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className={clsx("tape-live-dot", !running && !run && "opacity-40 motion-reduce:opacity-40")} aria-hidden />
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">Payment tape</span>
        </div>
        <span className="font-mono text-[11px] text-ink-faint tabular-nums">
          {run ? (
            <>
              <span className="text-ink">{formatInt(displayCount)}</span>
              <span className="hidden sm:inline"> · last {rows.length}</span>
            </>
          ) : running ? (
            "committing…"
          ) : (
            "awaiting run"
          )}
        </span>
      </div>

      <div className="relative flex-1 min-h-0">
        <div className="tape-fade-top pointer-events-none" aria-hidden />
        <div className="tape-fade-bottom pointer-events-none" aria-hidden />

        <div ref={ref} onScroll={onScroll} className="h-full overflow-y-auto tape-scroll">
          {empty ? (
            <div className="h-full min-h-[360px] flex items-center justify-center px-6">
              <div className="max-w-md text-center space-y-5">
                <div className="mx-auto w-16 h-16 rounded-[18px] bg-sage-100/80 border border-sage-600/20 flex items-center justify-center">
                  <Activity className="w-7 h-7 text-sage-600" strokeWidth={1.5} />
                </div>
                <div className="space-y-2">
                  <p className="font-serif text-[26px] font-medium text-ink tracking-tight leading-tight">
                    {running ? "Committing corpus…" : "Watch payment traffic flow"}
                  </p>
                  <p className="text-[14px] text-ink-muted leading-relaxed max-w-[34ch] mx-auto">{COPY.generate.empty}</p>
                </div>
                {running ? (
                  <p className="font-mono text-[12px] text-sage-600 animate-pulse motion-reduce:animate-none">
                    Seeding ledger from approved recipes…
                  </p>
                ) : (
                  <>
                    <p className="font-mono text-[11px] text-ink-faint uppercase tracking-wide">
                      seed {seed} · reproducible
                    </p>
                    {onSimulate ? (
                      <Button
                        variant="primary"
                        className="h-11 px-7 mt-1"
                        disabled={simulateDisabled}
                        onClick={onSimulate}
                        data-demo="simulate-hero"
                      >
                        {COPY.generate.primary}
                      </Button>
                    ) : null}
                  </>
                )}
              </div>
            </div>
          ) : (
            <table className="w-full text-[12px] table-fixed">
              <thead className="sticky top-0 z-[2] tape-thead">
                <tr className="text-left text-[10px] uppercase tracking-wider text-ink-faint font-sans">
                  <th className="px-4 h-9 w-[88px] font-medium hidden md:table-cell">Time</th>
                  <th className="px-3 h-9 w-[112px] font-medium">Family</th>
                  <th className="px-3 h-9 font-medium hidden sm:table-cell">Payer / beneficiary</th>
                  <th className="px-3 h-9 w-[112px] text-right font-medium">Amount</th>
                  <th className="px-4 h-9 w-[80px] font-medium hidden sm:table-cell">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="tape-row row-insert border-t border-border/40 h-11">
                    <td className="px-4 font-mono text-[11px] text-ink-faint font-tabular hidden md:table-cell">
                      {row.clock}
                    </td>
                    <td className="px-3">
                      <span
                        className={clsx(
                          "family-chip inline-block max-w-full truncate",
                          FAMILY_CHIP[row.family] ?? "family-chip-quiet",
                        )}
                      >
                        {row.familyLabel}
                      </span>
                    </td>
                    <td className="px-3 font-mono text-[11px] text-ink-muted truncate hidden sm:table-cell">
                      {row.parties}
                    </td>
                    <td className="px-3 text-right font-mono font-semibold font-tabular text-[15px] text-ink tracking-tight">
                      {formatInr(row.amount)}
                    </td>
                    <td className="px-4 hidden sm:table-cell">
                      <span className={clsx("tape-status", STATUS_CHIP[row.status] ?? "status-allow")}>
                        {row.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {!follow && newCount > 0 ? (
        <button
          type="button"
          className="h-8 border-t border-border/60 text-[11px] font-mono text-accent bg-accent-muted/30 hover:bg-accent-muted/60 transition-colors"
          onClick={() => {
            setFollow(true);
            setNewCount(0);
          }}
        >
          {COPY.logPill(newCount)}
        </button>
      ) : null}
    </div>
  );
}
