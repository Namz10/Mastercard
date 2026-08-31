import { useLocation } from "react-router-dom";
import { StagePills } from "@/components/layout/StagePills";

/** Status row: stage pills + ⌘K. Pillars live in the sidebar — not duplicated here. */
export function WorkspaceChrome() {
  const location = useLocation();
  const showPills = location.pathname.startsWith("/identify") || location.pathname.startsWith("/defend");

  return (
    <div className="h-10 shrink-0 glass-sheet rounded-sheet flex items-center px-3 gap-2 text-[13px]">
      {showPills ? (
        <div className="flex-1 min-w-0">
          <StagePills />
        </div>
      ) : (
        <div className="flex-1" />
      )}
      <button
        type="button"
        className="shrink-0 font-mono text-[10px] text-ink-faint hover:text-ink px-2 py-1 rounded-md hover:bg-accent-muted transition-colors duration-100"
        data-demo="command-palette"
        onClick={() => window.dispatchEvent(new Event("aegis:toggle-palette"))}
        title="Ops commands"
      >
        ⌘K
      </button>
    </div>
  );
}
