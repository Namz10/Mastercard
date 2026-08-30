import { useMemo, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusChip } from "@/components/ui/StatusChip";
import { useLatestRun } from "@/lib/latest-run-context";
import { formatPct } from "@/lib/format";
import { GTestChart } from "./GTestChart";
import { CoEvolutionChart } from "./CoEvolutionChart";
import { GenerationLedger } from "./GenerationLedger";
import { RetrainQueuePanel } from "./RetrainQueuePanel";
import { useArmsRace } from "./useArmsRace";
import { buildArmsRaceViewModel } from "./arms-race-vm";
import { useRetrainQueue } from "./useRetrainQueue";

export function ArmsRacePage() {
  const { loopM, hasScore, runId, result } = useArmsRace();
  const { lastScore } = useLatestRun();
  const loopMData = result?.loopM ?? null;
  const gtestRef = useRef<HTMLDivElement>(null);
  const queueRef = useRef<HTMLDivElement>(null);
  const [pulseBars, setPulseBars] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);

  const retrain = useRetrainQueue();
  const vm = useMemo(() => buildArmsRaceViewModel(loopMData), [loopMData]);
  const head = retrain.queue[0] ?? null;
  const approvedPass = Boolean(vm?.pass);

  const scrollToBarChart = () => {
    gtestRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setPulseBars(true);
    window.setTimeout(() => setPulseBars(false), 1600);
  };

  const scrollToQueue = () => {
    queueRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const onConfirmApprove = () => {
    if (!head || !runId) return;
    setApproveError(null);
    loopM.mutate(
      {
        miss_family: head.label_family,
        train_seed: 42,
        gtest_seed: 48,
      },
      {
        onSuccess: (data) => {
          const apDelta = data.comparison?.ap_delta ?? 0;
          const pass = Boolean(data.metrics?.pass);
          const fprOk = Boolean(data.comparison?.genuine_fp_ok);
          const apVerdict = data.comparison?.ap_verdict ?? "unknown";
          const softFail = !pass || !fprOk || apVerdict === "regressed";

          setModalOpen(false);

          if (softFail) {
            // Keep queue for retry; charts still refresh via useArmsRaceState
            console.warn("[Arms Race] Loop M soft-fail", { apVerdict, fprOk, pass });
            setApproveError(
              `Loop M completed but did not PASS (ap_verdict=${apVerdict} · genuine_fp_ok=${fprOk}). Queue kept for retry.`,
            );
            window.setTimeout(scrollToBarChart, 200);
            return;
          }

          retrain.completeFirstAsHistory({
            run_id: data.run_id,
            miss_family: data.miss_family,
            approved_at: new Date().toISOString(),
            pass: true,
            ap_delta: apDelta ?? 0,
            genuine_fp_ok: fprOk,
            ap_verdict: apVerdict,
          });
          window.setTimeout(scrollToBarChart, 200);
        },
        onError: (err) => {
          console.error("[Arms Race] Loop M failed", err);
          setApproveError((err as Error)?.message ?? "Loop M failed");
          setModalOpen(false);
          // Keep queue on API failure
        },
      },
    );
  };

  return (
    <div>
      <PageHeader
        title="Arms Race"
        actions={
          <>
            {approvedPass ? <StatusChip status="pass" /> : null}
            {vm ? (
              <span className="text-xs font-mono text-[#166534]">
                {vm.apDelta >= 0 ? "+" : ""}
                {formatPct(vm.apDelta, 2)} AP
              </span>
            ) : null}
            <Button variant="secondary" onClick={scrollToQueue} data-demo="review-retrain-queue">
              Review retrain queue ({retrain.queue.length})
            </Button>
          </>
        }
      />

      {!runId ? (
        <p className="text-sm text-ink-muted mb-4">Complete the generate → defend pipeline first.</p>
      ) : !hasScore && !lastScore ? (
        <p className="text-sm text-ink-muted mb-4">
          Fit and score the run on Decisioning before queuing Loop M.
        </p>
      ) : null}

      {vm ? (
        <div className="max-w-6xl mx-auto flex flex-col gap-6 mb-8">
          <div ref={gtestRef}>
            <GTestChart vm={vm} pulse={pulseBars} />
          </div>
          <CoEvolutionChart vm={vm.coEvolution} />
          <GenerationLedger
            vm={{
              ...vm.ledger,
              apDelta: vm.apDelta,
              apVerdict: vm.apVerdict,
              genuineFpOk: vm.genuineFpOk,
              pass: vm.pass,
              gtestSeed: vm.gtestSeed,
            }}
            onG1Click={scrollToBarChart}
          />
        </div>
      ) : (
        <div className="mb-8 max-w-6xl mx-auto">
          <EmptyState
            title="Charts appear after an approved Loop M retrain completes."
            detail="Miss inbox fills from Decisioning score_run. Loop M requires explicit analyst approval."
          />
        </div>
      )}

      <div ref={queueRef} className="max-w-6xl mx-auto scroll-mt-6">
        <RetrainQueuePanel
          misses={retrain.missRows}
          selectedIds={retrain.selectedIds}
          queuedFamilies={retrain.queuedFamilies}
          queue={retrain.queue}
          history={retrain.history}
          pending={loopM.isPending}
          modalOpen={modalOpen}
          modalItem={head}
          error={approveError}
          canAdd={retrain.canAdd}
          onToggle={retrain.toggleSelect}
          onToggleAll={retrain.toggleAll}
          onAddSelected={retrain.addSelected}
          onRemove={retrain.removeFromQueue}
          onMove={retrain.moveQueue}
          onOpenApprove={() => {
            if (!head) return;
            setApproveError(null);
            setModalOpen(true);
          }}
          onCancelApprove={() => setModalOpen(false)}
          onConfirmApprove={onConfirmApprove}
        />
      </div>
    </div>
  );
}
