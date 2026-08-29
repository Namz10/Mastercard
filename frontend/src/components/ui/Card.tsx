import type { ReactNode } from "react";

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded p-5">
      {title ? (
        <div className="font-mono uppercase text-ink-faint text-xs mb-3 tracking-wide">{title}</div>
      ) : null}
      {children}
    </div>
  );
}
