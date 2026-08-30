import { NavLink } from "react-router-dom";
import clsx from "clsx";

const NAV = [
  { to: "/", label: "Threat Map", hint: "T01–T24" },
  { to: "/identify", label: "Identify", hint: "Topic → HITL" },
  { to: "/simulation", label: "Simulation Console", hint: "Generate" },
  { to: "/decisioning", label: "Decisioning", hint: "Defend" },
  { to: "/arms-race", label: "Arms Race", hint: "Loop M" },
  { to: "/copilot", label: "Command Center", hint: "COMMAND" },
];

export function Sidebar() {
  return (
    <aside
      className="w-[220px] shrink-0 border-r border-border bg-surface flex flex-col"
      style={{ boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }}
    >
      <div className="px-5 py-5 font-mono text-sm font-medium tracking-wide">AEGISLOOP</div>
      <nav className="flex-1 px-2 space-y-1">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              clsx(
                "px-3 py-2 rounded text-sm flex justify-between transition-colors",
                isActive
                  ? "bg-surface-sunken text-ink font-medium"
                  : "text-ink-muted hover:bg-surface-sunken",
              )
            }
          >
            <span>{item.label}</span>
            <span className="font-mono text-[11px] uppercase text-ink-faint">{item.hint}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
