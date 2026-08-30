import { useState } from "react";
import type { UseMutationResult } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import type { CommandCenterBriefResponse } from "./command-types";

export function ExecutiveBrief({
  brief,
}: {
  brief: UseMutationResult<CommandCenterBriefResponse, Error, void, unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    const text = brief.data?.text;
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* ignore */
    }
  };

  return (
    <section className="bg-white border border-border rounded-xl mb-4 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-5 py-4 text-left hover:bg-surface-sunken transition-colors"
      >
        <div>
          <div className="font-mono uppercase text-ink-faint text-xs tracking-wide">
            Executive brief
          </div>
          <div className="text-sm text-ink-muted mt-0.5">
            LLM summarizes verified lab JSON — not the payment detector
          </div>
        </div>
        <span className="font-mono text-xs text-ink-faint">{open ? "−" : "+"}</span>
      </button>

      {open ? (
        <div className="px-5 pb-5 border-t border-border pt-4 space-y-3">
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            {brief.data?.disclaimer ??
              "LLM summarizes lab state from verified metrics. AuthGate + Brake score payments."}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              disabled={brief.isPending}
              onClick={() => brief.mutate()}
            >
              {brief.isPending ? "Generating…" : "Generate executive summary"}
            </Button>
            <Button
              variant="secondary"
              disabled={!brief.data?.text}
              onClick={() => void onCopy()}
            >
              {copied ? "Copied" : "Copy"}
            </Button>
            {brief.data?.source ? (
              <span className="self-center font-mono text-[11px] text-ink-faint">
                source={brief.data.source}
              </span>
            ) : null}
          </div>

          {brief.isError ? (
            <p className="text-sm text-signal-block">
              {(brief.error as Error)?.message ?? "Brief generation failed"}
            </p>
          ) : null}

          {brief.data?.text ? (
            <div className="rounded-lg border border-border bg-surface-sunken/40 px-4 py-3 text-sm text-ink leading-relaxed whitespace-pre-wrap">
              {brief.data.text}
            </div>
          ) : (
            <p className="text-sm text-ink-muted">
              Collapsed by default — generate a short judge-facing summary when ready.
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}
