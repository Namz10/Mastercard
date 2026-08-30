import type { UseMutationResult } from "@tanstack/react-query";
import { Button } from "@/components/ui/Button";
import type { GenerateRunResponse } from "@/lib/api-types";

export function LaunchPanel({
  population,
  canary,
}: {
  population: UseMutationResult<GenerateRunResponse, Error, void, unknown>;
  canary: UseMutationResult<GenerateRunResponse, Error, void, unknown>;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <Button
        variant="primary"
        disabled={population.isPending}
        onClick={() => population.mutate()}
        data-demo="run-population"
      >
        {population.isPending ? "Running…" : "Run population"}
      </Button>
      <Button variant="secondary" disabled={canary.isPending} onClick={() => canary.mutate()}>
        {canary.isPending ? "Running…" : "Run canary campaign"}
      </Button>
    </div>
  );
}
