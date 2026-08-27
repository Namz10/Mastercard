"""Atlas embedding preload — optional; not used for grounder reject (see grounder.py)."""

from packages.catalog.loader import load_catalog_yaml
from packages.osint.vector_store import clear_memory_store, register_catalog_embedding


def preload_catalog_embeddings() -> int:
    """Register seed catalog keys for librarian similarity helpers (optional)."""
    clear_memory_store()
    count = 0
    for spec in load_catalog_yaml():
        register_catalog_embedding(
            spec.name,
            spec.rail.value,
            spec.technique_id.value,
        )
        count += 1
    return count
