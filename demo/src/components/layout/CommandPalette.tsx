import { Command } from "cmdk";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { COPY } from "@/lib/copy";
import { runBoothDemo } from "@/lib/booth-demo";
import { requestRecordedIdentify, requestSkipIdentify } from "@/lib/identify-bus";
import { getSession, setSourceChip } from "@/lib/session-store";
import { useRecordedPacks } from "@/hooks/useRecordedPacks";
import { useHonestyProbe } from "@/hooks/useHonestyProbe";
import { isRecordedDemo } from "@/lib/api-client";
import { useNarration } from "@/explain/NarrationContext";

/** Structure from 21st originui Command id:382 — restyled paper/sage/ink. */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const { loadScore, loadLoop } = useRecordedPacks();
  const navigate = useNavigate();
  const probe = useHonestyProbe();
  const liveOk = probe.liveSearch && probe.llm && probe.health;
  const { setCaptionsHidden, captionsHidden } = useNarration();

  const toggle = useCallback(() => setOpen((o) => !o), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        e.stopPropagation();
        toggle();
      }
      if (e.key === "Escape") setOpen(false);
    };
    const onToggle = () => toggle();
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("aegis:toggle-palette", onToggle);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      window.removeEventListener("aegis:toggle-palette", onToggle);
    };
  }, [toggle]);

  const run = (fn: () => void) => {
    fn();
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center pt-[12vh] bg-ink/20"
      role="dialog"
      aria-modal="true"
      onClick={() => setOpen(false)}
    >
      <Command
        className="w-[480px] max-w-[90vw] max-h-[60vh] glass-sheet rounded-sheet overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
        label="Ops commands"
      >
        <Command.Input
          autoFocus
          placeholder="Command"
          className="h-9 w-full px-4 border-b border-border bg-transparent text-[13px] outline-none placeholder:text-ink-faint"
        />
        <Command.List className="overflow-y-auto py-1 max-h-[50vh]">
          <Command.Empty className="px-4 py-6 text-[13px] text-ink-faint">No matching command.</Command.Empty>
          <Group heading="Booth">
            <Item
              onSelect={() =>
                run(() => {
                  void runBoothDemo({ navigate });
                })
              }
              label={COPY.palette.boothDemo}
              kbd="B D"
              demoId="booth-demo"
            />
            <Item
              onSelect={() => run(() => navigate("/how-it-works"))}
              label="How it works"
              kbd="H W"
            />
            <Item
              onSelect={() => run(() => setCaptionsHidden(!captionsHidden))}
              label={captionsHidden ? "Show captions" : "Hide captions"}
            />
          </Group>
          <Group heading="Recorded">
            <Item
              onSelect={() =>
                run(() => {
                  navigate("/identify/discover");
                  requestRecordedIdentify();
                })
              }
              label={COPY.palette.recordedIdentify}
              kbd="R I"
            />
            <Item onSelect={() => run(() => void loadScore())} label={COPY.palette.lockedHoldout} kbd="R H" />
            <Item onSelect={() => run(() => void loadLoop())} label={COPY.palette.recordedRetrain} kbd="R T" />
            <Item onSelect={() => run(() => requestSkipIdentify())} label={COPY.skip} kbd="S" />
          </Group>
          <Group heading="Live">
            <Item
              onSelect={() => {
                if (!liveOk || isRecordedDemo()) return;
                run(() => setSourceChip("live", null));
              }}
              label={COPY.palette.returnLive}
              disabled={!liveOk || isRecordedDemo()}
            />
          </Group>
          <Group heading="Navigate">
            <Item onSelect={() => run(() => navigate("/identify"))} label={COPY.nav.identify} kbd="G I" />
            <Item onSelect={() => run(() => navigate("/generate"))} label={COPY.nav.generate} kbd="G G" />
            <Item onSelect={() => run(() => navigate("/defend/detection"))} label={COPY.nav.defend} kbd="G D" />
          </Group>
          <Group heading="Copy">
            <Item
              onSelect={() =>
                run(() => {
                  void navigator.clipboard.writeText(String(getSession().generate.seed ?? 42));
                })
              }
              label={COPY.palette.copySeed}
            />
            <Item
              onSelect={() =>
                run(() => {
                  const m = getSession().defend.score?.metrics;
                  const text = m
                    ? COPY.defend.op((m.recall_at_op * 100).toFixed(1), (m.genuine_fp * 100).toFixed(3))
                    : COPY.defend.empty;
                  void navigator.clipboard.writeText(text);
                })
              }
              label={COPY.palette.copyOp}
            />
          </Group>
        </Command.List>
      </Command>
    </div>
  );
}

function Group({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <Command.Group
      heading={heading}
      className="[&_[cmdk-group-heading]]:px-4 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:font-mono [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-ink-faint"
    >
      {children}
    </Command.Group>
  );
}

function Item({
  onSelect,
  label,
  kbd,
  disabled,
  demoId,
}: {
  onSelect: () => void;
  label: string;
  kbd?: string;
  disabled?: boolean;
  demoId?: string;
}) {
  return (
    <Command.Item
      value={label}
      disabled={disabled}
      onSelect={onSelect}
      data-demo={demoId}
      className="flex h-9 items-center justify-between px-4 text-[13px] data-[selected=true]:bg-accent-muted data-[disabled=true]:opacity-40 cursor-pointer"
    >
      <span>{label}</span>
      {kbd ? <kbd className="font-mono text-[11px] text-ink-faint border border-border rounded-sm px-1">{kbd}</kbd> : null}
    </Command.Item>
  );
}
