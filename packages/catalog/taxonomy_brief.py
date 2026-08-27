"""Compact T01–T24 taxonomy for curator and extract prompts."""

from packages.catalog.loader import load_catalog_yaml


def build_taxonomy_brief() -> str:
    specs = load_catalog_yaml()
    by_tid: dict[str, str] = {}
    for spec in specs:
        tid = spec.technique_id.value
        if tid not in by_tid:
            by_tid[tid] = f"{tid}: {spec.name} | cat{spec.category} {spec.rail.value} {spec.economic_class}"
    lines = []
    for i in range(1, 25):
        tid = f"T{i:02d}"
        if tid in by_tid:
            lines.append(by_tid[tid])
        else:
            lines.append(f"{tid}: (gap)")
    return "\n".join(lines)
