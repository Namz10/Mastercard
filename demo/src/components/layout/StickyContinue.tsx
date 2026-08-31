import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";

export function StickyContinue({
  to,
  label,
  onClick,
  disabled,
  secondary,
  demoId,
}: {
  to?: string;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  secondary?: ReactNode;
  demoId?: string;
}) {
  const navigate = useNavigate();

  return (
    <footer className="glass-sheet sticky bottom-0 z-10 -mx-4 px-4 mt-auto shrink-0 h-12 flex items-center gap-3 rounded-t-sheet">
      {secondary ? <div className="min-w-0 flex-1">{secondary}</div> : <div className="flex-1" />}
      <Button
        variant="primary"
        disabled={disabled}
        data-demo={demoId}
        onClick={() => {
          onClick?.();
          if (to && !disabled) navigate(to);
        }}
      >
        {label}
      </Button>
    </footer>
  );
}
