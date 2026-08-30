import clsx from "clsx";
import type { ReactNode } from "react";

export function Drawer({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  return (
    <>
      <div
        className={clsx(
          "fixed inset-0 bg-ink/20 z-40 transition-opacity",
          open ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside
        className={clsx(
          "fixed top-0 right-0 h-full w-full max-w-md bg-surface border-l border-border z-50 shadow-sm transition-transform duration-150",
          open ? "translate-x-0" : "translate-x-full",
        )}
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <h2 className="font-mono text-sm font-medium">{title}</h2>
          <button type="button" onClick={onClose} className="text-ink-faint hover:text-ink text-sm">
            Close
          </button>
        </div>
        <div className="p-5 overflow-y-auto h-[calc(100%-57px)]">{children}</div>
      </aside>
    </>
  );
}
