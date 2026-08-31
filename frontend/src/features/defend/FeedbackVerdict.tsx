import type { ScoreMetrics } from "@/lib/api-types";
import { COPY } from "@/lib/copy";
import { FAMILY_LABEL, formatPct } from "@/lib/format";
import { opPoint } from "@/features/decisioning/recall-fpr-data";

function familyLabel(family: string): string {
  return FAMILY_LABEL[family] ?? family.replace(/_/g, " ");
}

export function FeedbackVerdict({
  missFamily,
  before,
  after,
}: {
  missFamily: string;
  before: ScoreMetrics;
  after: ScoreMetrics;
}) {
  const beforeOp = opPoint(before);
  const afterOp = opPoint(after);
  const delta = afterOp.recallPct - beforeOp.recallPct;
  const deltaLabel = `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts recall`;
  const fpr = formatPct(after.genuine_fp, 3);

  return (
    <div className="flex flex-col justify-center gap-4 px-2 py-4 lg:py-0 min-w-0">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
        {familyLabel(missFamily)}
      </p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[12px] text-slate-600 mb-1">Before</p>
          <p className="font-mono text-[48px] lg:text-[56px] font-semibold text-slate-600 tabular-nums leading-none">
            {beforeOp.recallPct.toFixed(1)}%
          </p>
          <p className="font-mono text-[12px] text-ink-faint mt-2">@ genuine FPR {formatPct(before.genuine_fp, 3)}</p>
        </div>
        <div>
          <p className="text-[12px] text-sage-700 mb-1">After</p>
          <p className="font-mono text-[48px] lg:text-[56px] font-semibold text-sage-700 tabular-nums leading-none">
            {afterOp.recallPct.toFixed(1)}%
          </p>
          <p className="font-mono text-[12px] text-ink-faint mt-2">@ genuine FPR {fpr}</p>
        </div>
      </div>
      <span
        className={
          delta >= 0
            ? "inline-flex self-start font-mono text-[12px] px-2.5 py-1 rounded-full bg-sage-100 text-sage-800 border border-sage-600/25"
            : "inline-flex self-start font-mono text-[12px] px-2.5 py-1 rounded-full bg-rust-50 text-rust-800 border border-rust-600/25"
        }
      >
        {deltaLabel}
      </span>
      <p className="text-[13px] text-ink-muted leading-relaxed max-w-prose">
        Extra training of {familyLabel(missFamily)}. Graded on a new holdout — this loop cannot mark its own
        homework. Recall at the operating point {beforeOp.recallPct.toFixed(1)}% → {afterOp.recallPct.toFixed(1)}%.
        Genuine FPR {fpr}.
      </p>
      <p className="font-mono text-[10px] uppercase text-ink-faint">{COPY.defend.chartTitle}</p>
    </div>
  );
}
