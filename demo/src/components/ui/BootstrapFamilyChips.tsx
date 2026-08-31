import clsx from "clsx";

export function BootstrapFamilyChips({
  family,
  resample,
  total = 200,
  className,
}: {
  family?: string;
  resample?: number;
  total?: number;
  className?: string;
}) {
  if (!family || resample == null) return null;
  const pct = Math.min(100, (resample / total) * 100);
  return (
    <div className={clsx("flex items-center gap-2", className)} data-demo="bootstrap-chips">
      <span className="text-[11px] text-ink-muted">{family}</span>
      <div className="flex-1 h-1.5 bg-surface-sunken rounded-full max-w-[120px]">
        <div className="h-full bg-sage-600 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] tnum text-ink-faint">{resample}/{total}</span>
    </div>
  );
}
