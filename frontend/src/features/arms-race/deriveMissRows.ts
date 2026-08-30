import type { ScoreResponse } from "@/lib/api-types";
import {
  FAMILY_DISPLAY_NAME,
  FAMILY_TECHNIQUE_MAP,
  type MissRow,
} from "./retrain-types";

function familyName(family: string): string {
  return FAMILY_DISPLAY_NAME[family] ?? family.replace(/_/g, " ");
}

function techniqueFor(family: string): string {
  return FAMILY_TECHNIQUE_MAP[family] ?? "T??";
}

/**
 * Derive MissRow[] from a ScoreResponse.
 *
 * Honesty: recall_at_op is a binary operating-point metric, not per-family FN.
 * Prefer n_fn ≈ n_pos × (1 − recall_at_op) when n_pos is available; otherwise
 * surface n_pos as a proxy and label it clearly in the UI.
 */
export function deriveMissRowsFromScore(score: ScoreResponse | null): MissRow[] {
  if (!score?.metrics) return [];

  const metrics = score.metrics;
  const nPos = (metrics.n_pos ?? {}) as Record<string, number>;
  const apByFamily = metrics.ap_by_family ?? {};
  const recall = typeof metrics.recall_at_op === "number" ? metrics.recall_at_op : null;
  const evasion = recall != null ? Math.max(0, Math.min(1, 1 - recall)) : 0;

  const families = new Set<string>([
    ...Object.keys(nPos),
    ...Object.keys(apByFamily),
  ]);
  families.delete("normal");

  const rows: MissRow[] = [];

  for (const family of families) {
    const pos = nPos[family];
    const hasNPos = typeof pos === "number" && pos > 0;

    let n_fn: number;
    let n_fn_estimated: boolean;
    let n_fn_is_npos_proxy: boolean;

    if (hasNPos && recall != null) {
      n_fn = Math.max(0, Math.round(pos * (1 - recall)));
      n_fn_estimated = true;
      n_fn_is_npos_proxy = false;
    } else if (hasNPos) {
      n_fn = pos;
      n_fn_estimated = true;
      n_fn_is_npos_proxy = true;
    } else {
      // No n_pos — skip empty families with no positive support signal
      continue;
    }

    rows.push({
      id: `score:${score.run_id}:${family}`,
      technique_id: techniqueFor(family),
      name: familyName(family),
      label_family: family,
      n_fn,
      n_fn_estimated,
      n_fn_is_npos_proxy,
      evasion_pct: evasion,
      atlas_status: "open",
      source: "score_run",
      last_seen: "score_run / gdev44 slice",
    });
  }

  // Prefer higher estimated FN first within the inbox
  rows.sort((a, b) => b.n_fn - a.n_fn);
  return rows;
}
