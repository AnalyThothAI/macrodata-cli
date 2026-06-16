from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.app.runtime import build_runtime

VVIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv"
SKEW_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv"
VIX9D_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv"
LATEST_SKEW_VALUE = 143.75


@pytest.mark.parametrize(
    ("series_key", "url", "csv_text", "expected_value"),
    [
        ("cboe:VVIX", VVIX_URL, "DATE,VVIX\n05/19/2026,88.120000\n05/20/2026,91.340000\n", 91.34),
        ("cboe:SKEW", SKEW_URL, "DATE,SKEW\n05/19/2026,141.250000\n05/20/2026,143.750000\n", 143.75),
        (
            "cboe:VIX9D",
            VIX9D_URL,
            "DATE,OPEN,HIGH,LOW,CLOSE\n05/19/2026,16.100000,18.200000,15.900000,17.250000\n"
            "05/20/2026,17.300000,18.700000,16.800000,18.120000\n",
            18.12,
        ),
    ],
)
@respx.mock
def test_cboe_provider_parses_official_index_history_csv(
    series_key: str,
    url: str,
    csv_text: str,
    expected_value: float,
) -> None:
    route = respx.get(url).mock(return_value=Response(200, text=csv_text))
    runtime = build_runtime()

    observations = runtime.gateway.fetch_series(series_key, start="2026-05-20", end="2026-05-20")

    assert route.called
    assert len(observations) == 1
    assert observations[0].series_key == series_key
    assert observations[0].provider == "cboe"
    assert observations[0].observed_at == "2026-05-20"
    assert observations[0].value == expected_value
    assert observations[0].unit == "index"
    assert observations[0].frequency == "daily"
    assert observations[0].latency_class == "daily"
    assert observations[0].data_quality == "ok"
    assert observations[0].provenance == [{"provider": "cboe", "source_url": url}]


@respx.mock
def test_cboe_provider_latest_returns_last_available_row() -> None:
    respx.get(SKEW_URL).mock(
        return_value=Response(
            200,
            text="DATE,SKEW\n05/19/2026,141.250000\n05/20/2026,143.750000\n",
        )
    )
    runtime = build_runtime()

    observation = runtime.gateway.fetch_latest("cboe:SKEW")

    assert observation.observed_at == "2026-05-20"
    assert observation.value == LATEST_SKEW_VALUE


@respx.mock
def test_cboe_provider_rejects_malformed_history_csv() -> None:
    respx.get(VVIX_URL).mock(return_value=Response(200, text="DATE,VVIX\n05/20/2026,not-a-number\n"))
    runtime = build_runtime()

    with pytest.raises(Exception, match="not numeric"):
        runtime.gateway.fetch_series("cboe:VVIX", start="2026-05-20", end="2026-05-20")
