import clsx from "clsx";

const COLOR: Record<string, string> = {
  live_rule: "border-signal-safe text-signal-safe",
  draft_rule: "border-signal-watch text-signal-watch",
  named_gap: "border-signal-idle text-ink-muted",
  case_only: "border-signal-idle text-ink-muted",
  empty: "border-border text-ink-faint",
  hard_flag: "border-signal-block text-signal-block",
  nudge: "border-signal-watch text-signal-watch",
  allow: "border-signal-safe text-signal-safe",
  notify: "border-signal-watch text-signal-watch",
  step_up: "border-signal-watch text-signal-watch",
  hold: "border-signal-block text-signal-block",
  decline: "border-signal-block text-signal-block",
  mule_credit_restrict: "border-signal-watch text-signal-watch",
  pass: "border-signal-safe text-signal-safe",
  fail: "border-signal-block text-signal-block",
};

export function StatusChip({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm border font-mono text-[11px] uppercase tracking-wide",
        COLOR[status] ?? "border-border text-ink-muted",
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {status.replace(/_/g, " ")}
    </span>
  );
}
