"""Seed KillChain Atlas from YAML catalog."""

import argparse
from pathlib import Path

from apps.api.db import Base, SessionLocal, engine
from apps.api.models import AtlasRow
from packages.catalog.loader import DEFAULT_SEED_PATH, load_catalog_yaml


def seed_catalog(path: Path | None = None, reset: bool = False) -> int:
    Base.metadata.create_all(bind=engine)
    specs = load_catalog_yaml(path)

    db = SessionLocal()
    try:
        if reset:
            db.query(AtlasRow).delete()
            db.commit()

        count = 0
        for spec in specs:
            row = AtlasRow(
                vector_id=spec.vector_id,
                technique_id=spec.technique_id.value,
                name=spec.name,
                status=spec.status.value,
                confidence_level=spec.confidence_level.value,
                source_tier=spec.source_tier,
                generate_mode=spec.generate_mode.value,
                category=spec.category,
                spec=spec.model_dump(mode="json"),
            )
            db.merge(row)
            count += 1
        db.commit()
        return count
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed KillChain Atlas from YAML")
    parser.add_argument("--path", type=Path, default=DEFAULT_SEED_PATH)
    parser.add_argument("--reset", action="store_true", help="Clear atlas before seeding")
    args = parser.parse_args()
    n = seed_catalog(args.path, reset=args.reset)
    print(f"Seeded {n} atlas rows from {args.path}")


if __name__ == "__main__":
    main()
