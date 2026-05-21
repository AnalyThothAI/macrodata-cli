from __future__ import annotations

from typing import Protocol

from macrodata.core.models import MacroObservation, ProviderSmokeResult


class SeriesProvider(Protocol):
    provider_name: str

    def get_latest(self, dataset: str) -> MacroObservation:
        raise NotImplementedError

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        raise NotImplementedError

    def smoke(self) -> ProviderSmokeResult:
        raise NotImplementedError
