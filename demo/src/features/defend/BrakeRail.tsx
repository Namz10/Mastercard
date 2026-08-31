import { COPY } from "@/lib/copy";
import { formatInt, formatPct } from "@/lib/format";
import type { ScoreMetrics } from "@/lib/api-types";

const ACTIONS: {
  key: string;
  label: string;
  color: string;
  reason: string;
}[] = [
  {
    key: "allow",
    label: COPY.policy.allow,
    color: "#3E6B4F",
    reason: "Genuine traffic under the FPR cap",
  },
  {
    key: "notify",
    label: COPY.policy.notify,
    color: "#8A5A00",
    reason: "APP / social engineering — tell the customer, do not silent-decline",
  },
  {
    key: "step_up",
    label: COPY.policy.stepUp,
    color: "#8A5A00",
    reason: "Extra authentication before the payment clears",
  },
  {
    key: "hold",
    label: COPY.policy.hold,
    color: "#55606B",
    reason: "Park the payment for analyst review",
  },
  {
    key: "decline",
    label: COPY.policy.decline,
    color: "#9C3B23",
    reason: "High-confidence block at this operating point",
  },
  {
    key: "mule_credit_restrict",
    label: COPY.policy.restrictPayeeCredit,
    color: "#191C19",
    reason: "Mule — freeze the beneficiary account, not the victim",
  },
];

export function BrakeRail({
  histogram,
  metrics,
}: {
  histogram: Record<string, number> | null;
  metrics?: ScoreMetrics | null;
}) {
  const max = Math.max(1, ...ACTIONS.map((a) => histogram?.[a.key] ?? 0));
  const recall = metrics ? (metrics.recall_at_op * 100).toFixed(2) : null;
  const fpr = metrics ? formatPct(metrics.genuine_fp, 3) : null;

  return (
    <div
      className="glass-sheet workspace-card-lift h-full flex flex-col min-h-[280px] lg:min-h-0 rounded-sheet"
      data-demo="brake-rail"
    >
      <div className="px-4 py-3 border-b border-border/60">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">{COPY.defend.interventions}</p>
        {recall && fpr ? (
          <p className="text-[13px] text-ink mt-1.5 leading-relaxed">
            At the operating point (recall {recall}% @ genuine FPR {fpr}%), the bank would do this — not only a fraud
            label.
          </p>
        ) : (
          <p className="text-[13px] text-ink-muted mt-1">Policy actions on holdout</p>
        )}
      </div>
      <div className="flex-1 px-3 py-2 space-y-2 overflow-y-auto min-h-0">
        {ACTIONS.map((a) => {
          const n = histogram?.[a.key] ?? 0;
          const w = histogram ? Math.max(2, (n / max) * 100) : 0;
          return (
            <div key={a.key} className="min-h-10 flex flex-col gap-0.5 py-1">
              <div className="h-8 flex items-center gap-2">
                <span className="w-[7.5rem] shrink-0 text-[11px] text-ink-muted truncate">{a.label}</span>
                <div className="flex-1 h-1.5 bg-sage-100/50 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none"
                    style={{ width: `${w}%`, background: a.color }}
                  />
                </div>
                <span className="w-14 text-right font-mono text-[11px] font-tabular text-ink-faint">
                  {histogram ? formatInt(n) : "—"}
                </span>
              </div>
              <p className="text-[12px] text-ink-faint pl-0 sm:pl-[7.5rem] leading-snug">{a.reason}</p>
            </div>
          );
        })}
      </div>
      <p className="px-4 py-2.5 text-[13px] text-ink-muted border-t border-border/60 leading-relaxed">
        APP → hold/notify, never silent decline. Mule → restrict payee credit.
      </p>
    </div>
  );
}
