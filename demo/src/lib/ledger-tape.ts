import { FAMILY_LABEL } from "./format";

export interface TapeRow {
  id: string;
  clock: string;
  family: string;
  familyLabel: string;
  parties: string;
  amount: number;
  status: string;
}

const FAMILY_STATUS: Record<string, string> = {
  normal: "Allow",
  mule: "Restrict",
  identity_burst: "Hold",
  ato: "Notify",
  app_fraud: "Hold",
  invoice_fraud: "Notify",
};

const PAYERS = ["ravi", "meera", "arjun", "priya", "dev", "nina", "kabir", "isha"];
const PAYEES = ["shop", "fuel", "rent", "wallet", "payroll", "gift", "travel", "bills"];
const HANDLES = ["oksbi", "okicici", "okaxis", "paytm"];

function formatTapeClock(ms: number): string {
  const total = Math.floor(ms / 1000);
  const h = String(9 + (Math.floor(total / 3600) % 12)).padStart(2, "0");
  const m = String(Math.floor(total / 60) % 60).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  const frac = String(ms % 1000).padStart(3, "0");
  return `${h}:${m}:${s}.${frac}`;
}

function mulberry32(seed: number) {
  let s = seed >>> 0;
  return () => {
    s += 0x6d2b79f5;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Expand family counts into a last-40 payment tape. Seeded, not a live UPI feed. */
export function buildLedgerTape(
  counts: Record<string, number> | null | undefined,
  seed: number,
  cap = 40,
): TapeRow[] {
  const entries = Object.entries(counts ?? {}).filter(([, n]) => n > 0);
  if (entries.length === 0) return [];
  const total = entries.reduce((sum, [, n]) => sum + n, 0);
  const queues = entries.map(([family, n]) => {
    const share = Math.max(family === "normal" ? 0 : 1, Math.round((n / total) * cap));
    return Array.from({ length: share }, () => family);
  });
  const planned: string[] = [];
  let added = true;
  while (planned.length < cap && added) {
    added = false;
    for (const q of queues) {
      if (q.length > 0 && planned.length < cap) {
        planned.push(q.pop() as string);
        added = true;
      }
    }
  }
  const rows = planned.slice(0, cap);
  const rand = mulberry32(seed);
  return rows.map((family, i) => {
    const payer = PAYERS[Math.floor(rand() * PAYERS.length)];
    const payee = PAYEES[Math.floor(rand() * PAYEES.length)];
    const h1 = HANDLES[Math.floor(rand() * HANDLES.length)];
    const h2 = HANDLES[Math.floor(rand() * HANDLES.length)];
    const amount = family === "normal" ? 120 + Math.floor(rand() * 2400) : 800 + Math.floor(rand() * 48_000);
    return {
      id: `tape-${seed}-${i}`,
      clock: formatTapeClock(seed * 1000 + i * 900),
      family,
      familyLabel: FAMILY_LABEL[family] ?? family,
      parties: `${payer}***@${h1} → ${payee}***@${h2}`,
      amount,
      status: FAMILY_STATUS[family] ?? "Allow",
    };
  });
}
