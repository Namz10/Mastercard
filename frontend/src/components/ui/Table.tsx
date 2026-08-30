import type { ReactNode } from "react";

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto border border-border rounded">
      <table className="w-full text-sm">{children}</table>
    </div>
  );
}

export function Th({ mono, children }: { mono?: boolean; children: ReactNode }) {
  return (
    <th
      className={`text-left px-3 py-2 bg-surface-sunken text-ink-muted font-medium text-xs uppercase tracking-wide ${mono ? "font-mono" : ""}`}
    >
      {children}
    </th>
  );
}

export function Td({ mono, children }: { mono?: boolean; children: ReactNode }) {
  return (
    <td className={`px-3 py-2 border-t border-border ${mono ? "font-mono text-xs" : ""}`}>
      {children}
    </td>
  );
}
