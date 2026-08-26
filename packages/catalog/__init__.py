"""KillChain Atlas catalog — AttackSpec models and loader."""

from packages.catalog.models import AttackSpec
from packages.catalog.loader import load_catalog_yaml

__all__ = ["AttackSpec", "load_catalog_yaml"]
