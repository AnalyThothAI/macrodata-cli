from __future__ import annotations

from macrodata.catalog.entries import CATALOG_ENTRIES
from macrodata.core.errors import ValidationError
from macrodata.core.models import SourceCatalogEntry


class CatalogRegistry:
    def __init__(self, *, entries: list[SourceCatalogEntry]) -> None:
        self._entries = {entry.series_key: entry for entry in entries}

    def list_entries(self) -> list[SourceCatalogEntry]:
        return sorted(self._entries.values(), key=lambda entry: entry.series_key)

    def get(self, series_key: str) -> SourceCatalogEntry:
        entry = self._entries.get(series_key)
        if entry is None:
            raise ValidationError(code="unknown_series", message=f"unknown series: {series_key}")
        return entry


def default_catalog() -> CatalogRegistry:
    return CatalogRegistry(entries=CATALOG_ENTRIES)
