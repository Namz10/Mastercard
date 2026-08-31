import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { StatusChip } from "@/components/ui/StatusChip";
import type { MergedTechnique } from "@/lib/api-types";
import { COPY } from "@/lib/copy";
import { coverageToChipStatus } from "@/lib/format";

function Row({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex justify-between gap-4 py-2 border-b border-border text-sm">
      <span className="text-ink-muted">{label}</span>
      <span className="font-mono text-xs text-right break-all">{value ?? "—"}</span>
    </div>
  );
}

export function TechniqueDetailDrawer({
  technique,
  onClose,
  onDiscoverGap,
}: {
  technique: MergedTechnique | null;
  onClose: () => void;
  onDiscoverGap?: (topic: string) => void;
}) {
  return (
    <Drawer open={!!technique} onClose={onClose} title={technique?.technique_id ?? "Technique"}>
      {technique ? (
        <div>
          <div className="mb-4">
            <h3 className="font-medium mb-2">{technique.name}</h3>
            <StatusChip status={coverageToChipStatus(technique.coverage_status)} />
          </div>
          <Row label="Attack ID" value={technique.technique_id} />
          <Row label="Confidence" value={technique.confidence_level} />
          <Row label="Source tier" value={technique.source_tier} />
          <Row label="Generate" value={technique.generate_mode} />
          <Row label="Variants" value={technique.variants} />
          {technique.live_rule_ids.length > 0 ? (
            <Row label="Live rules" value={technique.live_rule_ids.join(", ")} />
          ) : null}
          {technique.named_gap_reason ? (
            <Row label="Coverage gap" value={technique.named_gap_reason} />
          ) : null}
          {coverageToChipStatus(technique.coverage_status) === "named_gap" ||
          coverageToChipStatus(technique.coverage_status) === "empty" ||
          coverageToChipStatus(technique.coverage_status) === "case_only" ? (
            <Button
              variant="primary"
              className="mt-4"
              onClick={() => {
                onDiscoverGap?.(technique.name);
                onClose();
              }}
            >
              {COPY.identify.gapCta}
            </Button>
          ) : null}
          {technique.features_expected.length > 0 ? (
            <div className="mt-4">
              <div className="font-mono text-xs uppercase text-ink-faint mb-2">Evidence span</div>
              <ul className="space-y-1">
                {technique.features_expected.map((f) => (
                  <li key={f} className="text-sm font-mono text-ink-muted border-l-2 border-border pl-3">
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </Drawer>
  );
}
