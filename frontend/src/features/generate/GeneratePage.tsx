import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { COPY } from "@/lib/copy";
import { formatInt, FAMILY_LABEL } from "@/lib/format";
import { useSessionSnapshot } from "@/lib/session-store";
import type { GenerateRunResponse } from "@/lib/api-types";
import { useGenerate } from "./useGenerate";
import { LedgerTape } from "./LedgerTape";
import { LayeredMuleGraph } from "./LayeredMuleGraph";

export function GeneratePage() {
  const session = useSessionSnapshot();
  const { eligible, simulate, canary } = useGenerate();
  const running = simulate.isPending || canary.isPending;
  const fidelityKnown = session.generate.fidelityPass != null;
  const seed = session.generate.seed ?? 42;
  const sessionRun: GenerateRunResponse | null = session.generate.runId
    ? {
        run_id: session.generate.runId,
        mode: session.generate.scale,
        parquet_path: "",
        sidecar_path: "",
        fidelity: {
          pass: session.generate.fidelityPass ?? false,
          mule_fan_in_median: session.generate.muleFanIn ?? undefined,
        },
        counts_by_label_family: session.generate.familyCounts ?? {},
        event_count: session.generate.eventCount ?? 0,
        world_seed: session.generate.seed ?? 42,
      }
    : null;
  const run = simulate.data ?? canary.data ?? sessionRun;
  const families = Object.keys(run?.counts_by_label_family ?? {}).filter((k) => k !== "normal");

  return (
    <div className="flex flex-col h-[calc(100vh-88px)] min-h-0">
      <PageHeader
        title={COPY.nav.generate}
        caption={COPY.generate.empty}
        actions={
          <>
            <Button
              variant="primary"
              disabled={running}
              onClick={() => simulate.mutate("demo")}
              data-demo="simulate"
            >
              {COPY.generate.primary}
            </Button>
            <Button variant="secondary" disabled={running} onClick={() => simulate.mutate("full")}>
              {COPY.generate.fullPopulation}
            </Button>
            <Button variant="secondary" disabled={running} onClick={() => canary.mutate()}>
              {COPY.generate.canary}
            </Button>
            {fidelityKnown ? (
              <Link to="/defend">
                <Button variant="primary" data-demo="continue-defend">
                  {COPY.generate.continue}
                </Button>
              </Link>
            ) : null}
          </>
        }
      />

      {simulate.error || canary.error ? (
        <p className="text-[13px] text-signal-block mb-2 border border-signal-block/30 bg-surface px-3 py-2 rounded">
          Approved recipes missing — using catalog seed, or retry.
        </p>
      ) : null}

      <div className="h-9 shrink-0 flex items-center gap-2 text-[12px] text-ink-muted border-b border-border mb-2 pb-2">
        {(eligible.data?.count ?? 0) > 0 ? (
          families.length
            ? families.map((f) => (
                <span key={f} className="px-1.5 py-0.5 border border-border rounded-sm font-mono text-[10px]">
                  {FAMILY_LABEL[f] ?? f}
                </span>
              ))
            : <span>Eligible recipes loaded</span>
        ) : (
          <span>{COPY.generate.catalogSeed}</span>
        )}
        <span className="ml-auto font-mono text-[11px] text-ink-faint">demo 200 × 40 × 14d</span>
      </div>

      <div className="flex-1 grid grid-cols-[62%_38%] gap-3 min-h-0">
        <LedgerTape run={run} running={running} />
        <div className="flex flex-col min-h-0 gap-2">
          <div className="border border-border rounded bg-surface px-5 py-4 shrink-0">
            <div className="font-mono text-[11px] uppercase text-ink-faint tracking-wide">{COPY.generate.seedStamp}</div>
            <div className="font-mono text-[48px] leading-none text-ink font-tabular">{seed}</div>
            <div className="font-mono text-[12px] text-ink-muted mt-1">reproducible · pcg64 · demo</div>
          </div>
          <LayeredMuleGraph run={run} />
        </div>
      </div>

      <div className="h-10 shrink-0 mt-2 border-t border-border pt-2 flex items-center gap-4 font-mono text-[12px] text-ink-muted">
        {fidelityKnown ? (
          <span className={session.generate.fidelityPass ? "text-sage-600" : "text-signal-block"}>
            {session.generate.fidelityPass ? COPY.generate.fidelityPass : COPY.generate.fidelityFail}
          </span>
        ) : running ? (
          <span>{COPY.generate.fidelityChecking}</span>
        ) : (
          <span>{COPY.generate.continueDisabled}</span>
        )}
        {run ? <span className="ml-auto">{formatInt(run.event_count)} events</span> : null}
      </div>
    </div>
  );
}
