import type { GenerateRunResponse } from "@/lib/api-types";
import { FAMILY_LABEL, formatInt } from "@/lib/format";
import { COPY } from "@/lib/copy";

const FAMILY_ORDER = ["normal", "mule", "identity_burst", "ato", "app_fraud", "invoice_fraud"];

export function LedgerTape({
  run,
  running,
}: {
  run: GenerateRunResponse | null;
  running: boolean;
}) {
  const rows = Object.entries(run?.counts_by_label_family ?? {}).sort(
    (a, b) => FAMILY_ORDER.indexOf(a[0]) - FAMILY_ORDER.indexOf(b[0]),
  );

  return (
    <div className="flex flex-col h-full border border-border rounded bg-surface min-h-0">
      <div className="px-3 py-2 border-b border-border flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase text-ink-faint">Payment tape</span>
        <span className="font-mono text-[11px] text-ink-faint">
          {run ? `${formatInt(run.event_count)} events` : running ? "committing…" : "idle"}
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 bg-paper-0">
            <tr className="text-left text-[11px] uppercase text-ink-faint font-sans">
              <th className="px-3 py-2">Family</th>
              <th className="px-3 py-2 text-right font-mono">Count</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([family, count]) => (
              <tr key={family} className="border-t border-border h-9">
                <td className="px-3">{FAMILY_LABEL[family] ?? family}</td>
                <td className="px-3 text-right font-mono font-tabular">{formatInt(count)}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={2} className="px-3 py-8 text-ink-faint">
                  {COPY.generate.empty}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}
