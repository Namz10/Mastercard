import clsx from "clsx";
import type { MergedTechnique } from "@/lib/api-types";
import { coverageToChipStatus } from "@/lib/format";
import { StatusChip } from "@/components/ui/StatusChip";

export function TechniqueGrid({
  techniques,
  onSelect,
  selectedId,
}: {
  techniques: MergedTechnique[];
  onSelect: (t: MergedTechnique) => void;
  selectedId?: string | null;
}) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
      {techniques.map((t) => {
        const status = coverageToChipStatus(t.coverage_status);
        const borderColor =
          status === "live_rule"
            ? "border-l-signal-safe"
            : status === "draft_rule"
              ? "border-l-signal-watch"
              : status === "named_gap" || status === "case_only"
                ? "border-l-signal-idle"
                : status === "empty"
                  ? "border-l-border"
                  : "border-l-signal-block";

        return (
          <button
            key={t.technique_id}
            type="button"
            onClick={() => onSelect(t)}
            className={clsx(
              "group text-left bg-surface border border-border rounded px-3 py-2.5 border-l-[6px] transition-colors hover:bg-surface-sunken",
              borderColor,
              selectedId === t.technique_id && "ring-2 ring-signal-info ring-offset-1",
            )}
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="font-mono text-xs text-ink-faint">{t.technique_id}</span>
              <StatusChip status={status} />
            </div>
            <div className="text-sm font-medium leading-snug truncate">{t.name}</div>
            <div className="mt-1 text-[11px] text-ink-faint font-mono truncate opacity-0 group-hover:opacity-100 motion-safe:transition-opacity motion-safe:duration-150 underline decoration-border underline-offset-2">
              {t.features_expected.slice(0, 2).join(" · ") || t.scout_topic_hint || "No evidence span yet"}
            </div>
          </button>
        );
      })}
    </div>
  );
}

export function TechniqueGridSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
      {Array.from({ length: 24 }).map((_, i) => (
        <div key={i} className="h-[72px] bg-surface-sunken border border-border rounded animate-pulse" />
      ))}
    </div>
  );
}
