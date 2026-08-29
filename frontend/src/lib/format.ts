export function formatPct(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function formatNum(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

export function formatInt(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString();
}

export const CATEGORY_LABELS: Record<number, string> = {
  1: "Mule & Settlement",
  2: "Identity & Onboarding",
  3: "Social Engineering / APP",
  4: "Adversarial AI / ML",
  5: "Merchant & BEC",
};

export function techniqueCategory(techniqueId: string): number {
  const n = parseInt(techniqueId.replace(/^T/i, ""), 10);
  if (Number.isNaN(n)) return 1;
  if (n <= 7) return 1;
  if (n <= 12) return 2;
  if (n <= 19) return 3;
  if (n <= 23) return 4;
  return 5;
}

export function coverageToChipStatus(coverageStatus: string): string {
  const map: Record<string, string> = {
    live_rule: "live_rule",
    draft_rule: "draft_rule",
    named_gap: "named_gap",
    case_only: "case_only",
    empty: "empty",
  };
  return map[coverageStatus] ?? coverageStatus;
}
