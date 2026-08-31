import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { JobThread } from "@/components/ui/JobThread";
import { StageShell } from "@/components/layout/StageShell";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { COPY } from "@/lib/copy";
import { formatPct } from "@/lib/format";
import { useDefend } from "./useDefend";

function CompareColumn({ label, recall, fpr }: { label: string; recall: string; fpr: string }) {
  return (
    <div className="flex-1 bento-panel px-4 py-5 text-center">
      <p className="text-[13px] text-ink-muted mb-2">{label}</p>
      <p className="font-mono text-[36px] font-semibold text-ink tabular-nums leading-none">{recall}%</p>
      <p className="font-mono text-[12px] text-ink-faint mt-2">@ FPR {fpr}</p>
    </div>
  );
}

export function HyperparametersPage() {
  const { session, tune } = useDefend();
  const [error, setError] = useState<string | null>(null);
  const miss = session.defend.missTechniqueId;
  const base = session.defend.scoreBeforeRetrain?.metrics ?? session.defend.score?.metrics ?? null;
  const afterFeedback = session.defend.loopResult ? session.defend.score?.metrics ?? null : null;
  const afterOptuna = session.defend.tunedScore?.metrics ?? null;
  const tuneDone = Boolean(session.defend.tuneResult);
  const skipped = Boolean(session.defend.tuneResult?.optuna_skipped_small_n);

  const onRunTune = async () => {
    setError(null);
    try {
      await tune.mutateAsync();
    } catch {
      setError(COPY.defend.tuneFail);
    }
  };

  const fmt = (m: typeof base) =>
    m
      ? {
          recall: (m.recall_at_op * 100).toFixed(2),
          fpr: formatPct(m.genuine_fp, 3),
        }
      : null;

  return (
    <StageShell
      title={COPY.stages.hyperparameters}
      caption={COPY.defend.hyperparametersCaption}
      actions={
        !tuneDone && !tune.isPending ? (
          <Button
            variant="primary"
            className="h-11 px-6"
            disabled={!session.generate.runId}
            onClick={() => void onRunTune()}
            data-demo="run-optuna"
          >
            {COPY.defend.runOptuna}
          </Button>
        ) : undefined
      }
      footer={
        tuneDone ? (
          <StickyContinue
            to={miss ? `/identify?highlight=${miss}` : "/identify"}
            label={COPY.defend.backIdentify}
            demoId="continue-identify"
          />
        ) : undefined
      }
    >
      {error ? <ErrorBanner message={error} onRetry={() => void onRunTune()} /> : null}
      {skipped ? (
        <p className="text-[13px] text-ink-muted mb-4 border border-border bg-surface px-3 py-2 rounded-sheet">
          {COPY.defend.optunaSkipped}
        </p>
      ) : null}

      {tune.isPending || tune.stream.running ? (
        <div className="flex-1 min-h-[420px] flex flex-col">
          <JobThread
            lines={tune.stream.lines}
            running
            title="Optuna search"
            emptyLabel={COPY.defend.optunaRunning}
          />
        </div>
      ) : !tuneDone ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-6">
          <p className="text-[14px] text-ink-muted text-center max-w-md">{COPY.defend.hyperparametersCaption}</p>
          <Button
            variant="primary"
            className="h-11 px-8"
            disabled={!session.generate.runId}
            onClick={() => void onRunTune()}
            data-demo="run-optuna"
          >
            {COPY.defend.runOptuna}
          </Button>
        </div>
      ) : (
        <div className="booth-crossfade-enter flex-1 flex flex-col gap-3">
          <div className="flex gap-3 min-h-0">
            {fmt(base) ? (
              <CompareColumn label={COPY.defend.compareBase} recall={fmt(base)!.recall} fpr={fmt(base)!.fpr} />
            ) : null}
            {fmt(afterFeedback) ? (
              <CompareColumn
                label={COPY.defend.compareFeedback}
                recall={fmt(afterFeedback)!.recall}
                fpr={fmt(afterFeedback)!.fpr}
              />
            ) : (
              <div className="flex-1 bento-panel px-4 py-5 text-center flex items-center justify-center">
                <p className="text-[13px] text-ink-faint">—</p>
              </div>
            )}
            {fmt(afterOptuna) ? (
              <CompareColumn
                label={COPY.defend.compareOptuna}
                recall={fmt(afterOptuna)!.recall}
                fpr={fmt(afterOptuna)!.fpr}
              />
            ) : null}
          </div>
          {miss ? (
            <p className="text-[12px] text-ink-faint">
              <Link to={`/identify?highlight=${miss}`} className="hover:text-ink underline-offset-2 hover:underline">
                {COPY.defend.backIdentify}
              </Link>
            </p>
          ) : null}
        </div>
      )}
    </StageShell>
  );
}
