import { useState } from "react";
import { Outlet } from "react-router-dom";
import { AegisSidebar } from "./AegisSidebar";
import { WorkspaceChrome } from "./WorkspaceChrome";
import { CommandPalette } from "./CommandPalette";

export function Shell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen workspace-bg overflow-hidden p-2.5 gap-2.5">
      <AegisSidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
      />
      <div className="flex-1 flex flex-col min-w-0 gap-2">
        <WorkspaceChrome />
        <main className="flex-1 overflow-hidden w-full min-h-0">
          <div className="bento-panel h-full min-h-0 overflow-hidden flex flex-col rounded-bento">
            <div className="flex-1 min-h-0 overflow-hidden px-4 py-3">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
