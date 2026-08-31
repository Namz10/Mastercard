import { Button } from "@/components/ui/Button";

export function ErrorBanner({
  message,
  onRetry,
  hint,
}: {
  message: string;
  onRetry?: () => void;
  hint?: string;
}) {
  return (
    <div
      className="text-[13px] text-signal-block mb-2 border border-signal-block/30 bg-surface px-3 py-2 rounded-sheet flex items-center gap-3"
      role="alert"
    >
      <span className="flex-1">{message}</span>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
      {hint ? <span className="text-[12px] text-ink-faint shrink-0">{hint}</span> : null}
    </div>
  );
}
