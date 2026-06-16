from __future__ import annotations

from importlib.metadata import version

import pytest
import respx
from httpx import Response

from macrodata.app.runtime import build_runtime
from macrodata.core.errors import ValidationError
from macrodata.providers.cftc import CftcProvider
from macrodata.providers.official_calendar import OfficialCalendarProvider
from macrodata.providers.official_fed_text import OfficialFedTextProvider
from macrodata.providers.treasury_auction import TreasuryAuctionProvider
from macrodata.providers.yahoo import YahooPriceProvider

VVIX_SAMPLE_VALUE = 91.34


def test_runtime_builds_catalog_and_gateway() -> None:
    runtime = build_runtime()

    assert runtime.catalog.get("fred:DGS10").dataset == "DGS10"
    assert runtime.gateway is not None


def test_runtime_wires_macro_core_proxy_providers() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("yahoo"), YahooPriceProvider)
    assert isinstance(runtime.gateway.provider("cftc"), CftcProvider)
    assert runtime.gateway.provider("cboe") is not None


@respx.mock
def test_runtime_cboe_provider_fetches_official_volatility_index_history() -> None:
    runtime = build_runtime()
    route = respx.get("https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv").mock(
        return_value=Response(
            200,
            text="DATE,VVIX\n05/19/2026,88.120000\n05/20/2026,91.340000\n",
        )
    )

    observations = runtime.gateway.fetch_series("cboe:VVIX", start="2026-05-20", end="2026-05-20")

    assert route.called
    assert observations[0].series_key == "cboe:VVIX"
    assert observations[0].provider == "cboe"
    assert observations[0].dataset == "VVIX"
    assert observations[0].observed_at == "2026-05-20"
    assert observations[0].value == VVIX_SAMPLE_VALUE
    assert observations[0].unit == "index"
    assert observations[0].frequency == "daily"
    assert observations[0].provenance == [
        {"provider": "cboe", "source_url": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv"}
    ]


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


def test_package_version_advances_for_cboe_volatility_release() -> None:
    assert version("macrodata-cli") == "0.1.18"
