import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { COPY } from "@/lib/copy";

const NAV = [
  { to: "/", label: COPY.nav.identify },
  { to: "/generate", label: COPY.nav.generate },
  { to: "/defend", label: COPY.nav.defend },
];

export function Sidebar() {
  return (
    <aside className="w-[220px] shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="px-5 py-5 font-sans text-[15px] font-semibold text-ink">{COPY.wordmark}</div>
      <nav className="flex-1 px-2 space-y-0.5">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              clsx(
                "block px-3 py-2 rounded text-[13px] transition-colors duration-100",
                isActive
                  ? "bg-surface-sunken text-ink font-medium"
                  : "text-ink-muted hover:bg-surface-sunken hover:text-ink",
              )
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
