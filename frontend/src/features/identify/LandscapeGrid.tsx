import clsx from "clsx";
import { Bot, MessageSquare, Network, Shield, UserRound } from "lucide-react";
import type { MergedTechnique } from "@/lib/api-types";
import { coverageToChipStatus } from "@/lib/format";
import { StatusChip } from "@/components/ui/StatusChip";

const CATEGORIES = [1, 2, 3, 4, 5] as const;

const CATEGORY_ICONS = {
  1: Network,
  2: UserRound,
  3: MessageSquare,
  4: Bot,
  5: Shield,
} as const;

function TechniqueCell({
  technique: t,
  highlighted,
  onSelect,
}: {
  technique: MergedTechnique;
  highlighted: boolean;
  onSelect: (t: MergedTechnique) => void;
}) {
  const status = coverageToChipStatus(t.coverage_status);
  const gap = status === "named_gap" || status === "empty" || status === "case_only";
  const live = status === "live_rule";

  return (
    <button
      type="button"
      ref={highlighted ? (el) => el?.scrollIntoView({ block: "nearest" }) : undefined}
      onClick={() => onSelect(t)}
      className={clsx(
        "workspace-card-lift relative w-full h-full text-left px-2.5 py-2 min-h-9 overflow-hidden",
        live && "rounded-xl bg-sage-100/95 border border-sage-600/35 shadow-[inset_3px_0_0_var(--sage-600)]",
        gap && "rounded-xl bg-white/40 border-2 border-dashed border-border/70 shadow-none",
        !live && !gap && "rounded-xl bg-surface-solid/80 border border-border",
        highlighted && "ring-2 ring-accent/40 border-accent/40",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent",
      )}
    >
      {!gap ? (
        <span
          className={clsx(
            "absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full",
            live && "bg-sage-600",
            !live && "bg-signal-watch/70",
          )}
          aria-hidden
        />
      ) : null}
      <div className={clsx("pl-1.5", gap && "opacity-80")}>
        <div className="flex items-center justify-between gap-1">
          <span
            className={clsx(
              "font-mono text-[11px] font-tabular",
              live ? "text-sage-700" : gap ? "text-ink-faint" : "text-ink-faint",
            )}
          >
            {t.technique_id}
          </span>
          <StatusChip status={status} />
        </div>
        <div
          className={clsx(
            "text-[13px] leading-snug mt-0.5 line-clamp-2",
            live ? "text-ink font-semibold" : gap ? "text-ink-faint font-normal" : "text-ink-muted",
          )}
        >
          {t.name}
        </div>
      </div>
    </button>
  );
}

export function LandscapeGrid({
  byCategory,
  categoryLabels,
  onSelect,
  highlightId,
  compact = false,
  loading = false,
}: {
  byCategory: Record<number, MergedTechnique[]>;
  categoryLabels: Record<number, string>;
  onSelect: (t: MergedTechnique) => void;
  highlightId?: string | null;
  compact?: boolean;
  loading?: boolean;
}) {
  if (compact) {
    return (
      <div className="bento-panel h-[72px] overflow-hidden flex gap-1.5 px-2 py-1.5">
        {Object.values(byCategory)
          .flat()
          .map((t) => (
            <button
              key={t.technique_id}
              type="button"
              onClick={() => onSelect(t)}
              className={clsx(
                "shrink-0 px-2 py-1 text-[10px] font-mono rounded-full transition-colors duration-100",
                highlightId === t.technique_id
                  ? "bg-accent text-accent-fg"
                  : "glass-control text-ink-muted hover:text-ink",
              )}
            >
              {t.technique_id}
            </button>
          ))}
      </div>
    );
  }

  const maxRows = Math.max(...CATEGORIES.map((cat) => (byCategory[cat] ?? []).length), loading ? 4 : 0);

  return (
    <div className="bento-panel flex flex-col h-full min-h-0 overflow-hidden">
      <div className="sticky top-0 z-10 grid grid-cols-5 shrink-0 border-b border-border bg-surface-solid/90">
        {CATEGORIES.map((cat) => {
          const Icon = CATEGORY_ICONS[cat];
          return (
            <div
              key={cat}
              className="h-9 px-2.5 flex items-center gap-1.5 text-[11px] font-mono uppercase tracking-wide text-ink-faint truncate"
            >
              <Icon className="w-3.5 h-3.5 shrink-0 text-sage-700" strokeWidth={1.75} aria-hidden />
              <span className="truncate">{categoryLabels[cat]}</span>
            </div>
          );
        })}
      </div>
      <div className="flex-1 overflow-y-auto min-h-0 p-2">
        <div
          className="grid grid-cols-5 gap-x-2 gap-y-1.5"
          style={{ gridTemplateRows: maxRows > 0 ? `repeat(${maxRows}, minmax(2.25rem, auto))` : undefined }}
        >
          {Array.from({ length: maxRows }).map((_, rowIdx) =>
            CATEGORIES.map((cat) => {
              const t = (byCategory[cat] ?? [])[rowIdx];
              if (!t) {
                return (
                  <div
                    key={`${cat}-${rowIdx}`}
                    className="min-h-9 rounded-xl border border-dashed border-border/70 flex items-center justify-center font-mono text-[12px] text-ink-faint"
                    aria-hidden
                  >
                    —
                  </div>
                );
              }
              return (
                <TechniqueCell
                  key={t.technique_id}
                  technique={t}
                  highlighted={highlightId === t.technique_id}
                  onSelect={onSelect}
                />
              );
            }),
          )}
        </div>
      </div>
    </div>
  );
}

export function LandscapeSkeleton() {
  return (
    <div className="bento-panel grid grid-cols-5 gap-2 h-[calc(100vh-220px)] p-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-dashed border-border flex items-center justify-center font-mono text-ink-faint min-h-[120px]">
          —
        </div>
      ))}
    </div>
  );
}
