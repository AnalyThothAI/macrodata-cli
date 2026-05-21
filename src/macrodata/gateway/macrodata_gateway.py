from __future__ import annotations

from macrodata.catalog.registry import CatalogRegistry
from macrodata.core.errors import ValidationError
from macrodata.core.models import MacroObservation
from macrodata.core.series_key import parse_series_key
from macrodata.providers.contracts import SeriesProvider


class MacrodataGateway:
    def __init__(self, *, catalog: CatalogRegistry, providers: dict[str, SeriesProvider]) -> None:
        self._catalog = catalog
        self._providers = providers

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        parsed = parse_series_key(series_key)
        self._catalog.get(parsed.value)
        provider = self._providers.get(parsed.provider)
        if provider is None:
            raise ValidationError(code="unknown_provider", message=f"unknown provider: {parsed.provider}")
        return provider.get_range(parsed.dataset, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        parsed = parse_series_key(series_key)
        self._catalog.get(parsed.value)
        provider = self._providers.get(parsed.provider)
        if provider is None:
            raise ValidationError(code="unknown_provider", message=f"unknown provider: {parsed.provider}")
        return provider.get_latest(parsed.dataset)
