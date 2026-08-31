import { X } from "lucide-react";
import { storyForStage } from "@/content/system-story";

export function ExplainDrawer({
  stage,
  open,
  onClose,
}: {
  stage: string;
  open: boolean;
  onClose: () => void;
}) {
  const story = storyForStage(stage);
  if (!open || !story) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <button type="button" className="absolute inset-0 bg-ink/20" onClick={onClose} aria-label="Close" />
      <div className="relative w-full max-w-md bg-paper-1 border-l border-border shadow-drawer h-full p-6 overflow-y-auto">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-lg font-medium text-ink">{story.title}</h2>
            <p className="text-[13px] text-ink-muted mt-1">{story.oneLine}</p>
          </div>
          <button type="button" onClick={onClose} className="p-1 text-ink-muted hover:text-ink">
            <X size={18} />
          </button>
        </div>
        <p className="text-[14px] text-ink leading-relaxed">{story.body}</p>
        <ul className="mt-4 space-y-2">
          {story.bullets.map((b) => (
            <li key={b} className="text-[13px] text-ink-muted flex gap-2">
              <span className="text-sage-600">•</span>
              {b}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
