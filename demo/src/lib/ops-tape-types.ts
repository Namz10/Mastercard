/** Shared ops tape line — DESIGN.md §6 geometry */
export type OpsTapeVerb =
  | "COLLECT"
  | "EXTRACT"
  | "RANK"
  | "GROUND"
  | "PROPOSE"
  | "REPLAY"
  | "COMMIT"
  | "INJECT"
  | "FIDELITY"
  | "FIT"
  | "SCORE"
  | "APPLY"
  | "RETRAIN";

export type OpsTapeLineStatus = "pending" | "active" | "done";

export interface OpsTapeLine {
  id: string;
  t?: number;
  clock?: string;
  verb: OpsTapeVerb | string;
  body: string;
  status?: OpsTapeLineStatus | string;
  artifacts?: Record<string, unknown>;
}

export interface OpsTapeStage {
  id: string;
  verb: OpsTapeVerb | string;
  body: string;
  /** Elapsed ms before this stage becomes active */
  afterMs: number;
  /** Optional dynamic body while active */
  activeBody?: (elapsedMs: number) => string;
}
