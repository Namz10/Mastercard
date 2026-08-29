import { PageHeader } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { LaunchPanel } from "./LaunchPanel";
import { LedgerTable } from "./LedgerTable";
import { MuleGraph } from "./MuleGraph";
import { useSimulation } from "./useSimulation";

export function SimulationPage() {
  const { latest, population, canary } = useSimulation();
  const error = population.error ?? canary.error;

  return (
    <div>
      <PageHeader title="Simulation Console" actions={<LaunchPanel population={population} canary={canary} />} />
      {error ? (
        <p className="text-sm text-signal-block mb-4">
          Last run failed — ensure approved vectors exist in the catalog.
        </p>
      ) : null}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <LedgerTable run={latest} />
        </Card>
        <Card>
          <MuleGraph run={latest} />
        </Card>
      </div>
    </div>
  );
}
