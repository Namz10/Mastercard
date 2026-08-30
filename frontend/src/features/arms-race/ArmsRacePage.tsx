import { useMemo, useRef, useState } from "react";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusChip } from "@/components/ui/StatusChip";
import { GTestChart } from "./GTestChart";
import { CoEvolutionChart } from "./CoEvolutionChart";
import { GenerationLedger } from "./GenerationLedger";
import { useArmsRace } from "./useArmsRace";
import { buildArmsRaceViewModel } from "./arms-race-vm";
import { formatPct } from "@/lib/format";

export function ArmsRacePage() {
  const { loopM, hasScore, runId, result } = useArmsRace();
  const loopMData = result?.loopM ?? null;
  const gtestRef = useRef<HTMLDivElement>(null);
  const [pulseBars, setPulseBars] = useState(false);

  const vm = useMemo(() => buildArmsRaceViewModel(loopMData), [loopMData]);

  const scrollToBarChart = () => {
    gtestRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    setPulseBars(true);
    window.setTimeout(() => setPulseBars(false), 1600);
  };

  return (
    <div>
      <PageHeader
        title="Arms Race"
        actions={
          <>
            {vm ? (
              <>
                <StatusChip status={vm.pass ? "pass" : "fail"} />
                <span className="text-xs font-mono text-[#166534]">
                  {vm.apDelta >= 0 ? "+" : ""}
                  {formatPct(vm.apDelta, 2)} AP
                </span>
              </>
            ) : null}
            <Button
              variant="primary"
              disabled={!runId || !hasScore || loopM.isPending}
              onClick={() => loopM.mutate()}
              data-demo="run-loop-m"
            >
              {loopM.isPending ? "Running Loop M…" : "Run Loop M"}
            </Button>
          </>
        }
      />

      {!runId ? (
        <p className="text-sm text-ink-muted mb-4">Complete the generate → defend pipeline first.</p>
      ) : !hasScore ? (
        <p className="text-sm text-ink-muted mb-4">Fit and score the run on Decisioning before running Loop M.</p>
      ) : null}
      {loopM.isError ? (
        <p className="text-sm text-signal-block mb-4">
          {(loopM.error as Error)?.message ?? "Loop M failed — fit and score the run on Decisioning first."}
        </p>
      ) : null}

      {vm ? (
        <div className="max-w-6xl mx-auto flex flex-col gap-6">
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
        <EmptyState
          title={
            loopM.isPending
              ? "Running feedback loop…"
              : "Run Loop M to compare base model vs post-feedback performance."
          }
        />
      )}
    </div>
  );
}
