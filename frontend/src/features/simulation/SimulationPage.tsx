import { useCallback, useEffect, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { useGenerateRun } from "@/hooks/useGenerateRun";
import type { GenerateRunResponse } from "@/lib/api-types";
import { CountersStrip } from "./CountersStrip";
import { LabControls } from "./LabControls";
import { LaunchPanel } from "./LaunchPanel";
import { LedgerTable } from "./LedgerTable";
import { scrollLogToPhase, LiveLog } from "./LiveLog";
import { MuleGraph } from "./MuleGraph";
import { PipelineRail } from "./PipelineRail";
import { StageCard } from "./StageCard";
import { DEFAULT_THREAD_ID } from "./lab-types";
import { useLabStream } from "./useLabStream";
import { useSimulation } from "./useSimulation";

function fmtMeta(v: string | number | boolean | null | undefined): string {
  if (v == null) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(4);
  return v;
}

export function SimulationPage() {
  const lab = useLabStream({ threadId: DEFAULT_THREAD_ID });
  const resultsRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [generateOk, setGenerateOk] = useState<string | null>(null);
  const [fidelityOk, setFidelityOk] = useState(true);

  const hydrateFromHistory = lab.hydrateFromHistory;

  const onRunComplete = useCallback(
    async (data: GenerateRunResponse) => {
      const fid = data.fidelity?.pass === true;
      const reasons = (data.fidelity?.reasons ?? []).slice(0, 2).join("; ");
      setGenerateOk(
        fid
          ? `${data.mode} OK · run_id=${data.run_id} · events=${data.event_count} · fidelity=pass`
          : `${data.mode} exported · run_id=${data.run_id} · events=${data.event_count} · fidelity=FAIL${reasons ? ` (${reasons})` : ""}`,
      );
      setFidelityOk(fid);
      // Pull any backend-emitted lab events into the live log (SSE is flaky through Vite).
      try {
        await hydrateFromHistory();
      } catch {
        // ignore — ledger panel still shows the run
      }
      window.setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 50);
    },
    [hydrateFromHistory],
  );

  const { population, canary, latest, pending, errorText } = useSimulation({ onRunComplete });
  const { data: persistedRun } = useGenerateRun();

  useEffect(() => {
    if (pending) {
      setGenerateOk(null);
      setFidelityOk(true);
    }
  }, [pending]);

  const displayRun = latest ?? persistedRun;

  const metaChips = [
    { label: "run_id", value: fmtMeta(lab.meta.runId ?? displayRun?.run_id) },
    { label: "world_seed", value: fmtMeta(lab.meta.worldSeed ?? displayRun?.world_seed) },
    { label: "row_count", value: fmtMeta(lab.meta.rowCount ?? displayRun?.event_count) },
    { label: "fidelity.pass", value: fmtMeta(lab.meta.fidelityPass ?? displayRun?.fidelity?.pass) },
    { label: "ap_delta", value: fmtMeta(lab.meta.apDelta) },
  ];

  return (
    <div>
      <PageHeader
        title="Simulation Console"
        actions={
          <LabControls
            mode={lab.mode}
            onModeChange={lab.setMode}
            paused={lab.paused}
            onPausedChange={lab.setPaused}
            events={lab.events}
            nextPhase={lab.nextPhase}
            onBeforeRun={lab.clearEvents}
            hydrateFromHistory={lab.hydrateFromHistory}
            busy={busy}
            setBusy={setBusy}
            streamError={lab.streamError}
            onActionError={setActionError}
          />
        }
      />

      {actionError ? (
        <div className="mb-4 rounded border border-signal-block/40 bg-red-50 px-3 py-2 text-sm text-signal-block">
          {actionError}
        </div>
      ) : null}

      <PipelineRail
        phaseStatus={lab.phaseStatus}
        runId={lab.meta.runId ?? displayRun?.run_id ?? null}
        threadId={lab.meta.threadId}
        generation={lab.meta.generation}
        loopMarkers={lab.loopMarkers}
        onPhaseClick={scrollLogToPhase}
      />

      <div className="grid grid-cols-1 lg:grid-cols-10 gap-4 mb-4">
        <div className="lg:col-span-6">
          <StageCard current={lab.current} progress={lab.progress} elapsedMs={lab.elapsedMs} />
        </div>
        <div className="lg:col-span-4">
          <LiveLog events={lab.events} paused={lab.paused} metaChips={metaChips} />
        </div>
      </div>

      <div className="mb-6">
        <CountersStrip counters={lab.counters} ledgerSnippets={lab.ledgerSnippets} />
      </div>

      {/* Generate controls + results — always visible, not buried */}
      <div ref={resultsRef} className="mb-6 border border-border rounded p-4 bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <div className="font-mono text-xs uppercase tracking-wide text-ink-faint">Generate</div>
            <p className="text-xs text-ink-muted mt-0.5">
              Population / FinCEN canary — results show below and in the live log.
            </p>
          </div>
          <LaunchPanel population={population} canary={canary} />
        </div>

        {pending ? (
          <div className="flex items-center gap-2 text-sm text-ink-muted mb-3">
            <Spinner /> Running generate request…
          </div>
        ) : null}

        {errorText ? (
          <div className="mb-3 rounded border border-signal-block/40 bg-red-50 px-3 py-2 text-sm text-signal-block">
            {errorText}
          </div>
        ) : null}

        {generateOk ? (
          <div
            className={
              fidelityOk
                ? "mb-3 rounded border border-[#166534]/30 bg-green-50 px-3 py-2 text-sm font-mono text-[#166534]"
                : "mb-3 rounded border border-amber-400/50 bg-amber-50 px-3 py-2 text-sm font-mono text-amber-900"
            }
          >
            {generateOk}
          </div>
        ) : null}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <LedgerTable run={displayRun} />
          </Card>
          <Card>
            <MuleGraph run={displayRun} />
          </Card>
        </div>
      </div>

      <div className="mt-3 font-mono text-[10px] text-ink-faint">
        SSE {lab.connected ? "connected" : "idle"} · thread={DEFAULT_THREAD_ID} · mode={lab.mode} ·
        events={lab.events.length}
        {displayRun ? ` · last_run=${displayRun.run_id}` : ""}
      </div>
    </div>
  );
}
