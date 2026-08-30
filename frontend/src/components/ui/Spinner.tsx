export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-ink-muted" role="status">
      <span className="inline-block w-4 h-4 border-2 border-border border-t-signal-info rounded-full animate-spin" />
      {label}
    </div>
  );
}
