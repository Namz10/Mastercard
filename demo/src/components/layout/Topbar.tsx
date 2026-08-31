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
    <header className="shrink-0 mb-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-baseline gap-3">
            <h1 className="font-serif text-[24px] font-medium text-ink shrink-0 tracking-tight leading-tight">
              {title}
            </h1>
            {census}
          </div>
          {caption ? <p className="text-[13px] text-ink-faint mt-1 leading-snug">{caption}</p> : null}
        </div>
        <div className="flex items-center gap-2 shrink-0 pt-0.5">
          {secondaryActions}
          {actions}
        </div>
      </div>
      {strip ? <div className="mt-2">{strip}</div> : null}
    </header>
  );
}
