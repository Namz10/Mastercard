import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { LoopMResponse } from "@/lib/api-types";
import { useLatestRun } from "@/lib/latest-run-context";
import { useDecisioningState } from "@/features/decisioning/useDecisioningState";
import { useArmsRaceState } from "./useArmsRaceState";

export function useArmsRace() {
  const { runId } = useLatestRun();
  const { score: staticScore } = useDecisioningState();
  const [result, setResult] = useArmsRaceState();

  const loopM = useMutation({
    mutationFn: (args: { miss_family: string; train_seed?: number; gtest_seed?: number }) => {
      if (!runId) throw new Error("No run_id");

      const missFamily = args.miss_family;
      if (!missFamily || missFamily === "normal") {
        throw new Error("No valid miss family — select a family from the retrain queue");
      }

      const payload = {
        run_id: runId,
        miss_family: missFamily,
        train_seed: args.train_seed ?? 42,
        gtest_seed: args.gtest_seed ?? 48,
        family_chosen_from_slice: "gdev44",
      };

      return api.post<LoopMResponse>("/defend/loop-m", payload);
    },
    onSuccess: (data) => {
      setResult({
        loopM: data,
        runAt: new Date().toISOString(),
      });
    },
  });

  return { loopM, hasScore: staticScore != null, runId, result };
}
