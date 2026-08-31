export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="border border-signal-block/30 bg-surface rounded p-6">
      <div className="font-mono text-signal-block text-lg mb-2">!</div>
      <p className="text-sm text-ink">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 text-sm text-signal-info underline underline-offset-2"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
