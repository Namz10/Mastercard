import { usePersistedState, clearPersisted } from "@/lib/usePersistedState";
import { STORAGE_KEYS } from "@/lib/storage-keys";

export interface DecisionEntry {
  vector_id: string;
  name: string;
  decision: "accepted" | "rejected";
}

interface IdentifySession {
  topic: string | null;
  decisions: DecisionEntry[];
}

const EMPTY: IdentifySession = { topic: null, decisions: [] };

export function useIdentifySession() {
  const [session, setSession] = usePersistedState<IdentifySession>(STORAGE_KEYS.identifySession, EMPTY);

  function startNewTopic(topic: string) {
    setSession({ topic, decisions: [] });
    clearPersisted(STORAGE_KEYS.armsRaceResult);
  }

  function recordDecision(entry: DecisionEntry) {
    setSession((prev) => ({
      ...prev,
      decisions: [...prev.decisions.filter((d) => d.vector_id !== entry.vector_id), entry],
    }));
  }

  return { session, startNewTopic, recordDecision };
}
