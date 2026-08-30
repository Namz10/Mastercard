import { Link } from "react-router-dom";
import { Radar, CreditCard, ShieldCheck } from "lucide-react";
import GlobeStudy from "@/components/ui/globe-study";
import { PixelBlast } from "@/components/ui/PixelBlast";
import { ModeChip } from "@/components/ui/ModeChip";
import { COPY } from "@/lib/copy";
import { useSessionSnapshot } from "@/lib/session-store";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

const LOOP_STEPS = [
  {
    icon: Radar,
    step: "01",
    label: COPY.nav.identify,
    desc: "Emerging typologies from allowlisted OSINT",
  },
  {
    icon: CreditCard,
    step: "02",
    label: COPY.nav.generate,
    desc: "Synthetic payment traffic at demo scale",
  },
  {
    icon: ShieldCheck,
    step: "03",
    label: COPY.nav.defend,
    desc: "Score on locked holdout — miss feeds the loop",
  },
] as const;

function StaticGlobePoster() {
  return (
    <div className="relative w-full h-full flex items-center justify-center overflow-hidden" aria-hidden>
      <div className="landing-globe-glow" />
      <div className="landing-globe-vignette" />
      <div
        className="absolute inset-0 opacity-50"
        style={{
          background:
            "radial-gradient(circle at 50% 45%, var(--sage-100) 0%, transparent 58%), linear-gradient(180deg, transparent 0%, rgba(238, 242, 234, 0.4) 100%)",
        }}
      />
      <div className="relative z-[3] w-[min(82%,520px)] aspect-square rounded-full border border-border/80 bg-surface/80 shadow-sm ring-1 ring-border/50 flex items-center justify-center backdrop-blur-sm">
        <div className="w-[88%] h-[88%] rounded-full border border-dashed border-sage-600/25" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">Threat surface</span>
        </div>
      </div>
    </div>
  );
}

export function LandingPage() {
  const session = useSessionSnapshot();
  const reducedMotion = usePrefersReducedMotion();

  return (
    <div className="landing-root min-h-screen flex flex-col">
      <header className="landing-header shrink-0 h-14 flex items-center justify-between px-6 lg:px-8">
        <div className="flex items-center gap-2.5">
          <span className="landing-header-mark" aria-hidden />
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-faint">
            GFF 2026
          </span>
        </div>
        <div className="landing-chip-slot">
          <ModeChip mode={session.ui.sourceChip} />
          <span className="hidden sm:inline text-hairline text-ink-faint select-none" aria-hidden>
            ·
          </span>
          <Link to="/identify" className="landing-skip-link">
            Skip to workspace
          </Link>
        </div>
      </header>

      <div className="landing-hero flex-1 relative min-h-0 lg:min-h-[calc(100vh-3.5rem)]">
        <div className="landing-canvas" aria-hidden>
          <div className="landing-mesh-wash" />
          <div className="landing-pixel-field">
            {!reducedMotion ? (
              <PixelBlast
                color="#3e6b4f"
                liquid={false}
                enableRipples={false}
                transparent
                pixelSize={6}
                edgeFade={0.16}
                patternScale={1.4}
                patternDensity={0.92}
                className="landing-pixel-blast"
              />
            ) : (
              <div className="landing-pixel-fallback-rich" aria-hidden />
            )}
          </div>
        </div>

        <div className="landing-grid relative z-[1] h-full min-h-[calc(100dvh-3.5rem)] lg:min-h-[calc(100vh-3.5rem)] grid lg:grid-cols-[minmax(0,36%)_minmax(0,64%)]">
          <section className="landing-content flex flex-col justify-center px-6 py-12 lg:px-12 lg:py-0 min-h-[min(46vh,440px)] lg:min-h-full">
            <div className="relative z-[2] max-w-[36rem] mx-auto lg:mx-0 w-full">
              <p className="landing-overline font-mono text-[11px] uppercase text-sage-600 mb-4">
                Closed-loop fraud operations
              </p>

              <h1 className="landing-wordmark font-serif font-medium text-ink leading-[0.92] tracking-[-0.04em]">
                {COPY.wordmark}
              </h1>

              <p className="landing-tagline mt-5 font-serif text-[22px] sm:text-[26px] lg:text-[28px] font-medium text-ink leading-[1.15] tracking-[-0.025em] text-balance">
                Catalog, discover, simulate, and defend — one{" "}
                <span className="landing-gradient-word">ledger</span>.
              </p>

              <p className="mt-5 text-[15px] lg:text-[16px] text-ink-muted leading-relaxed max-w-[42ch]">
                Twenty-four typologies on glass. Allowlisted OSINT proposes new attacks. Synthetic payment traffic
                proves fidelity. Detection scores on a locked holdout — miss feeds the next loop.
              </p>

              <ol className="mt-9 flex flex-col gap-2.5 sm:gap-3">
                {LOOP_STEPS.map((phase) => {
                  const Icon = phase.icon;
                  return (
                    <li key={phase.label} className="landing-step group">
                      <span className="landing-step-icon">
                        <Icon className="w-[18px] h-[18px]" strokeWidth={1.75} aria-hidden />
                      </span>
                      <div className="min-w-0 flex-1 pt-0.5">
                        <div className="flex items-center gap-2.5">
                          <span className="landing-phase-num">{phase.step}</span>
                          <p className="font-semibold text-[14px] text-ink leading-tight">{phase.label}</p>
                        </div>
                        <p className="mt-1 pl-[calc(1.75rem+0.625rem)] text-[12px] text-ink-faint leading-snug">
                          {phase.desc}
                        </p>
                      </div>
                    </li>
                  );
                })}
              </ol>

              <div className="mt-10 flex flex-wrap items-center gap-3">
                <Link to="/identify" className="landing-btn-primary">
                  Enter workspace
                </Link>
                <Link to="/identify" className="landing-btn-ghost">
                  Discover threats
                </Link>
              </div>
            </div>
          </section>

          <section className="landing-globe-panel relative min-h-[min(68vh,720px)] lg:min-h-full overflow-hidden">
            <div className="landing-globe-glow" />
            <div className="landing-globe-vignette" />
            <div className="landing-globe-stage">
              {reducedMotion ? (
                <StaticGlobePoster />
              ) : (
                <GlobeStudy mode="light" className="absolute inset-0" opacity={0.98} scale={1.5} />
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
