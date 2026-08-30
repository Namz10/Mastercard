import { PageHeader } from "@/components/layout/Topbar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function CopilotPage() {
  return (
    <div>
      <PageHeader title="Analyst Copilot" />
      <Card title="Analyst Copilot">
        <p className="text-sm text-ink-muted leading-relaxed mb-4">
          Case summary generation. LLM is not the detector — copilot explains scores the classifier already
          produced.
        </p>
        <Button disabled>Coming soon</Button>
      </Card>
    </div>
  );
}
