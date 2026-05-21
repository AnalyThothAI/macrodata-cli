from __future__ import annotations

import respx
from httpx import Response

from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.fred import FredSeriesProvider

EXPECTED_VALUE = 4.57


@respx.mock
def test_fred_range_parses_observations() -> None:
    route = respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={
                "observations": [
                    {
                        "date": "2026-05-20",
                        "value": "4.57",
                        "realtime_start": "2026-05-21",
                        "realtime_end": "2026-05-21",
                    }
                ]
            },
        )
    )
    provider = FredSeriesProvider(http_client=MacrodataHttpClient(), api_key="test-key")

    observations = provider.get_range("DGS10", start="2026-05-20", end="2026-05-20")

    assert route.called
    assert observations[0].series_key == "fred:DGS10"
    assert observations[0].value == EXPECTED_VALUE
    assert observations[0].source_ts == "2026-05-20"
