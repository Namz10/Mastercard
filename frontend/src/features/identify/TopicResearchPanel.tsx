import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api-client";
import { useIdentifyMutations } from "./useIdentify";
import { useIdentifySession } from "./useIdentifySession";

function summarizeErrors(errors: string[] | undefined): string | null {
  if (!errors?.length) return null;
  const tavily432 = errors.some((e) => e.includes("scout_tavily") && e.includes("432"));
  const fixtureFallback = errors.some((e) => e.includes("scout_fallback:fixtures"));
  if (tavily432 && fixtureFallback) {
    return "Tavily returned HTTP 432 (quota/rate limit). Fell back to local OSINT fixtures so HITL can still fill.";
  }
  if (tavily432) {
    return "Tavily returned HTTP 432 (quota/rate limit). Live search produced no usable proposals.";
  }
  const short = errors
    .slice(0, 3)
    .map((e) => (e.length > 120 ? `${e.slice(0, 117)}…` : e))
    .join(" · ");
  return short;
}

export function TopicResearchPanel() {
  const { session, startNewTopic } = useIdentifySession();
  const [topic, setTopic] = useState(session.topic ?? "");
  const { runResearch } = useIdentifyMutations();

  const errorBanner = runResearch.isError
    ? runResearch.error instanceof ApiError
      ? `Research failed (${runResearch.error.status}): ${runResearch.error.message.slice(0, 240)}`
      : (runResearch.error as Error)?.message ?? "Research failed — check API logs and retry."
    : null;

  const pipelineNotes = runResearch.isSuccess ? summarizeErrors(runResearch.data.errors) : null;
  const proposed = runResearch.data?.proposed_count ?? null;

  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-center">
        <input
          className="flex-1 border border-border rounded px-3 py-2 text-sm bg-surface focus:outline-none focus:ring-2 focus:ring-signal-info"
          placeholder="e.g. deepfake voice authorization for wire transfers"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          data-demo="research-input"
        />
        <Button
          variant="primary"
          disabled={!topic.trim() || runResearch.isPending}
          onClick={() =>
            runResearch.mutate(topic.trim(), {
              onSuccess: () => startNewTopic(topic.trim()),
            })
          }
          data-demo="research-button"
        >
          {runResearch.isPending ? "Researching…" : "Research"}
        </Button>
      </div>

      {runResearch.isPending ? (
        <p className="text-xs text-ink-muted font-mono animate-pulse">
          Running Identify graph (Tavily/fixtures → extract → curator → HITL)…
        </p>
      ) : null}

      {errorBanner ? <p className="text-xs text-signal-block">{errorBanner}</p> : null}

      {pipelineNotes ? (
        <p
          className={
            pipelineNotes.includes("Fell back")
              ? "text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1.5"
              : "text-xs text-signal-block bg-red-50 border border-signal-block/30 rounded px-2 py-1.5"
          }
        >
          {pipelineNotes}
        </p>
      ) : null}

      {runResearch.isSuccess ? (
        <div className="p-3 bg-surface-sunken rounded border border-border space-y-1">
          <p className="text-xs font-mono text-signal-info font-medium">
            Research completed (Run: {runResearch.data.run_id})
          </p>
          <p className="text-xs text-ink-muted">
            Found <strong>{runResearch.data.scout_candidate_count}</strong> scout candidates · curator kept{" "}
            <strong>{runResearch.data.curator_kept_count}</strong> · proposed{" "}
            <strong>{runResearch.data.proposed_count}</strong> threat vectors.
          </p>
          {proposed === 0 ? (
            <p className="text-xs text-signal-block font-medium pt-1">
              No HITL proposals this run. Check the amber/red note above (often Tavily quota). Retry after fixing
              the key, or set IDENTIFY_LIVE_SEARCH=false for fixture mode.
            </p>
          ) : (
            <p className="text-xs text-[#166534] font-medium pt-1">
              ↓ Candidate threat vectors are ready below in the HITL Queue. Approve to add them to the catalog.
            </p>
          )}
        </div>
      ) : null}

      {session.topic && !runResearch.isSuccess && !runResearch.isPending ? (
        <p className="text-xs text-ink-muted font-mono">
          Last topic: <span className="text-ink">{session.topic}</span>
        </p>
      ) : null}
    </div>
  );
}
