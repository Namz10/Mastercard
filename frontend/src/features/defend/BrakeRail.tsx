import { COPY } from "@/lib/copy";
import { formatInt } from "@/lib/format";

const ACTIONS: { key: string; label: string; color: string }[] = [
  { key: "allow", label: COPY.policy.allow, color: "#3E6B4F" },
  { key: "notify", label: COPY.policy.notify, color: "#8A5A00" },
  { key: "step_up", label: COPY.policy.stepUp, color: "#8A5A00" },
  { key: "hold", label: COPY.policy.hold, color: "#55606B" },
  { key: "decline", label: COPY.policy.decline, color: "#9C3B23" },
  { key: "mule_credit_restrict", label: COPY.policy.restrictPayeeCredit, color: "#191C19" },
];

export function BrakeRail({ histogram }: { histogram: Record<string, number> | null }) {
  const max = Math.max(1, ...ACTIONS.map((a) => histogram?.[a.key] ?? 0));
  return (
    <div className="glass-sheet workspace-card-lift h-full flex flex-col min-h-[280px] lg:min-h-0 rounded-sheet" data-demo="brake-rail">
      <div className="px-3 py-2.5 border-b border-border/60">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">{COPY.defend.interventions}</p>
        <p className="text-[11px] text-ink-faint mt-0.5">Policy actions on holdout</p>
      </div>
      <div className="flex-1 px-3 py-2 space-y-1.5 overflow-y-auto min-h-0">
        {ACTIONS.map((a) => {
          const n = histogram?.[a.key] ?? 0;
          const w = histogram ? Math.max(2, (n / max) * 100) : 0;
          return (
            <div key={a.key} className="h-8 flex items-center gap-2">
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
          );
        })}
      </div>
      <p className="px-3 py-2 text-[10px] text-ink-faint border-t border-border/60 leading-relaxed">
        APP → hold/notify, never silent decline. Mule → restrict payee credit.
      </p>
    </div>
  );
}
