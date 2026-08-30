import { useState } from "react";
import clsx from "clsx";
import { Check, Copy } from "lucide-react";
import { COPY } from "@/lib/copy";
import { PixelBlast } from "@/components/ui/PixelBlast";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

export function SeedStamp({ seed }: { seed: number }) {
  const [flash, setFlash] = useState(false);
  const [copied, setCopied] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(String(seed));
    } catch {
      /* clipboard may be denied in tests */
    }
    setFlash(true);
    setCopied(true);
    window.setTimeout(() => setFlash(false), 160);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <button
      type="button"
      onClick={() => void copy()}
      title={copied ? "Copied · reproducible" : `${COPY.generate.seedStamp} ${seed} · reproducible`}
      data-demo="seed-stamp"
      className={clsx(
        "relative overflow-hidden bento-panel workspace-card-lift w-full min-h-[88px] px-4 py-3 flex items-center gap-3 text-left group shrink-0",
        "transition-[border-color,box-shadow] duration-140 hover:border-sage-600/30",
        flash && "sage-flash",
      )}
    >
      {!reducedMotion ? (
        <PixelBlast
          color="#3e6b4f"
          liquid={false}
          enableRipples={false}
          transparent
          className="opacity-[0.18]"
          patternDensity={0.85}
          edgeFade={0.35}
        />
      ) : (
        <div
          className="pixel-blast-fallback absolute inset-0"
          style={{ ["--pixel-color" as string]: "#3e6b4f" }}
          aria-hidden
        />
      )}

      <div className="relative z-[1] flex flex-col gap-0.5 shrink-0">
        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-faint">
          {COPY.generate.seedStamp}
        </span>
        <span className="font-mono text-[42px] leading-none text-ink font-tabular tracking-tight">{seed}</span>
      </div>

      <div className="relative z-[1] ml-auto flex flex-col items-end gap-1">
        <span
          className={clsx(
            "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border font-mono text-[10px] uppercase tracking-wide transition-all duration-140",
            copied
              ? "border-sage-600/40 bg-sage-100 text-sage-700"
              : "border-border bg-white/60 text-ink-faint group-hover:border-sage-600/25 group-hover:text-ink-muted",
          )}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" strokeWidth={2.5} />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 opacity-70" strokeWidth={2} />
              Copy
            </>
          )}
        </span>
        <span className="text-[10px] text-ink-faint">Reproducible</span>
      </div>
    </button>
  );
}
