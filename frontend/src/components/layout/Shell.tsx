import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { StatusStrip } from "@/components/ui/ModeChip";
import { PhaseStepper } from "./PhaseStepper";
import { CommandPalette } from "./CommandPalette";

export function Shell() {
  return (
    <div className="flex h-screen bg-bg overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <StatusStrip />
        <PhaseStepper />
        <main className="flex-1 overflow-y-auto px-6 py-4 w-full">
          <Outlet />
        </main>
      </div>
      <CommandPalette />
    </div>
  );
}
