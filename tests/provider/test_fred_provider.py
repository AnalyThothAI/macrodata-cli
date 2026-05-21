from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
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


@respx.mock
def test_fred_range_rejects_malformed_numeric_values() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={"observations": [{"date": "2026-05-20", "value": "bad"}]},
        )
    )
    provider = FredSeriesProvider(http_client=MacrodataHttpClient(), api_key="test-key")

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("DGS10", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "fred"
    assert "DGS10" in raised.value.message
    assert "2026-05-20" in raised.value.message
    assert "test-key" not in raised.value.message


@respx.mock
def test_fred_range_rejects_non_dict_observation_rows() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(200, json={"observations": ["not-a-row"]})
    )
    provider = FredSeriesProvider(http_client=MacrodataHttpClient(), api_key="test-key")

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("DGS10", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.provider == "fred"
    assert "DGS10" in raised.value.message
