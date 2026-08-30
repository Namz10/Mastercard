import clsx from "clsx";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={clsx(
        "h-9 px-4 rounded-full text-[13px] font-medium disabled:opacity-40 disabled:cursor-not-allowed",
        "transition-[background-color,transform,box-shadow,border-color] duration-[120ms] ease-out",
        variant === "primary" &&
          "bg-accent text-accent-fg hover:bg-accent-hover shadow-[var(--landing-shadow-lift)] hover:-translate-y-px hover:shadow-[0_6px_20px_rgba(62,107,79,0.28),0_2px_6px_rgba(25,28,25,0.1)] active:translate-y-0 motion-reduce:transform-none motion-reduce:shadow-[var(--landing-shadow-lift)]",
        variant === "secondary" &&
          "bg-surface-solid border border-border text-ink hover:bg-accent-muted",
        variant === "ghost" &&
          "bg-white/70 border border-[var(--landing-glass-border)] text-ink hover:bg-white hover:border-accent-border hover:-translate-y-px hover:shadow-[var(--landing-shadow-soft)] active:translate-y-0 motion-reduce:transform-none",
        variant === "danger" && "bg-signal-block text-paper-1 hover:opacity-90",
        className,
      )}
      {...props}
    />
  );
}
