import { Link } from "react-router-dom";
import { SYSTEM_STORY } from "@/content/system-story";
import { CountUp } from "@/components/ui/CountUp";

export function HowItWorksPage() {
  const explain = SYSTEM_STORY;

  return (
    <div className="min-h-screen bg-canvas text-ink">
      <header className="border-b border-border bg-paper-1 px-6 py-4 flex items-center justify-between">
        <h1 className="font-serif text-xl">How AegisLoop works</h1>
        <div className="flex gap-3">
          <Link to="/" className="text-[13px] text-ink-muted hover:text-ink">Landing</Link>
          <Link to="/identify" className="landing-btn-primary text-center">
            Enter workspace
          </Link>
        </div>
      </header>
      <main className="max-w-3xl mx-auto px-6 py-10 space-y-10">
        <section className="grid grid-cols-3 gap-4 text-center">
          <div className="rounded-bento border border-border p-4 bg-paper-1">
            <CountUp value={24} className="text-2xl font-medium tnum" />
            <p className="text-[12px] text-ink-muted mt-1">Techniques T01–T24</p>
          </div>
          <div className="rounded-bento border border-border p-4 bg-paper-1">
            <CountUp value={398431} className="text-2xl font-medium tnum" />
            <p className="text-[12px] text-ink-muted mt-1">Simulated events</p>
          </div>
          <div className="rounded-bento border border-border p-4 bg-paper-1">
            <CountUp value={98.52} decimals={1} suffix="%" className="text-2xl font-medium tnum" />
            <p className="text-[12px] text-ink-muted mt-1">Champion recall @ OP</p>
          </div>
        </section>

        {explain.map((section) => (
          <section key={section.id} className="rounded-bento border border-border bg-paper-1 p-6">
            <h2 className="text-lg font-medium">{section.title}</h2>
            <p className="text-[13px] text-sage-700 mt-1">{section.oneLine}</p>
            <p className="text-[14px] text-ink-muted mt-3 leading-relaxed">{section.body}</p>
            <ul className="mt-4 space-y-2">
              {section.bullets.map((b) => (
                <li key={b} className="text-[13px] text-ink flex gap-2">
                  <span className="text-sage-600 shrink-0">→</span>
                  {b}
                </li>
              ))}
            </ul>
          </section>
        ))}

        <section className="rounded-bento border border-border bg-paper-1 p-6">
          <h2 className="text-lg font-medium">ML pipeline (fit stages)</h2>
          <table className="w-full mt-4 text-[13px]">
            <thead>
              <tr className="text-ink-faint border-b border-border">
                <th className="py-2 text-left">Stage</th>
                <th className="py-2 text-left">What we do</th>
              </tr>
            </thead>
            <tbody className="text-ink-muted">
              <tr className="border-b border-border/50"><td className="py-2">Inner HGB</td><td>Threshold model on inner_fit only</td></tr>
              <tr className="border-b border-border/50"><td className="py-2">Outer HGB</td><td>Champion refit on full train</td></tr>
              <tr className="border-b border-border/50"><td className="py-2">Permutation</td><td>Feature importance on inner-val</td></tr>
              <tr className="border-b border-border/50"><td className="py-2">Bootstrap CI</td><td>Cluster resamples per family</td></tr>
              <tr><td className="py-2">Loop M</td><td>Retrain miss family; grade gtest 48</td></tr>
            </tbody>
          </table>
        </section>

        <p className="text-[12px] text-ink-faint text-center">
          Prototype mode: RECORDED packs from validation freeze. See docs/METRICS.md in repo.
        </p>
      </main>
    </div>
  );
}
