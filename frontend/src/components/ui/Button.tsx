import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger";

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={clsx(
        "px-3.5 py-2 rounded text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
        variant === "primary" && "bg-ink text-white hover:bg-ink/90",
        variant === "secondary" && "bg-surface border border-border text-ink hover:bg-surface-sunken",
        variant === "danger" && "bg-signal-block text-white hover:opacity-90",
        className,
      )}
      {...props}
    />
  );
}
