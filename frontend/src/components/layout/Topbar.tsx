import type { ReactNode } from "react";

export function PageHeader({
  title,
  census,
  caption,
  actions,
}: {
  title: string;
  census?: ReactNode;
  caption?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="h-12 shrink-0 flex items-center justify-between gap-4 mb-4 pb-3 border-b border-border">
      <div className="flex items-baseline gap-4 min-w-0">
        <h1 className="font-serif text-2xl font-medium text-ink shrink-0">{title}</h1>
        {census}
        {caption ? <p className="text-[13px] text-ink-faint truncate hidden lg:block">{caption}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2 shrink-0">{actions}</div> : null}
    </header>
  );
}
