import { PageHeader } from "@/components/layout/Topbar";
import { Card } from "@/components/ui/Card";
import { HitlQueueTable } from "./HitlQueueTable";
import { TopicResearchPanel } from "./TopicResearchPanel";

export function IdentifyPage() {
  return (
    <div>
      <PageHeader title="Identify" />
      <Card title="Topic research">
        <TopicResearchPanel />
      </Card>
      <div className="mt-6">
        <h2 className="font-mono text-xs uppercase text-ink-faint mb-3 tracking-wide">HITL queue</h2>
        <HitlQueueTable />
      </div>
    </div>
  );
}
