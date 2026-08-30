/**
 * AUTO-GENERATED from OpenAPI when backend is running:
 * npx openapi-typescript http://localhost:8000/openapi.json -o src/lib/api-types.ts
 *
 * Hand-maintained to match live FastAPI routes until codegen is re-run.
 */

export interface TechniqueChip {
  vector_id: string;
  technique_id: string;
  name: string;
  status: string;
  confidence_level: string;
  source_tier: number;
  generate_mode: string;
  category: number;
}

export interface TechniqueGroup {
  technique_id: string;
  name: string;
  status: string;
  confidence_level: string;
  source_tier: number;
  generate_mode: string;
  variants: number;
  chips: TechniqueChip[];
}

export interface ThreatMapResponse {
  categories: Record<string, TechniqueGroup[]>;
  technique_count: number;
}

export interface CoverageCell {
  technique_id: string;
  vector_id: string | null;
  name: string | null;
  status: string | null;
  generate_mode: string | null;
  coverage_status: string;
  live_rule_ids: string[];
  named_gap_reason: string | null;
  draft_rule: Record<string, unknown> | null;
  features_expected: string[];
  scout_topic_hint: string | null;
}

export interface CoverageMapResponse {
  technique_count: number;
  cells: CoverageCell[];
  status_counts: Record<string, number>;
  scout_topics_for_gaps: string[];
}

export interface HitlItem {
  vector_id: string;
  technique_id: string;
  nearest_technique_id: string;
  tier_badges: (number | string)[];
  source_urls: string[] | null;
  vector_class: string | null;
  generate_mode: string | null;
  simulatable_signals_preview: Record<string, unknown> | null;
  confidence_level: string | null;
  corroboration_type: string | null;
  name: string | null;
  field_diff: Record<string, unknown> | null;
  /** review = pending disposition; in_catalog = prior identify-* approval (demo context) */
  disposition?: "review" | "in_catalog";
}

export interface HitlQueueResponse {
  count: number;
  catalog_count?: number;
  items: HitlItem[];
}

export interface IdentifyRunResponse {
  run_id: string;
  scout_candidate_count: number;
  curator_kept_count: number;
  candidate_urls: string[];
  extracted_docs: unknown[];
  proposed_count: number;
  proposed_specs: unknown[];
  hitl_required: boolean;
  hitl_queue: unknown[];
  errors: string[];
}

export interface HitlDecisionResponse {
  vector_id: string;
  status: string;
}

export interface FidelityResult {
  pass: boolean;
  psi_amount?: number;
  psi_hour?: number;
  fraud_rate?: number;
  mule_fan_in_median?: number;
  reasons?: string[];
}

export interface GenerateRunResponse {
  run_id: string;
  mode: string;
  parquet_path: string;
  split_path?: string;
  sidecar_path: string;
  fidelity: FidelityResult;
  counts_by_label_family: Record<string, number>;
  event_count: number;
  vector_id?: string | null;
  sim_days?: number;
  world_seed?: number;
  n_customers?: number;
  n_merchants?: number;
  injector_id?: string | null;
  lifecycle_stages_logged?: { lifecycle_stage: string; party_id: string }[];
}

export interface ScoreMetrics {
  pass: boolean;
  n_eval: number;
  ap_by_family: Record<string, { ap: number }>;
  tpr_at_fpr: Record<string, number | { tpr: number; fpr_target?: number }>;
  genuine_fp: number;
  f1_at_op: number;
  precision_at_op: number;
  recall_at_op: number;
  binary_ap: number;
  confusion_matrix: number[][];
  op_threshold: number;
  recipe_hash: string;
  model_freeze_id: string;
  top_features: string[];
  n_pos?: Record<string, number>;
  [k: string]: unknown;
}

export interface ScoreResponse {
  run_id: string;
  model_run_id: string;
  metrics: ScoreMetrics;
  action_histogram: Record<string, number>;
  split: string;
  recipe_hash: string;
  model_freeze_id: string;
}

export interface FitResponse {
  run_id: string;
  model_run_id: string;
  metrics: ScoreMetrics;
  [k: string]: unknown;
}

export interface LoopMComparison {
  family: string;
  ap_before: number | null;
  ap_after: number | null;
  ap_delta: number | null;
  ap_verdict: string;
  genuine_fp_before: number | null;
  genuine_fp_after: number | null;
  genuine_fp_ok: boolean;
}

export interface LoopMResponse {
  run_id: string;
  miss_family: string;
  catalog_solved?: boolean;
  train_seed?: number;
  gtest_seed?: number;
  n_extra?: number;
  extra_row_cap?: number;
  extra_row_cap_frac?: number;
  genuine_fpr_eps?: number;
  comparison: LoopMComparison;
  metrics: {
    pass: boolean;
    gtest_before: ScoreMetrics;
    gtest_after: ScoreMetrics;
  };
  model_run_id_before: string;
  model_run_id_after: string;
  pass?: boolean;
}

export interface MergedTechnique {
  technique_id: string;
  name: string;
  coverage_status: string;
  vector_id: string | null;
  generate_mode: string | null;
  confidence_level: string | null;
  source_tier: number | null;
  live_rule_ids: string[];
  named_gap_reason: string | null;
  features_expected: string[];
  scout_topic_hint: string | null;
  variants: number;
  chips: TechniqueChip[];
  category: number;
}
