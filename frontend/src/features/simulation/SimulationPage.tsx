/** Quarantined GFF 2026 — off nav. Proof-only lab. Do not restore to chrome. */
import { PageHeader } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { LaunchPanel } from "./LaunchPanel";
import { LedgerTable } from "./LedgerTable";
import { useGenerateRun } from "@/hooks/useGenerateRun";
import { Spinner } from "@/components/ui/Spinner";
import { MuleGraph } from "./MuleGraph";
import { useSimulation } from "./useSimulation";

export function SimulationPage() {
  const { latest, population, canary } = useSimulation();
  const { data: persistedRun, isLoading: generateLoading } = useGenerateRun();
  const error = population.error ?? canary.error;
  const displayRun = latest ?? persistedRun;
  const loading = generateLoading || (population.isLoading || canary.isLoading);

  return (
    <div>
      <PageHeader title="Simulation Console" actions={<LaunchPanel population={population} canary={canary} />} />
      {error ? (
        <p className="text-sm text-signal-block mb-4">
          Last run failed — ensure approved vectors exist in the catalog.
        </p>
      ) : null}
      {loading && (
        <div className="flex items-center justify-center py-4">
          <Spinner />
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <LedgerTable run={displayRun} />
        </Card>
        <Card>
          <MuleGraph run={displayRun} />
        </Card>
      </div>
    </div>
  );
}
