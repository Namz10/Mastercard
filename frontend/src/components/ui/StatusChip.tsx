import clsx from "clsx";

const COLOR: Record<string, string> = {
  live_rule: "border-sage-600 text-sage-600",
  draft_rule: "border-signal-watch text-signal-watch",
  named_gap: "border-slate-600 text-slate-600",
  case_only: "border-slate-600 text-slate-600",
  empty: "border-border text-ink-faint",
  hard_flag: "border-signal-block text-signal-block",
  nudge: "border-signal-watch text-signal-watch",
  allow: "border-sage-600 text-sage-600",
  notify: "border-signal-watch text-signal-watch",
  step_up: "border-signal-watch text-signal-watch",
  hold: "border-slate-600 text-slate-600",
  decline: "border-signal-block text-signal-block",
  mule_credit_restrict: "border-ink text-ink",
  pass: "border-sage-600 text-sage-600",
  fail: "border-signal-block text-signal-block",
};

const LABEL: Record<string, string> = {
  live_rule: "Live rule",
  draft_rule: "Draft rule",
  named_gap: "Coverage gap",
  case_only: "Coverage gap",
  empty: "Coverage gap",
  allow: "Allow",
  notify: "Notify",
  step_up: "Step-up",
  hold: "Hold",
  decline: "Decline",
  mule_credit_restrict: "Restrict (payee credit)",
};

export function StatusChip({ status }: { status: string }) {
  const label = LABEL[status] ?? status.replace(/_/g, " ");
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm border font-mono text-[10px] uppercase tracking-wide",
        COLOR[status] ?? "border-border text-ink-muted",
      )}
    >
      {label}
    </span>
  );
}
