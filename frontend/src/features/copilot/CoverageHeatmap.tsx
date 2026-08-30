import { useMemo } from "react";
import clsx from "clsx";
import { CATEGORY_LABELS, techniqueCategory } from "@/lib/format";
import type { CoverageCellSnapshot } from "./command-types";

const CELL_STYLE: Record<string, string> = {
  live_rule: "bg-[#166534] text-white border-[#166534]",
  draft_rule: "bg-[#CA8A04] text-white border-[#CA8A04]",
  draft: "bg-[#CA8A04] text-white border-[#CA8A04]",
  named_gap: "bg-[#E5E7EB] text-ink-muted border-[#E5E7EB]",
  case_only: "bg-[#F3F4F6] text-ink-faint border-dashed border-border",
  empty: "bg-white text-ink-faint border-border",
};

const LEGEND = [
  { key: "live_rule", label: "live_rule", className: "bg-[#166534]" },
  { key: "draft", label: "draft", className: "bg-[#CA8A04]" },
  { key: "named_gap", label: "named_gap", className: "bg-[#E5E7EB] border border-border" },
  {
    key: "case_only",
    label: "case_only",
    className: "bg-[#F3F4F6] border border-dashed border-border",
  },
];

function cellClass(status: string): string {
  return CELL_STYLE[status] ?? CELL_STYLE.empty;
}

export function CoverageHeatmap({ cells }: { cells: CoverageCellSnapshot[] }) {
  const byCategory = useMemo(() => {
    const map = new Map<number, CoverageCellSnapshot[]>();
    const byId = new Map(cells.map((c) => [c.technique_id, c]));

    for (let n = 1; n <= 24; n++) {
      const id = `T${String(n).padStart(2, "0")}`;
      const cat = techniqueCategory(id);
      const existing = byId.get(id);
      const cell: CoverageCellSnapshot = existing ?? {
        technique_id: id,
        vector_id: null,
        name: null,
        status: null,
        generate_mode: null,
        coverage_status: "empty",
      };
      const list = map.get(cat) ?? [];
      list.push(cell);
      map.set(cat, list);
    }
    return map;
  }, [cells]);

  const categories = Object.keys(CATEGORY_LABELS)
    .map(Number)
    .sort((a, b) => a - b);

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const c of cells) {
      const st = c.coverage_status || "empty";
      counts[st] = (counts[st] ?? 0) + 1;
    }
    return counts;
  }, [cells]);

  return (
    <section className="bg-white border border-border rounded-xl p-5 h-full">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="font-mono uppercase text-ink-faint text-xs tracking-wide">
          KillChain Atlas coverage (T01–T24)
        </div>
        <div className="flex flex-wrap gap-2">
          {LEGEND.map((l) => (
            <span key={l.key} className="inline-flex items-center gap-1.5 font-mono text-[10px] text-ink-muted">
              <span className={clsx("h-2.5 w-2.5 rounded-sm", l.className)} />
              {l.label}
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-5">
        {categories.map((cat) => {
          const group = byCategory.get(cat) ?? [];
          return (
            <div key={cat}>
              <div className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-2">
                {CATEGORY_LABELS[cat]}
              </div>
              <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-1.5">
                {group.map((cell) => (
                  <div
                    key={cell.technique_id}
                    title={`${cell.technique_id} · ${cell.coverage_status}${cell.name ? ` · ${cell.name}` : ""}${cell.scout_topic_hint ? ` · ${cell.scout_topic_hint}` : ""}`}
                    className={clsx(
                      "aspect-square min-h-[36px] rounded-md border flex flex-col items-center justify-center px-1",
                      cellClass(cell.coverage_status),
                    )}
                  >
                    <span className="font-mono text-[10px] font-medium leading-none">
                      {cell.technique_id}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-4 font-mono text-[11px] text-ink-faint">
        live_rule: {statusCounts.live_rule ?? 0} · draft: {statusCounts.draft_rule ?? 0} · named_gap:{" "}
        {statusCounts.named_gap ?? 0} · case_only: {statusCounts.case_only ?? 0} · empty:{" "}
        {statusCounts.empty ?? 0}
      </p>
    </section>
  );
}
