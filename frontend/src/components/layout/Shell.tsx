import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { GuidedDemoBar } from "@/features/demo/GuidedDemoBar";

export function Shell() {
  return (
    <div className="flex h-screen bg-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <GuidedDemoBar />
        <main className="flex-1 overflow-y-auto px-8 py-6 max-w-[1280px] w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
