"""Load and validate catalog YAML."""

from pathlib import Path

import yaml

from packages.catalog.models import AttackSpec, TechniqueId


DEFAULT_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "catalog" / "seed.yaml"


def load_catalog_yaml(path: Path | str | None = None) -> list[AttackSpec]:
    """Parse and validate a YAML list of AttackSpec rows."""
    seed_path = Path(path) if path else DEFAULT_SEED_PATH
    raw = yaml.safe_load(seed_path.read_text())
    if not isinstance(raw, list):
        raise ValueError(f"Catalog YAML must be a list, got {type(raw)}")
    return [AttackSpec.model_validate(row) for row in raw]


def catalog_summary(specs: list[AttackSpec]) -> dict:
    """Summary stats for validation gates."""
    technique_ids = {s.technique_id for s in specs}
    generate_rows = [s for s in specs if s.generate_mode.value == "generate"]
    return {
        "count": len(specs),
        "technique_ids": sorted(t.value for t in technique_ids),
        "missing_techniques": sorted(
            set(TechniqueId) - technique_ids,
            key=lambda t: t.value,
        ),
        "generate_count": len(generate_rows),
    }
