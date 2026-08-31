import clsx from "clsx";
import { useNarration } from "./NarrationContext";

export function NowHappening({ className }: { className?: string }) {
  const { narration } = useNarration();
  if (!narration) return null;

  return (
    <div
      className={clsx(
        "rounded-bento border border-border bg-paper-1/90 backdrop-blur-sm p-4 shadow-bento",
        className,
      )}
      data-demo="now-happening"
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-sage-700">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sage-600 opacity-40" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-sage-600" />
          </span>
          NOW
        </span>
        {narration.verb ? (
          <span className="text-[11px] text-ink-faint font-mono">{narration.verb}</span>
        ) : null}
      </div>
      <p className="text-[15px] font-medium text-ink leading-snug">{narration.now}</p>
      <p className="text-[13px] text-ink-muted mt-1">{narration.happening}</p>
      <p className="text-[12px] text-ink-faint mt-2">{narration.why}</p>
      {narration.next ? (
        <p className="text-[12px] text-sage-700 mt-2">Up next: {narration.next}</p>
      ) : null}
    </div>
  );
}
