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
    <div className="h-full border border-border rounded bg-surface flex flex-col min-h-0">
      <div className="px-3 py-2 border-b border-border text-[13px]">{COPY.defend.interventions}</div>
      <div className="flex-1 px-3 py-2 space-y-2 overflow-y-auto">
        {ACTIONS.map((a) => {
          const n = histogram?.[a.key] ?? 0;
          const w = histogram ? Math.max(2, (n / max) * 100) : 0;
          return (
            <div key={a.key} className="h-9 flex items-center gap-2">
              <span className="w-28 shrink-0 text-[12px]">{a.label}</span>
              <div className="flex-1 h-1 bg-paper-0">
                <div className="h-1" style={{ width: `${w}%`, background: a.color }} />
              </div>
              <span className="w-16 text-right font-mono text-[12px] font-tabular">{histogram ? formatInt(n) : "—"}</span>
            </div>
          );
        })}
      </div>
      <p className="px-3 py-2 text-[11px] text-ink-faint border-t border-border">
        APP → hold/notify, never silent decline. Mule → restrict payee credit.
      </p>
    </div>
  );
}
