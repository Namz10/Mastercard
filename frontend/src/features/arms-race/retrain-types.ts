/** Retrain-queue types for governed Loop M (HITL approval). */

export type AtlasStatus = "open" | "defending" | "solved";

export type MissSource = "score_run" | "manual_miss";

/**
 * Heuristic technique_id map (label_family → catalog technique).
 * mule→T01, app_fraud→T13, identity→T12, ato→T12, bec→T16
 */
export const FAMILY_TECHNIQUE_MAP: Record<string, string> = {
  mule: "T01",
  app_fraud: "T13",
  identity: "T12",
  identity_burst: "T12",
  ato: "T12",
  bec: "T16",
};

export const FAMILY_DISPLAY_NAME: Record<string, string> = {
  mule: "Mule fan-in funnel",
  app_fraud: "APP fraud",
  identity: "Identity burst",
  identity_burst: "Identity burst",
  ato: "Account takeover",
  bec: "BEC impersonation",
};

export interface MissRow {
  id: string;
  vector_id?: string;
  technique_id: string;
  name: string;
  label_family: string;
  /** Estimated FN count — see n_fn_estimated */
  n_fn: number;
  /** True when n_fn is estimated from n_pos × (1 − recall_at_op), not exact CM FN */
  n_fn_estimated: boolean;
  /** When true, UI should label the count as n_pos proxy (FN unknown) */
  n_fn_is_npos_proxy: boolean;
  evasion_pct: number;
  atlas_status: AtlasStatus;
  source: MissSource;
  last_seen?: string;
}

export interface RetrainQueueItem {
  id: string;
  label_family: string;
  technique_id: string;
  name: string;
  n_fn: number;
  n_fn_estimated: boolean;
  n_fn_is_npos_proxy: boolean;
  added_at: string;
  approved: boolean;
}

export interface RetrainHistoryEntry {
  id: string;
  run_id: string;
  miss_family: string;
  approved_at: string;
  pass: boolean;
  ap_delta: number;
  genuine_fp_ok: boolean;
  /** Always false — Loop M never auto-solves the catalog */
  catalog_solved: false;
  ap_verdict?: string;
}
