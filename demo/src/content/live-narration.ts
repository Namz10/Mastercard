/** Fallback narration when timeline tick omits now/why/happening */
export function fallbackNarration(verb: string, body: string): {
  now: string;
  why: string;
  happening: string;
} {
  const key = `${verb}::${body.slice(0, 40)}`;
  const table: Record<string, { now: string; why: string; happening: string }> = {
    "COLLECT::Collect started": {
      now: "Scanning allowlisted OSINT",
      why: "Only vetted URLs — not open web search.",
      happening: "FinCEN, RBI, IOC feeds",
    },
    "FIT::Train detector": {
      now: "Training inner HistGBM",
      why: "Threshold model — not shipped champion.",
      happening: "HistGradientBoostingClassifier on inner_fit",
    },
    "FIT::Outer model": {
      now: "Refit outer HGB on full train",
      why: "Threshold frozen — no eval peek.",
      happening: "Champion model training",
    },
    "INJECT::Layer mule": {
      now: "Overlaying mule campaigns",
      why: "Fan-in burst then cash-out paths.",
      happening: "Typed injector graph_mule",
    },
  };
  if (table[key]) return table[key];
  return {
    now: `${verb}: ${body}`,
    why: "Lab protocol step — see How it works.",
    happening: body,
  };
}
