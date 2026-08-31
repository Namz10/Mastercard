import clsx from "clsx";
import { Building2, GraduationCap, Newspaper, Globe } from "lucide-react";
import { hostFromUrl, sourceTier, sourceTitle } from "@/lib/discover-catalog-map";

const TIER_ICON = {
  regulator: Building2,
  academic: GraduationCap,
  news: Newspaper,
  other: Globe,
} as const;

export function CatalogSourceDeck({
  sources,
  running = false,
}: {
  sources: string[];
  running?: boolean;
}) {
  return (
    <div className="catalog-source-deck panel flex flex-col h-full min-h-0" data-demo="source-cards">
      <div className="h-9 px-3 border-b border-border font-mono text-[11px] uppercase text-ink-faint flex items-center gap-2">
        {running && sources.length === 0 ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
        Catalog sources · {sources.length}
      </div>
      <ul className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {sources.map((url) => {
          const host = hostFromUrl(url);
          const tier = sourceTier(host);
          const TierIcon = TIER_ICON[tier];
          const title = sourceTitle(url);
          return (
            <li
              key={url}
              className="catalog-source-card row-insert flex items-start gap-3 p-2.5 rounded-lg border border-border/80 bg-surface-solid/90 hover:border-sage-600/30 hover:bg-sage-100/20 transition-colors duration-100"
            >
              <div className="relative shrink-0">
                <img
                  src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=32`}
                  alt=""
                  width={20}
                  height={20}
                  className="rounded-sm mt-0.5"
                  loading="lazy"
                />
                <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-paper-1 border border-border flex items-center justify-center">
                  <TierIcon className="w-2.5 h-2.5 text-sage-700" strokeWidth={2} />
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium text-ink leading-tight">{title}</p>
                <p className="font-mono text-[10px] text-ink-faint mt-0.5 truncate">{host}</p>
                <span
                  className={clsx(
                    "inline-block mt-1.5 font-mono text-[9px] uppercase tracking-wide px-1.5 py-px rounded border",
                    tier === "regulator" && "text-sage-700 border-sage-600/30 bg-sage-100/50",
                    tier === "academic" && "text-ink-muted border-border bg-surface",
                    tier === "news" && "text-ochre-700 border-ochre-700/20 bg-surface",
                    tier === "other" && "text-ink-faint border-border",
                  )}
                >
                  {tier}
                </span>
              </div>
            </li>
          );
        })}
        {sources.length === 0 ? (
          <li className="px-2 py-6 text-center text-[12px] text-ink-faint">
            Sources attach as collectors find allowlisted URLs…
          </li>
        ) : null}
      </ul>
    </div>
  );
}
