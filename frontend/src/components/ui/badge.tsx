import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "border-border bg-canvas text-ink-muted",
        sage: "border-sage-600/25 bg-sage-100 text-sage-700",
        watch: "border-signal-watch/30 bg-canvas text-signal-watch",
        block: "border-signal-block/30 bg-canvas text-signal-block",
        outline: "border-border bg-transparent text-ink-faint",
        accent: "border-accent/25 bg-accent-muted text-accent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
