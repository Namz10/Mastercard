import { useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { StatusChip } from "@/components/ui/StatusChip";
import { JobThread } from "@/components/ui/JobThread";
import { RunGate } from "@/components/ui/RunGate";
import { StickyContinue } from "@/components/layout/StickyContinue";
import { StageShell } from "@/components/layout/StageShell";
import { COPY } from "@/lib/copy";
import { formatInt } from "@/lib/format";
import { useElapsedJob } from "@/hooks/useElapsedJob";
import { useGenerateProgress } from "@/hooks/useGenerateProgress";
import { useSessionSnapshot, clearDefendIfStale } from "@/lib/session-store";
import type { GenerateRunResponse } from "@/lib/api-types";
import { useGenerate } from "./useGenerate";
import { LedgerTape } from "./LedgerTape";
import { LayeredMuleGraph } from "./LayeredMuleGraph";

function sessionToRun(session: ReturnType<typeof useSessionSnapshot>): GenerateRunResponse | null {
  if (!session.generate.runId) return null;
  return {
    run_id: session.generate.runId,
    mode: session.generate.scale,
    parquet_path: "",
    sidecar_path: "",
    fidelity: {
      pass: session.generate.fidelityPass === true,
      reasons: session.generate.fidelityReasons ?? undefined,
      mule_fan_in_median: session.generate.muleFanIn ?? undefined,
    },
    counts_by_label_family: session.generate.familyCounts ?? {},
    event_count: session.generate.eventCount ?? 0,
    world_seed: session.generate.seed ?? undefined,
  };
}

function GenerateLedgerSkeleton() {
  return (
    <div className="panel flex flex-col h-full min-h-0 opacity-60" aria-hidden>
      <div className="h-9 px-3 border-b border-border flex items-center shrink-0">
        <span className="font-mono text-[11px] uppercase text-ink-faint">Ledger tape</span>
      </div>
      <div className="flex-1 p-3 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-7 rounded-md bg-border/40 animate-pulse" style={{ width: `${70 + (i % 3) * 10}%` }} />
        ))}
      </div>
    </div>
  );
}

export function GeneratePage() {
  const session = useSessionSnapshot();
  const { simulate, stream } = useGenerate();
  const running = simulate.isPending || stream.running;
  const elapsed = useElapsedJob(running);
  const progress = useGenerateProgress(stream.lines);
  const seed = session.generate.seed ?? 42;

  const run = simulate.data ?? sessionToRun(session);
  const hasRun = Boolean(run && !running);
  const fidelityPass = run?.fidelity?.pass === true;
  const fidelityFail = hasRun && run?.fidelity?.pass === false;
  const reasons = run?.fidelity?.reasons ?? session.generate.fidelityReasons ?? [];

  const onSimulate = () => simulate.mutate();

  useEffect(() => {
    clearDefendIfStale();
  }, []);

  const counterParts: string[] = [];
  if (progress.eventCount != null) counterParts.push(`${formatInt(progress.eventCount)} events`);
  if (progress.customersDone != null && progress.nCustomers != null) {
    counterParts.push(`${formatInt(progress.customersDone)} / ${formatInt(progress.nCustomers)} customers`);
  }

  return (
    <StageShell
      title={COPY.nav.generate}
      caption={COPY.generate.caption}
      actions={
        hasRun || running ? (
          <Button variant="secondary" disabled={running} onClick={onSimulate}>
            {running ? COPY.generate.fidelityChecking : COPY.generate.primary}
          </Button>
        ) : null
      }
      footer={
        hasRun ? (
          <StickyContinue
            to="/defend/detection"
            label={COPY.generate.continue}
            demoId="continue-defend"
            secondary={
              <div className="flex items-center gap-2 min-w-0">
                <StatusChip status={fidelityPass ? "pass" : fidelityFail ? "fail" : "pending"} />
                {run ? (
                  <span className="font-mono text-[11px] text-ink-faint tabular-nums">
                    {formatInt(run.event_count)} events
                  </span>
                ) : null}
              </div>
            }
          />
        ) : undefined
      }
    >
      {simulate.error ? (
        <p className="text-[13px] text-signal-block mb-2 border border-signal-block/30 bg-surface px-3 py-2 rounded-sheet">
          Could not simulate. Retry.
        </p>
      ) : null}

      {running ? (
        <div className="flex-1 min-h-[420px] flex flex-col gap-2">
          <div
            className="shrink-0 h-12 flex items-center px-3 bento-panel catalog-scan-banner"
            data-demo="generate-scanning"
          >
            <div className="min-w-0 flex-1">
              <p className="text-[13px] text-ink truncate">
                {COPY.generate.primary} — {elapsed}s · seed {seed}
              </p>
              {counterParts.length > 0 ? (
                <p className="font-mono text-[11px] text-ink-faint tabular-nums mt-0.5">
                  {counterParts.join(" · ")}
                </p>
              ) : (
                <p className="text-[12px] text-ink-faint mt-0.5 truncate">
                  {progress.lastBody ?? COPY.generate.fidelityChecking}
                </p>
              )}
            </div>
            <span className="tape-live-dot shrink-0 ml-2" aria-hidden />
          </div>
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,62fr)_minmax(0,38fr)] gap-3 min-h-0">
            <JobThread
              lines={stream.lines}
              running
              title="Simulating payment traffic"
              emptyLabel={COPY.generate.fidelityChecking}
            />
            <GenerateLedgerSkeleton />
          </div>
        </div>
      ) : hasRun ? (
        <div className="booth-crossfade-enter flex-1 flex flex-col gap-2 min-h-0">
          <div
            className={
              fidelityPass ? "fidelity-strip fidelity-strip-pass shrink-0" : "fidelity-strip fidelity-strip-fail shrink-0"
            }
          >
            {fidelityPass ? <StatusChip status="pass" /> : <StatusChip status="fail" />}
            <span className="text-[13px]">
              {fidelityPass ? COPY.generate.fidelityPass : COPY.generate.fidelityFail}
              {run ? ` · ${formatInt(run.event_count)} events` : ""}
            </span>
          </div>
          {fidelityFail && reasons.length > 0 ? (
            <ul className="text-[12px] text-ink-muted list-disc pl-5 shrink-0 max-w-prose">
              {reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : null}
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-[minmax(0,62fr)_minmax(0,38fr)] gap-3 min-h-0">
            <LedgerTape run={run!} running={false} seed={seed} onSimulate={onSimulate} simulateDisabled={running} />
            <div className="flex flex-col min-h-0 gap-2.5">
              <LayeredMuleGraph run={run!} running={false} />
            </div>
          </div>
        </div>
      ) : (
        <RunGate
          verb="COMMIT"
          title="Simulate payment traffic"
          body={COPY.generate.empty}
          runLabel={COPY.generate.primary}
          onRun={onSimulate}
          running={running}
          runningDetail={running ? `${COPY.generate.fidelityChecking}… ${elapsed}s` : undefined}
          demoId="simulate"
        />
      )}
    </StageShell>
  );
}
