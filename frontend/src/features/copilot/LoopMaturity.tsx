import clsx from "clsx";
import type { CommandCenterLoop } from "./command-types";

const STATUS_STYLE: Record<string, string> = {
  live: "border-[#166534] text-[#166534] bg-green-50",
  partial: "border-signal-watch text-signal-watch bg-amber-50/50",
  roadmap: "border-border text-ink-muted bg-surface-sunken",
  offline: "border-border text-ink-faint bg-surface",
  writeup: "border-border text-ink-muted bg-surface",
};

const ORDER = ["I", "C", "M", "T", "R", "A", "F", "G", "H"];

export function LoopMaturity({ loops }: { loops: Record<string, CommandCenterLoop> }) {
  const rows = ORDER.filter((id) => loops[id]).map((id) => ({ id, ...loops[id] }));
  // Include any unexpected keys
  for (const id of Object.keys(loops)) {
    if (!ORDER.includes(id)) rows.push({ id, ...loops[id] });
  }

  return (
    <section className="bg-white border border-border rounded-xl p-5 mb-8">
      <div className="font-mono uppercase text-ink-faint text-xs tracking-wide mb-1">
        Loop maturity
      </div>
      <p className="text-xs text-ink-muted mb-4">
        Honest status from lab evidence — roadmap / offline are not sold as live.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left font-mono text-[10px] uppercase text-ink-faint border-b border-border">
              <th className="py-2 pr-3 font-medium">Loop</th>
              <th className="py-2 pr-3 font-medium">Name</th>
              <th className="py-2 pr-3 font-medium">Status</th>
              <th className="py-2 font-medium">Evidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-border/60 last:border-0">
                <td className="py-2.5 pr-3 font-mono text-xs font-semibold text-[#166534]">
                  {row.id}
                </td>
                <td className="py-2.5 pr-3 text-ink">{row.name}</td>
                <td className="py-2.5 pr-3">
                  <span
                    className={clsx(
                      "inline-flex font-mono text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-sm border",
                      STATUS_STYLE[row.status] ?? STATUS_STYLE.roadmap,
                    )}
                  >
                    {row.status}
                  </span>
                </td>
                <td className="py-2.5 font-mono text-[11px] text-ink-muted">{row.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
