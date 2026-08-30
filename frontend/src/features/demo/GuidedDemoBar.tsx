import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import clsx from "clsx";
import { STEPS } from "./useGuidedDemo";

function getStep(): number {
  return Number(sessionStorage.getItem("aegisloop-demo-step") ?? "0");
}

function setStep(next: number) {
  sessionStorage.setItem("aegisloop-demo-step", String(Math.max(0, Math.min(next, STEPS.length - 1))));
}

export function GuidedDemoBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const step = getStep();

  const onNext = () => {
    const next = Math.min(step + 1, STEPS.length - 1);
    setStep(next);
    navigate(STEPS[next].path);
  };

  return (
    <div className="border-b border-border bg-surface-sunken px-6 py-2 flex items-center justify-between gap-4 shrink-0">
      <div className="flex items-center gap-2 overflow-x-auto">
        <span className="text-xs font-mono uppercase text-ink-faint shrink-0">Demo</span>
        {STEPS.map((s, i) => (
          <button
            key={s.label}
            type="button"
            onClick={() => {
              setStep(i);
              navigate(s.path);
            }}
            className={clsx(
              "px-2 py-0.5 rounded-sm text-[11px] font-mono shrink-0 border transition-colors",
              i === step && location.pathname === s.path
                ? "border-signal-info text-signal-info bg-surface"
                : i <= step
                  ? "border-border text-ink-muted"
                  : "border-transparent text-ink-faint",
            )}
          >
            {i + 1}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-ink-muted hidden lg:inline max-w-xs truncate">{STEPS[step]?.label}</span>
        <Button variant="primary" onClick={onNext} disabled={step >= STEPS.length - 1}>
          Next step →
        </Button>
      </div>
    </div>
  );
}
