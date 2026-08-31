import type { NavigateFunction } from "react-router-dom";
import { acceptCatalogSeed, setSourceChip } from "@/lib/session-store";

export interface BoothDemoDeps {
  navigate: NavigateFunction;
  simulate: () => Promise<unknown>;
  loadScore: () => Promise<unknown>;
}

/** Path B — recorded booth walk via ⌘K only. */
export async function runBoothDemo({ navigate, simulate, loadScore }: BoothDemoDeps): Promise<void> {
  acceptCatalogSeed();
  setSourceChip("recorded", "Booth demo");
  navigate("/generate");
  await simulate();
  await loadScore();
  navigate("/defend/detection");
}

export const BOOTH_DEMO_LABEL = "Run booth demo";
