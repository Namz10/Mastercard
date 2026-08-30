import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { COPY } from "@/lib/copy";
import { useRecordedPacks } from "@/hooks/useRecordedPacks";
import { getSession, setSourceChip } from "@/lib/session-store";
import clsx from "clsx";

interface Command {
  id: string;
  group: string;
  label: string;
  shortcut?: string;
  action: () => void;
}

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { loadScore, loadLoop, loadIdentify } = useRecordedPacks();
  const navigate = useNavigate();

  const commands: Command[] = [
    {
      id: "rec-identify",
      group: "Recorded",
      label: COPY.palette.recordedIdentify,
      action: () => void loadIdentify(),
    },
    {
      id: "rec-score",
      group: "Recorded",
      label: COPY.palette.lockedHoldout,
      action: () => void loadScore(),
    },
    {
      id: "rec-loop",
      group: "Recorded",
      label: COPY.palette.recordedRetrain,
      action: () => void loadLoop(),
    },
    {
      id: "return-live",
      group: "Live",
      label: COPY.palette.returnLive,
      action: () => setSourceChip("live"),
    },
    {
      id: "copy-seed",
      group: "Copy seed",
      label: COPY.palette.copySeed,
      action: () => {
        const seed = getSession().generate.seed ?? 42;
        void navigator.clipboard.writeText(String(seed));
      },
    },
    {
      id: "nav-identify",
      group: "Navigate",
      label: COPY.nav.identify,
      action: () => navigate("/"),
    },
    {
      id: "nav-generate",
      group: "Navigate",
      label: COPY.nav.generate,
      action: () => navigate("/generate"),
    },
    {
      id: "nav-defend",
      group: "Navigate",
      label: COPY.nav.defend,
      action: () => navigate("/defend"),
    },
  ];

  const filtered = commands.filter(
    (c) => !query || c.label.toLowerCase().includes(query.toLowerCase()) || c.group.toLowerCase().includes(query.toLowerCase()),
  );
  const groups = [...new Set(filtered.map((c) => c.group))];

  const toggle = useCallback(() => setOpen((o) => !o), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggle();
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center pt-[12vh] bg-ink/20" role="dialog" aria-modal="true">
      <div className="w-[480px] max-w-[90vw] bg-surface border border-border rounded-drawer shadow-drawer overflow-hidden">
        <input
          autoFocus
          className="w-full px-4 py-3 border-b border-border bg-transparent text-sm outline-none"
          placeholder="Ops commands…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="max-h-[360px] overflow-y-auto py-2">
          {groups.map((group) => (
            <div key={group}>
              <div className="px-4 py-1 text-[10px] font-mono uppercase text-ink-faint tracking-wide">{group}</div>
              {filtered
                .filter((c) => c.group === group)
                .map((cmd) => (
                  <button
                    key={cmd.id}
                    type="button"
                    className={clsx(
                      "w-full flex items-center justify-between px-4 py-2 text-left text-[13px]",
                      "hover:bg-surface-sunken transition-colors duration-100",
                    )}
                    onClick={() => {
                      cmd.action();
                      setOpen(false);
                      setQuery("");
                    }}
                  >
                    <span>{cmd.label}</span>
                    {cmd.shortcut ? (
                      <span className="font-mono text-[10px] text-ink-faint">{cmd.shortcut}</span>
                    ) : null}
                  </button>
                ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
