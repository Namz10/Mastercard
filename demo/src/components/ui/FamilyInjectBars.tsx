import clsx from "clsx";

export function FamilyInjectBars({
  counts,
  className,
}: {
  counts: Record<string, number>;
  className?: string;
}) {
  const max = Math.max(...Object.values(counts), 1);
  return (
    <div className={clsx("space-y-2", className)} data-demo="family-bars">
      {Object.entries(counts).map(([fam, n]) => (
        <div key={fam} className="flex items-center gap-2 text-[12px]">
          <span className="w-24 text-ink-muted truncate">{fam}</span>
          <div className="flex-1 h-2 bg-surface-sunken rounded-full overflow-hidden">
            <div
              className="h-full bg-sage-600 transition-all duration-500"
              style={{ width: `${(n / max) * 100}%` }}
            />
          </div>
          <span className="tnum text-ink-faint w-12 text-right">{n}</span>
        </div>
      ))}
    </div>
  );
}
