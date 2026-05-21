from __future__ import annotations

from macrodata.catalog.registry import CatalogRegistry
from macrodata.core.errors import ValidationError
from macrodata.core.models import MacroObservation, SourceCatalogEntry
from macrodata.core.series_key import parse_series_key
from macrodata.providers.contracts import SeriesProvider


class MacrodataGateway:
    def __init__(self, *, catalog: CatalogRegistry, providers: dict[str, SeriesProvider]) -> None:
        self._catalog = catalog
        self._providers = providers

    def provider(self, provider_name: str) -> SeriesProvider | None:
        return self._providers.get(provider_name)

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        parsed = parse_series_key(series_key)
        entry = self._catalog.get(parsed.value)
        provider = self.provider(parsed.provider)
        if provider is None:
            raise ValidationError(code="unknown_provider", message=f"unknown provider: {parsed.provider}")
        return [
            self._enrich_observation(observation, entry)
            for observation in provider.get_range(parsed.dataset, start=start, end=end)
        ]

    def fetch_latest(self, series_key: str) -> MacroObservation:
        parsed = parse_series_key(series_key)
        entry = self._catalog.get(parsed.value)
        provider = self.provider(parsed.provider)
        if provider is None:
            raise ValidationError(code="unknown_provider", message=f"unknown provider: {parsed.provider}")
        return self._enrich_observation(provider.get_latest(parsed.dataset), entry)

    def _enrich_observation(self, observation: MacroObservation, entry: SourceCatalogEntry) -> MacroObservation:
        return observation.model_copy(update={"unit": entry.unit, "frequency": entry.frequency})
