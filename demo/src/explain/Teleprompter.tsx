import { useNarration } from "./NarrationContext";
import { captionsEnabled, parseSpeedMode } from "@/demo/speed";

export function Teleprompter() {
  const { narration, captionsHidden } = useNarration();
  const mode = parseSpeedMode();
  if (captionsHidden || !captionsEnabled(mode) || !narration) return null;

  return (
    <div
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-lg px-4 py-3 rounded-sheet border border-border bg-paper-1/95 shadow-float backdrop-blur-md pointer-events-none"
      data-demo="teleprompter"
    >
      <p className="text-[13px] text-ink">
        <span className="font-medium text-sage-700">Now: </span>
        {narration.now}
      </p>
    </div>
  );
}
