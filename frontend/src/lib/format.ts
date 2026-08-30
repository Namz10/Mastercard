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
  return value.toLocaleString("en-IN");
}

export function formatInr(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `₹${value.toLocaleString("en-IN")}`;
}

export const FAMILY_LABEL: Record<string, string> = {
  normal: "quiet",
  mule: "mule",
  identity_burst: "identity burst",
  ato: "ATO",
  app_fraud: "APP scam",
  invoice_fraud: "invoice",
};

export const FAMILY_TO_TECHNIQUE: Record<string, string> = {
  mule: "T02",
  identity_burst: "T08",
  ato: "T09",
  app_fraud: "T13",
  invoice_fraud: "T24",
};

export function missFamilyToTechnique(family: string): string {
  return FAMILY_TO_TECHNIQUE[family] ?? "T13";
}

export function worstApFamily(apByFamily: Record<string, { ap: number } | number> | undefined): string {
  if (!apByFamily) return "app_fraud";
  let worst = "app_fraud";
  let worstAp = Infinity;
  for (const [family, val] of Object.entries(apByFamily)) {
    if (family === "normal") continue;
    const ap = typeof val === "object" && val && "ap" in val ? val.ap : Number(val);
    if (ap < worstAp) {
      worstAp = ap;
      worst = family;
    }
  }
  return worst;
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
