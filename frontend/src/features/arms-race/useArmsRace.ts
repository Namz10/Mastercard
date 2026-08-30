import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api-client";
import type { LoopMResponse } from "@/lib/api-types";
import { useLatestRun } from "@/lib/latest-run-context";
import { useDecisioningState } from "@/features/decisioning/useDecisioningState";
import { useArmsRaceState } from "./useArmsRaceState";

function pickMissFamily(lastScore: import("@/lib/api-types").ScoreResponse | null): string {
  const nPos = lastScore?.metrics?.n_pos as Record<string, number> | undefined;
  if (nPos) {
    const fraudFamilies = Object.entries(nPos).filter(([k]) => k !== "normal");
    if (fraudFamilies.length > 0) {
      return fraudFamilies.sort((a, b) => b[1] - a[1])[0][0];
    }
  }
  const apByFamily = lastScore?.metrics?.ap_by_family ?? {};
  let worst = "app_fraud";
  let worstAp = Infinity;
  for (const [family, val] of Object.entries(apByFamily)) {
    const ap = typeof val === "object" && val && "ap" in val ? (val as { ap: number }).ap : 1;
    if (ap < worstAp) {
      worstAp = ap;
      worst = family;
    }
  }
  return worst;
}

export function useArmsRace() {
  const { runId } = useLatestRun();
  const { score: staticScore } = useDecisioningState();
  const [result, setResult] = useArmsRaceState();

  const loopM = useMutation({
    mutationFn: (args?: { train_seed: number; gtest_seed: number }) => {
      if (!runId) throw new Error("No run_id");

      const missFamily = pickMissFamily(staticScore);
      if (!missFamily || missFamily === "normal") {
        throw new Error("No valid miss family available — score the run first");
      }

      const payload = {
        run_id: runId,
        miss_family: missFamily,
        train_seed: 42,
        gtest_seed: 48,
        family_chosen_from_slice: "gdev44",
        ...(args ?? {}),
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
