import { FAMILY_LABEL } from "./format";
import type { LogLine } from "@/features/identify/useDiscoverStream";

export type GraphPoint = { value: number; label?: string };

/** Cumulative corpus size across simulate days (seeded, ends at event_count). */
export function buildCorpusGrowthSeries(
  eventCount: number,
  seed: number,
  days = 7,
): GraphPoint[] {
  if (eventCount <= 0) return [];
  let s = seed >>> 0;
  const rand = () => {
    s += 0x6d2b79f5;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const weights = Array.from({ length: days }, () => 0.4 + rand());
  const total = weights.reduce((a, b) => a + b, 0);
  let cumulative = 0;
  return weights.map((w, i) => {
    cumulative += Math.round((w / total) * eventCount);
    if (i === days - 1) cumulative = eventCount;
    return { label: `D${i + 1}`, value: cumulative };
  });
}

/** Fraud-family totals from generate run counts (excludes normal). */
export function buildFamilyCountSeries(counts: Record<string, number> | null | undefined): GraphPoint[] {
  if (!counts) return [];
  return Object.entries(counts)
    .filter(([k, n]) => k !== "normal" && n > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([key, value]) => ({
      label: (FAMILY_LABEL[key] ?? key).slice(0, 8),
      value,
    }));
}

/** Cumulative ops-log depth during Identify discover (real session stream). */
export function buildDiscoverTimeline(lines: LogLine[]): GraphPoint[] {
  if (lines.length === 0) return [];
  const bucket = Math.max(1, Math.ceil(lines.length / 8));
  const points: GraphPoint[] = [];
  for (let i = bucket; i <= lines.length; i += bucket) {
    const slice = lines.slice(0, i);
    const sources = new Set<string>();
    for (const line of slice) {
      const urls = line.artifacts?.urls;
      if (Array.isArray(urls)) urls.forEach((u) => sources.add(String(u)));
    }
    points.push({
      label: slice[slice.length - 1]?.verb ?? String(i),
      value: sources.size || slice.length,
    });
  }
  if (points.length === 0 || points[points.length - 1].value !== lines.length) {
    const last = lines[lines.length - 1];
    points.push({ label: last?.verb ?? "done", value: lines.length });
  }
  return points;
}
