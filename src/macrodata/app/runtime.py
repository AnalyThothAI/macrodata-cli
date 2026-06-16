from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macrodata.app.services import MacrodataService
from macrodata.catalog.registry import CatalogRegistry, default_catalog
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.gateway.macrodata_gateway import MacrodataGateway
from macrodata.providers.cboe import CboeIndexProvider
from macrodata.providers.cftc import CftcProvider
from macrodata.providers.contracts import SeriesProvider
from macrodata.providers.fred import FredSeriesProvider
from macrodata.providers.nyfed import NyFedMarketsProvider
from macrodata.providers.official_calendar import OfficialCalendarProvider
from macrodata.providers.official_fed_text import OfficialFedTextProvider
from macrodata.providers.treasury_auction import TreasuryAuctionProvider
from macrodata.providers.treasury_fiscal import TreasuryFiscalProvider
from macrodata.providers.yahoo import YahooPriceProvider


@dataclass(frozen=True)
class MacrodataRuntime:
    catalog: CatalogRegistry
    http_client: MacrodataHttpClient
    gateway: MacrodataGateway
    service: MacrodataService


def build_runtime(
    *,
    timeout_sec: float = 10.0,
    fred_api_key: str | None = None,
    bundle_max_workers: int = 8,
    calendar_today: date | None = None,
) -> MacrodataRuntime:
    catalog = default_catalog()
    http_client = MacrodataHttpClient(timeout_sec=timeout_sec)
    providers: dict[str, SeriesProvider] = {
        "fred": FredSeriesProvider(http_client=http_client, api_key=fred_api_key),
        "nyfed": NyFedMarketsProvider(http_client=http_client),
        "treasury_fiscal": TreasuryFiscalProvider(http_client=http_client),
        "treasury_auction": TreasuryAuctionProvider(http_client=http_client, today=calendar_today),
        "cboe": CboeIndexProvider(http_client=http_client),
        "yahoo": YahooPriceProvider(timeout_sec=timeout_sec),
        "cftc": CftcProvider(http_client=http_client),
        "official_calendar": OfficialCalendarProvider(http_client=http_client, today=calendar_today),
        "official_fed_text": OfficialFedTextProvider(http_client=http_client, today=calendar_today),
    }
    gateway = MacrodataGateway(catalog=catalog, providers=providers)
    service = MacrodataService(gateway=gateway, max_workers=bundle_max_workers)
    return MacrodataRuntime(catalog=catalog, http_client=http_client, gateway=gateway, service=service)
