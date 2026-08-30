import { useCallback, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import clsx from "clsx";
import { STEPS, readDemoStep, writeDemoStep } from "./useGuidedDemo";

export function GuidedDemoBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStepState] = useState(() => readDemoStep());

  const go = useCallback(
    (index: number) => {
      const next = writeDemoStep(index);
      setStepState(next);
      navigate(STEPS[next].path);
    },
    [navigate],
  );

  const onNext = () => {
    go((step + 1) % STEPS.length);
  };

  return (
    <div className="border-b border-border bg-surface-sunken px-6 py-2 flex items-center justify-between gap-4 shrink-0">
      <div className="flex items-center gap-2 overflow-x-auto">
        <span className="text-xs font-mono uppercase text-ink-faint shrink-0">Demo</span>
        {STEPS.map((s, i) => (
          <button
            key={s.action}
            type="button"
            onClick={() => go(i)}
            title={s.label}
            className={clsx(
              "px-2 py-0.5 rounded-sm text-[11px] font-mono shrink-0 border transition-colors",
              i === step
                ? "border-signal-info text-signal-info bg-surface"
                : i < step
                  ? "border-border text-ink-muted"
                  : "border-transparent text-ink-faint",
            )}
          >
            {i + 1}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-ink-muted hidden lg:inline max-w-xs truncate">
          {STEPS[step]?.label}
          {location.pathname !== STEPS[step]?.path ? ` · go to ${STEPS[step]?.path}` : ""}
        </span>
        <Button variant="primary" onClick={onNext} data-demo="next-step">
          Next step →
        </Button>
      </div>
    </div>
  );
}
