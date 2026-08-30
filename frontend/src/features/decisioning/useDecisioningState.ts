import { usePersistedState } from "@/lib/usePersistedState";
import { STORAGE_KEYS } from "@/lib/storage-keys";
import type { ScoreResponse } from "@/lib/api-types";

interface TrainingState {
  status: "idle" | "completed";
  completedAt: string | null;
}

const INITIAL_TRAINING: TrainingState = { status: "idle", completedAt: null };

export function useDecisioningState() {
  const [training, setTraining] = usePersistedState<TrainingState>(
    STORAGE_KEYS.decisioningTraining,
    INITIAL_TRAINING,
  );
  const [score, setScore] = usePersistedState<ScoreResponse | null>(STORAGE_KEYS.decisioningScore, null);

  return { training, setTraining, score, setScore };
}
