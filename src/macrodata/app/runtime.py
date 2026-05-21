from __future__ import annotations

from dataclasses import dataclass

from macrodata.app.services import MacrodataService
from macrodata.catalog.registry import CatalogRegistry, default_catalog
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.gateway.macrodata_gateway import MacrodataGateway
from macrodata.providers.contracts import SeriesProvider
from macrodata.providers.fred import FredSeriesProvider
from macrodata.providers.nyfed import NyFedMarketsProvider


@dataclass(frozen=True)
class MacrodataRuntime:
    catalog: CatalogRegistry
    http_client: MacrodataHttpClient
    gateway: MacrodataGateway
    service: MacrodataService


def build_runtime(*, timeout_sec: float = 10.0, fred_api_key: str | None = None) -> MacrodataRuntime:
    catalog = default_catalog()
    http_client = MacrodataHttpClient(timeout_sec=timeout_sec)
    providers: dict[str, SeriesProvider] = {
        "fred": FredSeriesProvider(http_client=http_client, api_key=fred_api_key),
        "nyfed": NyFedMarketsProvider(http_client=http_client),
    }
    gateway = MacrodataGateway(catalog=catalog, providers=providers)
    service = MacrodataService(gateway=gateway)
    return MacrodataRuntime(catalog=catalog, http_client=http_client, gateway=gateway, service=service)
