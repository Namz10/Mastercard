import type { HitlItem } from "@/lib/api-types";

export function hitlDedupeKey(item: HitlItem): string {
  const technique = (item.technique_id ?? "").trim().toUpperCase();
  const name = (item.name ?? "").trim().toLowerCase();
  return `${technique}|${name}`;
}

/** Dedupe HITL rows by vector_id, then by technique+name identity. Preserves order. */
export function dedupeHitlItems(items: HitlItem[]): HitlItem[] {
  const seenIds = new Set<string>();
  const seenKeys = new Set<string>();
  const out: HitlItem[] = [];

  for (const item of items) {
    const id = item.vector_id;
    if (id && seenIds.has(id)) continue;

    const key = hitlDedupeKey(item);
    if (key !== "|" && seenKeys.has(key)) continue;

    if (id) seenIds.add(id);
    if (key !== "|") seenKeys.add(key);
    out.push(item);
  }

  return out;
}

export function pendingHitlItems(items: HitlItem[]): HitlItem[] {
  return dedupeHitlItems(items.filter((i) => i.disposition !== "in_catalog"));
}
