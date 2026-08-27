"""Atlas embedding preload into Postgres pgvector."""

from packages.catalog.loader import load_catalog_yaml
from packages.osint.vector_store import register_catalog_embedding


def preload_catalog_embeddings() -> int:
    """Register seed catalog keys for librarian / grounder cosine dedup."""
    count = 0
    for spec in load_catalog_yaml():
        register_catalog_embedding(
            spec.name,
            spec.rail.value,
            spec.technique_id.value,
            vector_id=spec.vector_id,
        )
        count += 1
    return count
