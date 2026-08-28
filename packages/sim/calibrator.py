"""WorldCalibrator — fixture HTML → HITL patch. No live NPCI/Tavily (Plan 08 Phase F)."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from packages.sim.priors import DEFAULT_PRIORS_PATH, WorldPriors, load_priors, rupees_to_minor

_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = _ROOT / "data" / "fixtures" / "world_calibrator"
HISTORY_DIR = _ROOT / "data" / "priors_history"

VALUE_VOLUME_TOL = 0.05
UNCHANGED_EPS = 0.005

MAY_FILL_CATEGORIES = frozenset({"grocery", "fast_food", "utilities", "fuel", "telecom", "p2p"})
MUST_NOT_FILL_CATEGORIES = frozenset({"salary", "rent"})
HOUR_HEADERS = frozenset({"hour", "hours", "hour_of_day", "hod", "peak_hour"})

CATEGORY_ALIASES = {
    "grocery": "grocery",
    "kirana": "grocery",
    "food and grocery": "grocery",
    "fast food": "fast_food",
    "fast_food": "fast_food",
    "utilities": "utilities",
    "utility": "utilities",
    "fuel": "fuel",
    "petrol": "fuel",
    "telecom": "telecom",
    "mobile": "telecom",
    "p2p": "p2p",
    "peer to peer": "p2p",
    "salary": "salary",
    "rent": "rent",
}

ALLOWED_CLAIM = (
    "Quiet life calibrated to the latest approved public aggregates, with provenance."
)
FORBIDDEN_CLAIM = (
    "Not cloned live UPI; normal spend is not extracted from fraud news; "
    "kirana hours are not inferred from a mule article."
)


class CalibratorProposal(BaseModel):
    status: Literal["propose", "abstain"]
    reason: str
    source_url: str
    as_of_month: str
    raw_quotes: list[str] = Field(default_factory=list)
    fields_updated: list[str] = Field(default_factory=list)
    fields_unchanged: list[str] = Field(default_factory=list)
    patch: dict[str, Any] = Field(default_factory=dict)
    allowed_claim: str = ALLOWED_CLAIM
    forbidden_claim: str = FORBIDDEN_CLAIM


class _HTMLTables(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[dict[str, Any]] = []
        self._table: dict[str, Any] | None = None
        self._row: list[str] | None = None
        self._cell = ""
        self._in_cell = False
        self.source_hint = ""
        self._capture_p = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        if tag == "table":
            self._table = {
                "as_of": ad.get("data-as-of", ""),
                "id": ad.get("id", ""),
                "rows": [],
            }
        elif tag in {"td", "th"} and self._table is not None:
            self._in_cell = True
            self._cell = ""
            if self._row is None:
                self._row = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag == "p":
            self._capture_p = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", self._cell).strip())
            self._in_cell = False
        elif tag == "tr" and self._table is not None and self._row is not None:
            if any(c for c in self._row):
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        elif tag == "p":
            self._capture_p = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell += data
        if self._capture_p and "http" in data and not self.source_hint:
            found = re.search(r"https?://[^\s]+", data)
            if found:
                self.source_hint = found.group(0).rstrip(").,")


def _norm(cell: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", cell.strip().lower()).strip("_")


def _num(cell: str) -> float | None:
    cleaned = cell.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_hour_table(headers: list[str]) -> bool:
    return any(_norm(h) in HOUR_HEADERS or "hour" in _norm(h) for h in headers)


def _colmap(headers: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for i, h in enumerate(headers):
        n = _norm(h)
        if n in {"category", "mcc", "merchant_category"}:
            out["category"] = i
        elif n in {"volume", "txn", "transactions", "txn_count"}:
            out["volume"] = i
        elif n in {"value_rupees", "value", "amount_rupees", "value_inr"}:
            out["value"] = i
        elif n in {"avg_rupees", "avg", "average", "mean", "mean_rupees"}:
            out["avg"] = i
        elif n in {"field", "key", "name"}:
            out["field"] = i
        elif n in {"value", "val"} and "value" not in out:
            out["kv"] = i
    return out


def _rel_err(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-12)


def list_fixtures() -> list[str]:
    if not FIXTURE_DIR.is_dir():
        return []
    return sorted(p.name for p in FIXTURE_DIR.iterdir() if p.is_file())


def fixture_path(fixture_id: str) -> Path:
    name = fixture_id
    direct = FIXTURE_DIR / name
    if direct.is_file():
        return direct
    for p in FIXTURE_DIR.glob(f"{fixture_id}.*"):
        return p
    raise KeyError(f"unknown calibrator fixture: {fixture_id}")


def _abstain(reason: str, source_url: str, as_of: str, quotes: list[str]) -> CalibratorProposal:
    return CalibratorProposal(
        status="abstain",
        reason=reason,
        source_url=source_url,
        as_of_month=as_of,
        raw_quotes=quotes[:12],
        fields_updated=[],
        fields_unchanged=[
            "hour_of_day",
            "categories.salary",
            "categories.rent",
            "persona_weights",
            "persona_txn_per_day",
        ],
        patch={},
    )


def propose_from_bytes(
    payload: bytes,
    *,
    source_url: str,
    filename: str = "",
    current: WorldPriors | None = None,
) -> CalibratorProposal:
    current = current or load_priors()
    as_of = current.as_of_month
    if filename.lower().endswith(".pdf") or payload[:5] == b"%PDF-":
        return _abstain("pdf_not_supported", source_url, as_of, ["%PDF"])
    try:
        html = payload.decode("utf-8")
    except UnicodeDecodeError:
        return _abstain("not_utf8_html", source_url, as_of, [])
    return propose_from_html(html, source_url=source_url, current=current)


def propose_from_path(path: Path, *, current: WorldPriors | None = None) -> CalibratorProposal:
    source_url = f"fixture://world_calibrator/{path.name}"
    return propose_from_bytes(
        path.read_bytes(),
        source_url=source_url,
        filename=path.name,
        current=current,
    )


def propose_from_html(
    html: str,
    *,
    source_url: str,
    current: WorldPriors | None = None,
) -> CalibratorProposal:
    current = current or load_priors()
    parser = _HTMLTables()
    parser.feed(html)
    cited = parser.source_hint or source_url
    quotes: list[str] = []
    as_of = current.as_of_month
    category_means: dict[str, float] = {}
    kv: dict[str, float] = {}
    saw_hour_table = False
    mismatch = False

    for table in parser.tables:
        rows: list[list[str]] = table["rows"]
        if not rows:
            continue
        if table.get("as_of"):
            as_of = str(table["as_of"])
        headers = rows[0]
        if _is_hour_table(headers):
            saw_hour_table = True
            quotes.append("hour_table_ignored:" + "|".join(headers))
            continue
        cols = _colmap(headers)
        body = rows[1:] if len(rows) > 1 else []
        if "category" in cols and "volume" in cols and "value" in cols:
            for row in body:
                if max(cols.values()) >= len(row):
                    continue
                raw_cat = row[cols["category"]]
                cat = CATEGORY_ALIASES.get(raw_cat.strip().lower())
                vol = _num(row[cols["volume"]])
                val = _num(row[cols["value"]])
                pub = _num(row[cols["avg"]]) if "avg" in cols else None
                if cat is None or vol is None or val is None or vol <= 0:
                    continue
                computed = val / vol
                quote = f"{cat}: value={val} volume={vol} mean={computed:.4f}"
                if pub is not None:
                    quote += f" published_avg={pub}"
                quotes.append(quote)
                if pub is not None and _rel_err(pub, computed) > VALUE_VOLUME_TOL:
                    mismatch = True
                    quotes.append(f"abstain_mismatch_{cat}: published vs value/volume >5%")
                    continue
                if cat in MUST_NOT_FILL_CATEGORIES:
                    quotes.append(f"skip_assumption_category:{cat}")
                    continue
                if cat in MAY_FILL_CATEGORIES:
                    category_means[cat] = computed
        elif "field" in cols:
            val_i = cols.get("kv", cols.get("value"))
            if val_i is None:
                continue
            for row in body:
                if max(cols["field"], val_i) >= len(row):
                    continue
                key = _norm(row[cols["field"]])
                num = _num(row[val_i])
                if num is None:
                    continue
                kv[key] = num
                quotes.append(f"kv:{key}={num}")

    if mismatch and not category_means and "p2m_share" not in kv:
        return _abstain(
            "value_volume_avg_mismatch",
            cited,
            as_of,
            quotes,
        )

    fields_updated: list[str] = []
    fields_unchanged = [
        "hour_of_day",
        "categories.salary",
        "categories.rent",
        "lognormal_sigma",
        "persona_weights",
        "persona_txn_per_day",
    ]
    patch: dict[str, Any] = {}
    cat_patch: dict[str, Any] = {}
    for cat, mean in category_means.items():
        old = current.categories[cat].mean_rupees
        if _rel_err(mean, old) <= UNCHANGED_EPS:
            fields_unchanged.append(f"categories.{cat}.mean_rupees")
            continue
        cat_patch[cat] = {
            "mean_rupees": round(mean, 4),
            "kind": "mean_from_value_over_volume",
        }
        fields_updated.append(f"categories.{cat}.mean_rupees")
    if cat_patch:
        patch["categories"] = cat_patch

    if "p2m_share" in kv:
        share = kv["p2m_share"]
        if 0 < share < 1:
            if _rel_err(share, current.p2m_share) > UNCHANGED_EPS:
                patch["p2m_share"] = share
                fields_updated.append("p2m_share")
            else:
                fields_unchanged.append("p2m_share")

    cap_patch: dict[str, int] = {}
    mapping = {
        "txn_min_rupees": "txn_min_minor",
        "txn_max_rupees": "txn_max_minor",
        "day_max_rupees": "day_max_minor",
    }
    for src, dest in mapping.items():
        if src not in kv:
            continue
        minor = rupees_to_minor(kv[src])
        current_v = getattr(current.caps, dest)
        if minor != current_v:
            cap_patch[dest] = minor
            fields_updated.append(f"caps.{dest}")
        else:
            fields_unchanged.append(f"caps.{dest}")
    if cap_patch:
        patch["caps"] = cap_patch

    if as_of != current.as_of_month:
        patch["as_of_month"] = as_of
        fields_updated.append("as_of_month")
    else:
        fields_unchanged.append("as_of_month")

    if saw_hour_table:
        quotes.append("hour_of_day_not_filled:v1_assumption")

    if not fields_updated:
        reason = "no_fillable_public_aggregates"
        if saw_hour_table:
            reason = "fraud_or_hour_table_without_p2m_aggregates"
        return _abstain(reason, cited, current.as_of_month, quotes)

    patch["provenance"] = [
        {
            "source_url": cited,
            "note": "Fixture HTML value/volume means; not a live UPI clone.",
        }
    ]
    fields_updated.append("provenance")
    return CalibratorProposal(
        status="propose",
        reason="numeric_gate_passed",
        source_url=cited,
        as_of_month=as_of,
        raw_quotes=quotes[:20],
        fields_updated=fields_updated,
        fields_unchanged=fields_unchanged,
        patch=patch,
    )


def apply_proposal(current: WorldPriors, proposal: CalibratorProposal) -> WorldPriors:
    if proposal.status != "propose":
        raise ValueError("cannot apply abstain proposal")
    data = current.model_dump(mode="json")
    patch = dict(proposal.patch)
    patch.pop("hour_of_day", None)
    cats = dict(patch.get("categories") or {})
    for banned in MUST_NOT_FILL_CATEGORIES:
        cats.pop(banned, None)
    if "as_of_month" in patch:
        data["as_of_month"] = patch["as_of_month"]
    if "p2m_share" in patch:
        data["p2m_share"] = patch["p2m_share"]
    if "caps" in patch:
        data["caps"].update(patch["caps"])
    if cats:
        for key, blob in cats.items():
            if key not in MAY_FILL_CATEGORIES:
                continue
            data["categories"].setdefault(key, {"mean_rupees": 1.0, "rail": "upi_like"})
            data["categories"][key].update(blob)
    for item in patch.get("provenance") or []:
        urls = {p["source_url"] for p in data["provenance"]}
        if item["source_url"] not in urls:
            data["provenance"].append(item)
    data["ticket_stat"] = "mean_from_value_over_volume"
    return WorldPriors.model_validate(data)


def hitl_decide(
    action: Literal["approve", "reject"],
    proposal: CalibratorProposal,
    *,
    seed_path: Path | None = None,
    dest_path: Path | None = None,
) -> dict[str, Any]:
    seed_path = seed_path or DEFAULT_PRIORS_PATH
    current = load_priors(seed_path)
    seed_dump = current.model_dump(mode="json")
    if action == "reject":
        if dest_path is not None:
            dest_path.write_text(json.dumps(seed_dump, indent=2) + "\n", encoding="utf-8")
        return {
            "applied": False,
            "seed_unchanged": True,
            "priors": seed_dump,
        }
    if action != "approve":
        raise ValueError("action must be approve or reject")
    updated = apply_proposal(current, proposal)
    out = updated.model_dump(mode="json")
    wrote_seed = dest_path is not None and dest_path.resolve() == seed_path.resolve()
    if dest_path is not None:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return {"applied": True, "seed_unchanged": not wrote_seed, "priors": out}
