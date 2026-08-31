import { useMemo } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { PanelLeftClose, PanelLeftOpen, Search, BookOpen } from "lucide-react";
import clsx from "clsx";
import { SidebarNav, type NavGroupData } from "@/components/ui/dashboard-sidebar";
import { ModeChip } from "@/components/ui/ModeChip";
import { COPY } from "@/lib/copy";
import { useSessionSnapshot, isDefendScoreCurrent } from "@/lib/session-store";

const PHASES = [
  { id: "identify", to: "/identify", label: COPY.nav.identify },
  { id: "generate", to: "/generate", label: COPY.nav.generate },
  { id: "defend", to: "/defend", label: COPY.nav.defend },
] as const;

function phaseBadge(
  phase: (typeof PHASES)[number]["id"],
  session: ReturnType<typeof useSessionSnapshot>,
): number | string | undefined {
  if (phase === "identify") {
    const n = session.identify.approved.length;
    return n > 0 ? n : undefined;
  }
  if (phase === "generate") {
    if (session.generate.fidelityPass === true && session.generate.seed != null) return session.generate.seed;
    return undefined;
  }
  if (phase === "defend" && session.defend.score && isDefendScoreCurrent(session) && session.generate.fidelityPass === true) {
    const recall = session.defend.score.metrics.recall_at_op;
    return recall != null ? `${Math.round(recall * 100)}%` : "✓";
  }
  return undefined;
}

export function AegisSidebar({
  collapsed,
  onToggleCollapse,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const session = useSessionSnapshot();

  const activeId = useMemo(() => {
    const match = PHASES.find((p) => location.pathname.startsWith(p.to));
    return match?.id ?? "identify";
  }, [location.pathname]);

  const navGroups: NavGroupData[] = useMemo(
    () => [
      {
        items: [
          {
            id: "how-it-works",
            title: "How it works",
            icon: BookOpen,
            onSelect: () => navigate("/how-it-works"),
          },
          {
            id: "search",
            title: "Search",
            icon: Search,
            shortcut: "⌘K",
            onSelect: () => window.dispatchEvent(new Event("aegis:toggle-palette")),
            glass: true,
          },
        ],
      },
      {
        heading: "Closed loop",
        items: PHASES.map((p) => ({
          id: p.id,
          title: p.label,
          href: p.to,
          badge: phaseBadge(p.id, session),
        })),
      },
    ],
    [session],
  );

  if (collapsed) {
    return (
      <aside className="glass-sidebar w-12 shrink-0 flex flex-col items-center py-3 gap-2 h-full">
        <button
          type="button"
          onClick={onToggleCollapse}
          className="p-1.5 rounded-md text-ink-faint hover:bg-accent-muted hover:text-ink transition-colors duration-100"
          aria-label="Expand sidebar"
        >
          <PanelLeftOpen className="w-[18px] h-[18px]" strokeWidth={1.5} />
        </button>
        <button
          type="button"
          title="Search (⌘K)"
          className="w-8 h-8 flex items-center justify-center rounded-lg glass-control text-ink-faint hover:text-ink transition-colors duration-100"
          onClick={() => window.dispatchEvent(new Event("aegis:toggle-palette"))}
        >
          <Search className="w-4 h-4" strokeWidth={1.5} />
        </button>
        <nav className="flex flex-col gap-1 mt-1" aria-label="Phases">
          {PHASES.map((p) => {
            const badge = phaseBadge(p.id, session);
            return (
              <NavLink
                key={p.id}
                to={p.to}
                title={p.label}
                className={({ isActive }) =>
                  clsx(
                    "relative w-8 h-8 flex items-center justify-center rounded-lg text-[11px] font-medium transition-colors duration-100",
                    isActive ? "bg-accent text-accent-fg" : "text-ink-faint hover:bg-accent-muted hover:text-ink",
                  )
                }
              >
                {p.label.charAt(0)}
                {badge != null ? (
                  <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] px-0.5 flex items-center justify-center rounded-full bg-accent text-[8px] font-mono text-accent-fg">
                    {typeof badge === "number" && badge > 9 ? "9+" : badge}
                  </span>
                ) : null}
              </NavLink>
            );
          })}
        </nav>
      </aside>
    );
  }

  return (
    <aside className="w-[260px] shrink-0 overflow-hidden h-full">
      <SidebarNav
        activeId={activeId}
        onSelect={(id) => {
          const phase = PHASES.find((p) => p.id === id);
          if (phase) navigate(phase.to);
        }}
        navGroups={navGroups}
        sessionContext={{
          title: COPY.wordmark,
          subtitle: "Closed-loop booth",
        }}
        header={
          <div className="flex items-center justify-between mb-1 -mt-0.5">
            <ModeChip mode={session.ui.sourceChip} className="scale-[0.92] origin-left" />
            <button
              type="button"
              onClick={onToggleCollapse}
              className="p-1.5 rounded-md text-ink-faint hover:bg-accent-muted hover:text-ink transition-colors duration-100"
              aria-label="Collapse sidebar"
            >
              <PanelLeftClose className="w-[16px] h-[16px]" strokeWidth={1.5} />
            </button>
          </div>
        }
      />
    </aside>
  );
}
