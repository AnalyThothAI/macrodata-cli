from __future__ import annotations

from macrodata.core.models import MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway


class MacrodataService:
    def __init__(self, *, gateway: MacrodataGateway) -> None:
        self._gateway = gateway

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        return self._gateway.fetch_series(series_key, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        return self._gateway.fetch_latest(series_key)
