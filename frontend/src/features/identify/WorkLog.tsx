import type { OpsTapeLine } from "@/components/ui/OpsTape";
import { OpsTape } from "@/components/ui/OpsTape";

/** @deprecated use OpsTapeLine from @/components/ui/OpsTape */
export type LogLine = OpsTapeLine;

export function WorkLog(props: React.ComponentProps<typeof OpsTape>) {
  return <OpsTape {...props} variant="rail" />;
}

function hostFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function SourceCards({ sources, running = false }: { sources: string[]; running?: boolean }) {
  return (
    <div className="panel flex flex-col h-full min-h-0" data-demo="source-cards">
      <div className="h-9 px-3 border-b border-border font-mono text-[11px] uppercase text-ink-faint flex items-center gap-2">
        {running && sources.length === 0 ? <span className="tape-live-dot shrink-0" aria-hidden /> : null}
        Sources ({sources.length})
      </div>
      <ul className="flex-1 overflow-y-auto">
        {sources.map((url) => {
          const host = hostFromUrl(url);
          return (
            <li
              key={url}
              className="row-insert min-h-9 px-3 py-2 flex items-center gap-2.5 border-b border-border hover:bg-accent-muted/40 transition-colors"
            >
              <img
                src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(host)}&sz=32`}
                alt=""
                width={16}
                height={16}
                className="shrink-0 rounded-sm"
                loading="lazy"
              />
              <div className="min-w-0 flex-1">
                <p className="text-[12px] font-medium text-ink truncate">{host}</p>
                <p className="font-mono text-[10px] text-ink-faint truncate">{url}</p>
              </div>
            </li>
          );
        })}
        {sources.length === 0 ? (
          <li className="px-3 py-4 text-[12px] text-ink-faint">Collecting from allowlisted OSINT…</li>
        ) : null}
      </ul>
    </div>
  );
}

/** @deprecated use SourceCards */
export const SourceList = SourceCards;
