import type { OpsTapeLine } from "@/lib/ops-tape-types";

const BANNED = /\btavily\b|inner_val|scout\b|curator\b|librarian\b/i;

/** Map raw SSE / progress bodies to catalog language — never vendor names on glass. */
export function mapDiscoverCatalogLine(verb: string, body: string): { verb: string; body: string; skip?: boolean } {
  const v = (verb || "COLLECT").toUpperCase();
  const raw = body.trim();
  const low = raw.toLowerCase();

  if (low.includes("started") && v === "COLLECT") {
    return { verb: "COLLECT", body: "Open allowlisted OSINT collectors" };
  }

  if (low.includes("tavily")) {
    if (low.includes("candidates")) {
      return { verb: "RANK", body: "Rank OSINT candidates by regulator tier" };
    }
    const q = raw.replace(/^tavily search\s*·\s*/i, "").trim();
    return { verb: "COLLECT", body: q ? `Search — ${q}` : "Search allowlisted web" };
  }

  if (low.includes("rss")) return { verb: "COLLECT", body: "Regulator RSS feeds (FinCEN, RBI, FTC)" };
  if (low.includes("arxiv") || low.includes("preprint")) {
    return { verb: "COLLECT", body: "Academic preprints — payment fraud" };
  }
  if (low.includes("gnews") || low.includes("news")) {
    return { verb: "COLLECT", body: "News wire — payment fraud" };
  }

  if (v === "EXTRACT" || low.includes("reading articles") || low.includes("extract")) {
    return { verb: "EXTRACT", body: "Extract article bodies from sources" };
  }
  if (v === "RANK" || low.includes("ranking")) {
    return { verb: "RANK", body: "Rank sources by tier and corroboration" };
  }
  if (v === "GROUND" || low.includes("matching") || low.includes("corroborat") || low.includes("scoring source")) {
    return { verb: "GROUND", body: "Ground findings to MITRE-style catalog" };
  }
  if (v === "PROPOSE" || low.includes("propos")) {
    const n = raw.match(/(\d+)/)?.[1];
    return {
      verb: "PROPOSE",
      body: n ? `${n} candidate attack${n === "1" ? "" : "s"} for catalog review` : "Candidate attacks for catalog review",
    };
  }
  if (v === "REPLAY") {
    return { verb: "REPLAY", body: raw.includes("recorded") ? raw : `${raw} · recorded` };
  }

  if (BANNED.test(raw)) {
    return { verb: v, body: "Catalog research step", skip: false };
  }

  return { verb: v, body: raw };
}

export function hostFromUrl(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function sourceTitle(url: string): string {
  const host = hostFromUrl(url);
  if (host.includes("fincen")) return "FinCEN advisory";
  if (host.includes("ftc.gov")) return "FTC consumer alert";
  if (host.includes("rbi.org")) return "RBI circular";
  if (host.includes("arxiv")) return "arXiv preprint";
  if (host.includes("cisa")) return "CISA alert";
  return host;
}

export function sourceTier(host: string): "regulator" | "news" | "academic" | "other" {
  if (/fincen|rbi|ftc|cisa|europa|gov\.uk|npci/.test(host)) return "regulator";
  if (/arxiv|ieee|acm/.test(host)) return "academic";
  if (/reuters|bloomberg|techcrunch/.test(host)) return "news";
  return "other";
}

export function mergeCatalogLine(prev: OpsTapeLine[], next: OpsTapeLine): OpsTapeLine[] {
  if (prev.length === 0) return [next];
  return [...prev, next];
}
