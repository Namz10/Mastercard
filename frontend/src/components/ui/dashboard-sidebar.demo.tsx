import { useState } from "react";
import { BarChart3, FileText, Home, Settings, Users } from "lucide-react";
import { SidebarNav, type NavGroupData } from "./dashboard-sidebar";

/** Lab preview only — mock workspace groups for component QA. Not used in booth shell. */
const DEMO_GROUPS: NavGroupData[] = [
  {
    heading: "Overview",
    items: [
      { id: "home", title: "Home", icon: Home },
      { id: "reports", title: "Reports", icon: FileText, badge: 3 },
    ],
  },
  {
    heading: "Workspace",
    items: [
      { id: "analytics", title: "Analytics", icon: BarChart3 },
      {
        id: "team",
        title: "Team",
        icon: Users,
        children: [
          { id: "members", title: "Members" },
          { id: "roles", title: "Roles" },
        ],
      },
    ],
  },
];

const DEMO_BOTTOM = [{ id: "settings", title: "Settings", icon: Settings }];

export default function DashboardSidebarDemo() {
  const [activeId, setActiveId] = useState("home");

  return (
    <div className="h-screen bg-bg flex">
      <SidebarNav
        activeId={activeId}
        onSelect={setActiveId}
        navGroups={DEMO_GROUPS}
        bottomItems={DEMO_BOTTOM}
        sessionContext={{
          title: "Acme Corp",
          subtitle: "Fraud ops sandbox",
          badge: "demo",
        }}
        header={
          <p className="font-mono text-[10px] uppercase tracking-wide text-ink-faint mb-2 px-2">
            Component preview
          </p>
        }
      />
      <main className="flex-1 p-8 text-ink-muted text-[13px]">
        Active item: <span className="font-mono text-ink">{activeId}</span>
      </main>
    </div>
  );
}
