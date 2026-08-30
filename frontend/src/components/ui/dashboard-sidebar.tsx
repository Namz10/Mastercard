import { useState, type ElementType, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";

export type NavItemData = {
  id: string;
  title: string;
  icon?: ElementType;
  badge?: number | string;
  shortcut?: string;
  children?: NavItemData[];
  href?: string;
  onSelect?: () => void;
  glass?: boolean;
};

export type NavGroupData = {
  heading?: string;
  items: NavItemData[];
};

type SessionContextProps = {
  title: string;
  subtitle?: string;
  badge?: string;
};

export function SessionContextHeader({ title, subtitle, badge }: SessionContextProps) {
  return (
    <div className="flex items-center gap-3 px-2 py-2 mb-3 rounded-xl glass-control">
      <div className="w-8 h-8 rounded-lg bg-accent text-accent-fg flex items-center justify-center font-semibold text-[13px] shrink-0">
        {title.charAt(0)}
      </div>
      <div className="flex flex-col overflow-hidden min-w-0">
        <span className="text-[13px] font-medium leading-none mb-1 text-ink truncate">{title}</span>
        {subtitle ? (
          <span className="text-[11px] text-ink-faint leading-none truncate">{subtitle}</span>
        ) : null}
      </div>
      {badge ? (
        <span className="ml-auto font-mono text-[10px] uppercase tracking-wide text-ink-faint shrink-0">
          {badge}
        </span>
      ) : null}
    </div>
  );
}

function NavItem({
  item,
  activeId,
  onSelect,
  level = 0,
}: {
  item: NavItemData;
  activeId: string;
  onSelect: (id: string) => void;
  level?: number;
}) {
  const isActive = activeId === item.id;
  const hasChildren = !!item.children?.length;
  const [isOpen, setIsOpen] = useState(false);
  const Icon = item.icon;

  const handleClick = () => {
    if (item.onSelect) {
      item.onSelect();
      return;
    }
    if (hasChildren) {
      setIsOpen(!isOpen);
      return;
    }
    onSelect(item.id);
  };

  const rowClass = `group flex items-center justify-between px-2.5 py-[7px] rounded-lg cursor-pointer transition-colors duration-100 select-none
    ${item.glass ? "glass-control text-ink-muted hover:text-ink" : ""}
    ${!item.glass && isActive ? "bg-accent text-accent-fg font-medium" : ""}
    ${!item.glass && !isActive ? "text-ink-muted hover:bg-accent-muted hover:text-ink" : ""}`;

  const inner = (
    <>
      <div className="flex items-center gap-2.5 min-w-0">
        {Icon ? (
          <Icon
            className={`w-[16px] h-[16px] shrink-0 transition-colors duration-100
              ${isActive && !item.glass ? "text-accent-fg" : "text-ink-faint group-hover:text-ink-muted"}`}
            strokeWidth={1.5}
          />
        ) : null}
        <span className="text-[13px] tracking-wide truncate">{item.title}</span>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        {item.shortcut ? (
          <kbd
            className="hidden group-hover:inline-flex items-center justify-center h-5 px-1.5 text-[10px] font-medium font-mono text-ink-faint bg-surface border border-border rounded-[4px]"
          >
            {item.shortcut}
          </kbd>
        ) : null}
        {item.badge ? (
          <span className={`flex items-center justify-center min-w-[20px] h-5 px-1.5 text-[10px] font-medium rounded-full ${isActive ? "bg-white/20 text-accent-fg" : "bg-accent-muted text-accent"}`}>
            {item.badge}
          </span>
        ) : null}
        {hasChildren ? (
          <ChevronRight
            className={`w-3.5 h-3.5 text-ink-faint transition-transform duration-100 ${isOpen ? "rotate-90" : ""}`}
            strokeWidth={2}
          />
        ) : null}
      </div>
    </>
  );

  return (
    <div className="flex flex-col w-full">
      {item.href && !hasChildren ? (
        <Link
          to={item.href}
          className={rowClass}
          style={{ paddingLeft: `${level * 12 + 10}px` }}
          onClick={() => onSelect(item.id)}
        >
          {inner}
        </Link>
      ) : (
        <div
          className={rowClass}
          style={{ paddingLeft: `${level * 12 + 10}px` }}
          onClick={handleClick}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              handleClick();
            }
          }}
        >
          {inner}
        </div>
      )}

      {hasChildren ? (
        <div
          className={`grid transition-[grid-template-rows,opacity] duration-100 ease-out ${
            isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
          }`}
        >
          <div className="overflow-hidden min-h-0 relative flex flex-col gap-0.5 mt-0.5">
            <div
              className="absolute top-0 bottom-0 border-l border-border"
              style={{ left: `${level * 12 + 17.5}px` }}
            />
            {item.children!.map((child) => (
              <NavItem key={child.id} item={child} activeId={activeId} onSelect={onSelect} level={level + 1} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function SidebarNav({
  className = "",
  activeId,
  onSelect,
  navGroups,
  bottomItems = [],
  sessionContext,
  header,
  footer,
}: {
  className?: string;
  activeId: string;
  onSelect: (id: string) => void;
  navGroups: NavGroupData[];
  bottomItems?: NavItemData[];
  sessionContext?: SessionContextProps;
  header?: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div
      className={`glass-sidebar flex flex-col w-[260px] h-full p-3 font-sans ${className}`}
    >
      {header}
      {sessionContext ? <SessionContextHeader {...sessionContext} /> : null}

      <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] flex flex-col gap-4 mt-1">
        <nav aria-label="Phases">
          {navGroups.map((group, idx) => (
            <div key={group.heading ?? idx} className="flex flex-col gap-0.5 mb-4 last:mb-0">
              {group.heading ? (
                <span className="px-2.5 mb-1 text-[11px] font-semibold tracking-wider text-ink-faint uppercase">
                  {group.heading}
                </span>
              ) : null}
              {group.items.map((item) => (
                <NavItem key={item.id} item={item} activeId={activeId} onSelect={onSelect} />
              ))}
            </div>
          ))}
        </nav>
      </div>

      {bottomItems.length > 0 || footer ? (
        <div className="mt-auto pt-4 border-t border-border/80 flex flex-col gap-0.5">
          {bottomItems.map((item) => (
            <NavItem key={item.id} item={item} activeId={activeId} onSelect={onSelect} />
          ))}
          {footer}
        </div>
      ) : null}
    </div>
  );
}
