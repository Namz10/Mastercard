import type { OpsTapeLine } from "@/lib/ops-tape-types";

const BANNED = /\[(fit|score)\]|inner_val|bootstrap_ci|HGBM|HGB|permutation_importance/i;

const STAGE_BODY: Record<string, string> = {
  load_parquet: "Load holdout parquet",
  inner_hgb: "Train detector",
  permutation_importance: "Which features moved the score",
  bootstrap_ci: "Checking stability on holdout",
};

/** Map backend progress to booth English — never raw stderr on glass. */
export function mapJobCatalogLine(verb: string, body: string): { verb: string; body: string; skip?: boolean } {
  const v = (verb || "FIT").toUpperCase();
  const raw = body.trim();
  const low = raw.toLowerCase();

  if (low.includes("quiet traffic") || low.includes("quiet events")) {
    return { verb: "COMMIT", body: raw };
  }

  if (low.includes("write train/split parquet")) {
    return { verb: "COMMIT", body: raw };
  }

  if (low.startsWith("start ") || low.startsWith("done ")) {
    const stage = raw.split(/\s+/)[1] ?? raw;
    const mapped = STAGE_BODY[stage] ?? stage.replace(/_/g, " ");
    return { verb: v === "DONE" ? v : "FIT", body: mapped };
  }

  if (low.includes("bootstrap_ci") || low.includes("resample")) {
    const m = raw.match(/family=(\w+).*?(\d+)\/(\d+)/i);
    if (m) {
      const fam = m[1].replace(/_/g, " ");
      return { verb: "FIT", body: `Stability — ${fam} ${m[2]} of ${m[3]}` };
    }
    return { verb: "FIT", body: "Checking stability on holdout" };
  }

  if (low.includes("trial") && low.includes("of")) {
    return { verb: "TUNE", body: raw };
  }

  if (BANNED.test(raw) && !STAGE_BODY[raw]) {
    const stage = raw.replace(/^\[fit\]\s*/i, "").replace(/^start\s+/i, "");
    if (STAGE_BODY[stage]) return { verb: "FIT", body: STAGE_BODY[stage] };
    return { verb: v, body: raw.replace(/^\[fit\]\s*/i, "").replace(/_/g, " ") };
  }

  return { verb: v, body: raw };
}

export function mergeJobLine(prev: OpsTapeLine[], next: OpsTapeLine): OpsTapeLine[] {
  if (prev.length === 0) return [next];
  const last = prev[prev.length - 1];
  // Update in-place only for rapid bootstrap resample ticks on the same family
  if (
    last.verb === "FIT" &&
    next.verb === "FIT" &&
    last.body.startsWith("Stability —") &&
    next.body.startsWith("Stability —") &&
    last.body.split(" ")[1] === next.body.split(" ")[1]
  ) {
    return [...prev.slice(0, -1), { ...next, id: last.id }];
  }
  if (
    last.verb === "COMMIT" &&
    next.verb === "COMMIT" &&
    last.body.startsWith("Quiet traffic") &&
    next.body.startsWith("Quiet traffic")
  ) {
    return [...prev.slice(0, -1), { ...next, id: last.id, status: "active" }];
  }
  return [...prev, next];
}
