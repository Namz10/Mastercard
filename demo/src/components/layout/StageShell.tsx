import type { ReactNode } from "react";
import { PageHeader } from "@/components/layout/Topbar";

export function StageShell({
  title,
  caption,
  census,
  actions,
  secondaryActions,
  strip,
  children,
  footer,
}: {
  title: string;
  caption?: string;
  census?: ReactNode;
  actions?: ReactNode;
  secondaryActions?: ReactNode;
  strip?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex flex-col h-full min-h-0 relative -mx-4 -my-3 px-4 py-3">
      <PageHeader
        title={title}
        caption={caption}
        census={census}
        actions={actions}
        secondaryActions={secondaryActions}
        strip={strip}
      />
      <div className="flex-1 min-h-0 flex flex-col">{children}</div>
      {footer}
    </div>
  );
}
