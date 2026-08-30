/** Command Center snapshot — mirrors GET /api/command-center/snapshot */

export interface CommandCenterSystem {
  status: string;
  postgres: boolean;
  pgvector: boolean;
  identify_live_search: boolean;
  tavily_configured: boolean;
  llm: Record<string, unknown>;
}

export interface CommandCenterKpis {
  atlas_techniques: string;
  atlas_count: number;
  live_rules: number;
  hitl_pending: number;
  loop_m_ap_delta: number | null;
  genuine_fpr: number | null;
  authgate_p50_ms: number | null;
}

export interface CoverageCellSnapshot {
  technique_id: string;
  vector_id: string | null;
  name: string | null;
  status: string | null;
  generate_mode: string | null;
  coverage_status: string;
  live_rule_ids?: string[];
  named_gap_reason?: string | null;
  draft_rule?: Record<string, unknown> | null;
  features_expected?: string[];
  scout_topic_hint?: string | null;
}

export interface CommandCenterCoverage {
  technique_count: number | null;
  cells: CoverageCellSnapshot[];
  status_counts: Record<string, number>;
  scout_topics_for_gaps: string[];
  generate_eligible: number;
}

export interface DefendMetrics {
  binary_ap?: number | null;
  recall_at_op?: number | null;
  precision_at_op?: number | null;
  genuine_fp?: number | null;
  f1_at_op?: number | null;
  tpr_at_fpr?: Record<string, number>;
  authgate_ms?: { p50?: number | null; p99?: number | null };
  app_ablation?: {
    with_flags_ap?: number | null;
    without_flags_ap?: number | null;
    delta?: number | null;
  };
  pass?: boolean | null;
}

export interface CommandCenterDefend {
  champion_run_id: string | null;
  metrics: DefendMetrics;
  drafts_pending: number;
  v0_rule_count: number;
}

export interface LoopMLast {
  run_id?: string;
  ap_delta?: number | null;
  pass?: boolean | null;
  genuine_fp_ok?: boolean | null;
}

export interface CommandCenterLoop {
  name: string;
  status: string;
  evidence: string;
}

export interface CommandCenterLabEvent {
  ts: string;
  phase: string;
  stage: string;
  level: string;
  message: string;
  loop: string | null;
  tech: string[];
  payload: Record<string, unknown>;
  thread_id: string;
}

export interface CommandCenterEthics {
  synthetic_only: boolean;
  catalog_solved: boolean;
  cat4_public_api: boolean;
  llm_not_detector: boolean;
}

export type PhaseStatusValue = "idle" | "active" | "running" | "complete" | "completed" | "error";

export interface CommandCenterSnapshot {
  generated_at: string;
  thread_id: string;
  system: CommandCenterSystem;
  kpis: CommandCenterKpis;
  atlas: {
    techniques: number;
    by_status: Record<string, number>;
    by_generate_mode: Record<string, number>;
  };
  coverage: CommandCenterCoverage;
  identify: {
    hitl_pending: number;
    hitl_approved: number;
    hitl_rejected: number;
    last_topic: string | null;
    last_run: Record<string, unknown>;
  };
  generate: {
    last_run: {
      run_id?: string;
      mode?: string;
      world_seed?: number | null;
      n_customers?: number | null;
      n_merchants?: number | null;
      sim_days?: number | null;
      row_count?: number | null;
      mix?: Record<string, unknown>;
      fidelity?: {
        pass?: boolean | null;
        psi_amount?: number | null;
        psi_hour?: number | null;
        fraud_rate?: number | null;
        mule_fan_in_median?: number | null;
        reasons?: string[];
      };
    };
    fidelity: Record<string, unknown>;
  };
  defend: CommandCenterDefend;
  evolve: {
    generation: number;
    loop_m_last: LoopMLast;
    retrain_queue: unknown[];
    catalog_solved: boolean;
  };
  loops: Record<string, CommandCenterLoop>;
  phase_status: Record<string, PhaseStatusValue | string>;
  lab_events: CommandCenterLabEvent[];
  ethics: CommandCenterEthics;
}

export interface CommandCenterBriefRequest {
  thread_id?: string;
  snapshot?: CommandCenterSnapshot | null;
}

export interface CommandCenterBriefResponse {
  generated_at: string;
  source: "llm" | "static" | string;
  text: string;
  disclaimer: string;
}
