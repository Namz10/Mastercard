/** Quarantined GFF 2026 — off nav. Proof-only lab. Do not restore to chrome. */
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { useIdentifyMutations } from "./useIdentify";
import { useIdentifySession } from "./useIdentifySession";

export function TopicResearchPanel() {
  const { session, startNewTopic } = useIdentifySession();
  const [topic, setTopic] = useState(session.topic ?? "");
  const { runResearch } = useIdentifyMutations();

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
      {runResearch.isError ? (
        <p className="text-xs text-signal-block">Research failed — check API logs and retry.</p>
      ) : null}
      {runResearch.isSuccess ? (
        <div className="p-3 bg-surface-hover rounded border border-border space-y-1">
          <p className="text-xs font-mono text-signal-info font-medium">
            Research completed (Run: {runResearch.data.run_id})
          </p>
          <p className="text-xs text-ink-muted">
            Found <strong>{runResearch.data.scout_candidate_count}</strong> scout candidates and proposed{" "}
            <strong>{runResearch.data.proposed_count}</strong> threat vectors (Curator kept{" "}
            {runResearch.data.curator_kept_count}).
          </p>
          <p className="text-xs text-signal-success font-medium pt-1">
            ↓ Candidate threat vectors are ready below in the HITL Queue. Approve candidate vector(s) to add them to
            the catalog for generation.
          </p>
        </div>
      ) : null}
      {session.topic && !runResearch.isSuccess ? (
        <p className="text-xs text-ink-muted font-mono">
          Research complete for topic: <span className="text-ink">{session.topic}</span>
        </p>
      ) : null}
    </div>
  );
}
