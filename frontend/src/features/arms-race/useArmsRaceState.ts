import { usePersistedState } from "@/lib/usePersistedState";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import type { LoopMResponse } from "@/lib/api-types";

export interface ArmsRaceResult {
  loopM: LoopMResponse;
  runAt: string;
}

export function useArmsRaceState() {
  return usePersistedState<ArmsRaceResult | null>(STORAGE_KEYS.armsRaceResult, null);
}
