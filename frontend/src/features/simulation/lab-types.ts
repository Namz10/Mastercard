/** Lab SSE event schema — mirrors packages/lab/events.py LabEvent. */

export type LabPhase = "identify" | "generate" | "defend" | "evolve" | "system";

export type LabLevel = "info" | "stage" | "loop" | "warn" | "error" | "hitl";

export type PhaseStatus = "pending" | "active" | "completed" | "failed";

export type StreamMode = "live" | "replay";

export interface LabEvent {
  ts: string;
  phase: LabPhase;
  stage: string;
  level: LabLevel;
  message: string;
  loop: string | null;
  tech: string[];
  payload: Record<string, unknown>;
  thread_id: string;
}

export interface PipelinePhaseDef {
  id: Exclude<LabPhase, "system">;
  label: string;
  badges: string[];
}

export const PIPELINE_PHASES: PipelinePhaseDef[] = [
  { id: "identify", label: "IDENTIFY", badges: ["Loop C", "Loop I"] },
  { id: "generate", label: "GENERATE", badges: ["ShadowRail"] },
  { id: "defend", label: "DEFEND", badges: ["AuthGate", "Brake"] },
  { id: "evolve", label: "EVOLVE", badges: ["Loop M"] },
];

export const MACRO_PHASES = PIPELINE_PHASES.map((p) => p.id);

export interface LoopMarker {
  loop: string;
  kind: "open" | "close";
  ts: string;
  phase: LabPhase;
  pass?: boolean;
  index: number;
}

export interface LabCounters {
  events: number;
  rowsExported: number | null;
  fraudRate: number | null;
  fidelityPass: boolean | null;
  genuineFpr: number | null;
  authgateMsP50: number | null;
  modelFreezeId: string | null;
}

export interface LedgerSnippet {
  lifecycle_stage: string;
  party_id: string;
}

export interface PhaseStatusMap {
  identify: PhaseStatus;
  generate: PhaseStatus;
  defend: PhaseStatus;
  evolve: PhaseStatus;
}

export interface DemoRunRequest {
  thread_id: string;
  mode: StreamMode;
  skip_identify?: boolean;
  skip_generate?: boolean;
  skip_defend?: boolean;
  skip_evolve?: boolean;
  topic?: string;
  world_seed?: number;
  n_customers?: number;
  n_merchants?: number;
  sim_days?: number;
  miss_family?: string | null;
}

export interface DemoRunResponse {
  thread_id: string;
  stream_url?: string;
  status?: string;
  skip_evolve?: boolean;
  replayed?: number;
  path?: string;
}

export const DEFAULT_THREAD_ID = "demo-1";

export const DEMO_BODY: DemoRunRequest = {
  thread_id: DEFAULT_THREAD_ID,
  mode: "live",
  skip_evolve: true,
  // Same floor as LaunchPanel population — small worlds fail mule_fan_in fidelity.
  n_customers: 240,
  n_merchants: 40,
  sim_days: 30,
};
