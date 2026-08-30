export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="border border-dashed border-border rounded p-8 text-center">
      <div className="font-mono text-ink-faint text-lg mb-2">·</div>
      <p className="text-sm text-ink-muted">{title}</p>
      {detail ? <p className="text-xs text-ink-faint mt-1">{detail}</p> : null}
    </div>
  );
}
