from __future__ import annotations

from importlib.metadata import version

import pytest
import respx
from httpx import Response

from macrodata.app.runtime import build_runtime
from macrodata.core.errors import ValidationError
from macrodata.providers.cftc import CftcProvider
from macrodata.providers.deribit import DeribitPublicMarketProvider
from macrodata.providers.official_calendar import OfficialCalendarProvider
from macrodata.providers.official_fed_text import OfficialFedTextProvider
from macrodata.providers.okx import OkxPublicDataProvider
from macrodata.providers.treasury_auction import TreasuryAuctionProvider
from macrodata.providers.yahoo import YahooPriceProvider

VIX1D_SAMPLE_VALUE = 12.92
VIX9D_SAMPLE_VALUE = 18.12


def test_runtime_builds_catalog_and_gateway() -> None:
    runtime = build_runtime()

    assert runtime.catalog.get("fred:DGS10").dataset == "DGS10"
    assert runtime.gateway is not None


def test_runtime_wires_macro_core_proxy_providers() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("yahoo"), YahooPriceProvider)
    assert isinstance(runtime.gateway.provider("cftc"), CftcProvider)
    assert runtime.gateway.provider("cboe") is not None


def test_runtime_wires_okx_and_deribit_crypto_derivatives_providers() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("okx"), OkxPublicDataProvider)
    assert isinstance(runtime.gateway.provider("deribit"), DeribitPublicMarketProvider)


@pytest.mark.parametrize(
    ("series_key", "source_url", "expected_dataset", "csv_text", "expected_value"),
    [
        (
            "cboe:VIX1D",
            "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX1D_History.csv",
            "VIX1D",
            "DATE,OPEN,HIGH,LOW,CLOSE\n05/19/2026,13.600000,19.400000,11.700000,14.250000\n"
            "05/20/2026,14.300000,16.700000,10.800000,12.920000\n",
            VIX1D_SAMPLE_VALUE,
        ),
        (
            "cboe:VIX9D",
            "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv",
            "VIX9D",
            "DATE,OPEN,HIGH,LOW,CLOSE\n05/19/2026,16.100000,18.200000,15.900000,17.250000\n"
            "05/20/2026,17.300000,18.700000,16.800000,18.120000\n",
            VIX9D_SAMPLE_VALUE,
        ),
    ],
)
@respx.mock
def test_runtime_cboe_provider_fetches_official_volatility_index_history(
    series_key: str,
    source_url: str,
    expected_dataset: str,
    csv_text: str,
    expected_value: float,
) -> None:
    runtime = build_runtime()
    route = respx.get(source_url).mock(return_value=Response(200, text=csv_text))

    observations = runtime.gateway.fetch_series(series_key, start="2026-05-20", end="2026-05-20")

    assert route.called
    assert observations[0].series_key == series_key
    assert observations[0].provider == "cboe"
    assert observations[0].dataset == expected_dataset
    assert observations[0].observed_at == "2026-05-20"
    assert observations[0].value == expected_value
    assert observations[0].unit == "index"
    assert observations[0].frequency == "daily"
    assert observations[0].provenance == [{"provider": "cboe", "source_url": source_url}]


def test_runtime_wires_official_calendar_provider() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("official_calendar"), OfficialCalendarProvider)


def test_runtime_wires_official_fed_text_provider() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("official_fed_text"), OfficialFedTextProvider)


def test_runtime_wires_treasury_auction_provider() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("treasury_auction"), TreasuryAuctionProvider)


def test_runtime_rejects_unknown_cboe_dataset() -> None:
    runtime = build_runtime()

    with pytest.raises(ValidationError):
        runtime.gateway.fetch_latest("cboe:NOT_REAL")


def test_package_version_advances_for_crypto_derivatives_history_release() -> None:
    assert version("macrodata-cli") == "0.1.22"
