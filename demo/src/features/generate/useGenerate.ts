import { useGenerateEligible } from "@/features/defend/useDefend";
import { useGenerateJob, POPULATION_SCALE } from "@/lib/generate-job";

export { POPULATION_SCALE };

export function useGenerate() {
  const eligible = useGenerateEligible();
  const { simulate, stream } = useGenerateJob();
  return { eligible, simulate, stream, POPULATION_SCALE };
}
