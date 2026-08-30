import type { ReactNode } from "react";

export function PageHeader({
  title,
  census,
  caption,
  actions,
  secondaryActions,
  strip,
}: {
  title: string;
  census?: ReactNode;
  caption?: string;
  actions?: ReactNode;
  secondaryActions?: ReactNode;
  strip?: ReactNode;
}) {
  return (
    <header className="shrink-0 mb-2">
      <div className="h-12 flex items-center justify-between gap-4">
        <div className="flex items-baseline gap-3 min-w-0">
          <h1 className="font-sans text-[22px] font-semibold text-ink shrink-0 tracking-tight">{title}</h1>
          {census}
          {caption ? <p className="text-[12px] text-ink-faint truncate hidden xl:block max-w-[36ch]">{caption}</p> : null}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {secondaryActions}
          {actions}
        </div>
      </div>
      {strip ? <div className="mt-1 mb-1">{strip}</div> : null}
    </header>
  );
}
