import type { UseMutationResult } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import type { GenerateRunResponse } from "@/lib/api-types";

export function LaunchPanel({
  population,
  canary,
}: {
  population: UseMutationResult<GenerateRunResponse, Error, void, unknown>;
  canary: UseMutationResult<GenerateRunResponse, Error, string, unknown>;
}) {
  const busy = population.isPending || canary.isPending;

  return (
    <div className="flex flex-wrap gap-2 items-center">
      <Button
        variant="primary"
        disabled={busy}
        onClick={() => population.mutate()}
        data-demo="run-population"
      >
        {population.isPending ? "Running population…" : "Run population"}
      </Button>
      <Button
        variant="secondary"
        disabled={busy}
        onClick={() => canary.mutate("fincen-fin-2024-alert004")}
        data-demo="run-canary"
      >
        {canary.isPending ? "Running canary…" : "Run canary campaign"}
      </Button>
      {busy ? (
        <span className="font-mono text-[11px] text-ink-faint animate-pulse">calling /generate…</span>
      ) : null}
    </div>
  );
}
