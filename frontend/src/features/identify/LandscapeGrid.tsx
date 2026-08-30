import clsx from "clsx";
import type { MergedTechnique } from "@/lib/api-types";
import { coverageToChipStatus } from "@/lib/format";
import { StatusChip } from "@/components/ui/StatusChip";

export function LandscapeGrid({
  byCategory,
  categoryLabels,
  onSelect,
  highlightId,
  compact = false,
}: {
  byCategory: Record<number, MergedTechnique[]>;
  categoryLabels: Record<number, string>;
  onSelect: (t: MergedTechnique) => void;
  highlightId?: string | null;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="h-[72px] overflow-hidden border border-border rounded bg-surface flex gap-1 px-2 py-1">
        {Object.values(byCategory)
          .flat()
          .map((t) => (
            <button
              key={t.technique_id}
              type="button"
              onClick={() => onSelect(t)}
              className={clsx(
                "shrink-0 px-2 py-1 text-[10px] font-mono border border-border rounded-sm",
                highlightId === t.technique_id && "bg-sage-100 border-sage-600",
              )}
            >
              {t.technique_id}
            </button>
          ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-5 gap-3 h-full min-h-0">
      {[1, 2, 3, 4, 5].map((cat) => {
        const techniques = byCategory[cat] ?? [];
        return (
          <div key={cat} className="flex flex-col min-h-0 border border-border rounded bg-surface">
            <div className="px-2 py-1.5 border-b border-border text-[11px] font-mono uppercase text-ink-faint truncate">
              {categoryLabels[cat]}
            </div>
            <div className="flex-1 overflow-y-auto divide-y divide-border">
              {techniques.map((t) => {
                const status = coverageToChipStatus(t.coverage_status);
                const highlighted = highlightId === t.technique_id;
                return (
                  <button
                    key={t.technique_id}
                    type="button"
                    onClick={() => onSelect(t)}
                    className={clsx(
                      "w-full text-left px-2 py-1.5 hover:bg-surface-sunken transition-colors duration-100",
                      highlighted && "bg-sage-100",
                    )}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-mono text-[11px] text-ink-faint font-tabular">{t.technique_id}</span>
                      <StatusChip status={status} />
                    </div>
                    <div className="text-[12px] leading-snug text-ink truncate">{t.name}</div>
                  </button>
                );
              })}
              {techniques.length === 0 ? (
                <div className="px-2 py-4 text-center font-mono text-ink-faint">—</div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function LandscapeSkeleton() {
  return (
    <div className="grid grid-cols-5 gap-3 h-[calc(100vh-220px)]">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="border border-border rounded bg-surface flex items-center justify-center font-mono text-ink-faint">
          —
        </div>
      ))}
    </div>
  );
}
