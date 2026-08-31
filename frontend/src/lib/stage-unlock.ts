import type { AegisSession } from "@/lib/session-store";
import { isDefendScoreCurrent } from "@/lib/session-store";

export type IdentifyStage = "landscape" | "discover" | "review";
export type DefendStage = "detection" | "interventions" | "feedback" | "hyperparameters";

export function identifyStageUnlocked(stage: IdentifyStage, session: AegisSession): boolean {
  if (stage === "landscape") return true;
  if (stage === "discover") return true;
  if (stage === "review") {
    return Boolean(session.identify.runId) || session.identify.approved.length > 0;
  }
  return false;
}

export function defendStageUnlocked(stage: DefendStage, session: AegisSession): boolean {
  const hasGenerate = Boolean(session.generate.runId);
  const hasScore = isDefendScoreCurrent(session);

  if (stage === "detection") return hasGenerate;
  if (stage === "interventions") return hasScore;
  if (stage === "feedback") return hasScore;
  if (stage === "hyperparameters") {
    const loopDone = Boolean(session.defend.loopResult);
    const tuneDone = Boolean(session.defend.tunedScore || session.defend.tuneResult);
    return loopDone || tuneDone || hasScore;
  }
  return false;
}

export function identifyStageLabel(stage: IdentifyStage): string {
  const labels: Record<IdentifyStage, string> = {
    landscape: "Landscape",
    discover: "Discover",
    review: "Review",
  };
  return labels[stage];
}

export function defendStageLabel(stage: DefendStage): string {
  const labels: Record<DefendStage, string> = {
    detection: "Detection",
    interventions: "Interventions",
    feedback: "Improve defense",
    hyperparameters: "Optuna",
  };
  return labels[stage];
}

export function previousIdentifyStage(stage: IdentifyStage): IdentifyStage | null {
  if (stage === "discover") return "landscape";
  if (stage === "review") return "discover";
  return null;
}

export function previousDefendStage(stage: DefendStage): DefendStage | null {
  if (stage === "interventions") return "detection";
  if (stage === "feedback") return "interventions";
  if (stage === "hyperparameters") return "feedback";
  return null;
}
