from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.stooq import StooqProvider

STOOQ_URL = "https://stooq.com/q/d/l/"
STOOQ_QUOTE_URL = "https://stooq.com/q/l/"
EXPECTED_CLOSE = 604.25
NO_DATA_EXIT_CODE = 4


@respx.mock
def test_stooq_range_parses_daily_csv_close_and_request_params() -> None:
    route = respx.get(STOOQ_URL).mock(
        return_value=Response(
            200,
            text="Date,Open,High,Low,Close,Volume\n2026-05-20,600.0,605.0,598.0,604.25,1000\n",
        )
    )
    provider = StooqProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("spy.us", start="2026-05-20", end="2026-05-20")

    assert route.called
    request = route.calls.last.request
    assert request.url.params["s"] == "spy.us"
    assert request.url.params["i"] == "d"
    assert request.url.params["d1"] == "20260520"
    assert request.url.params["d2"] == "20260520"
    assert observations[0].series_key == "stooq:spy.us"
    assert observations[0].provider == "stooq"
    assert observations[0].dataset == "spy.us"
    assert observations[0].observed_at == "2026-05-20"
    assert observations[0].value == EXPECTED_CLOSE
    assert observations[0].unit == "price"
    assert observations[0].frequency == "daily"
    assert observations[0].source_ts == "2026-05-20"
    assert observations[0].latency_class == "daily"
    assert observations[0].data_quality == "ok"
    assert observations[0].provenance == [{"provider": "stooq", "source_url": STOOQ_URL}]


@respx.mock
def test_stooq_latest_raises_no_data_for_empty_csv() -> None:
    respx.get(STOOQ_QUOTE_URL).mock(return_value=Response(200, text="Symbol,Date,Time,Open,High,Low,Close,Volume\n"))
    provider = StooqProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_latest("spy.us")

    assert raised.value.code == "no_data"
    assert raised.value.provider == "stooq"
    assert raised.value.exit_code == NO_DATA_EXIT_CODE


@respx.mock
def test_stooq_latest_uses_quote_csv_endpoint() -> None:
    route = respx.get(STOOQ_QUOTE_URL).mock(
        return_value=Response(
            200,
            text=(
                "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
                "SPY.US,2026-05-20,22:00:25,600.0,605.0,598.0,604.25,1000\n"
            ),
        )
    )
    provider = StooqProvider(http_client=MacrodataHttpClient())

    observation = provider.get_latest("spy.us")

    assert route.called
    request = route.calls.last.request
    assert request.url.params["s"] == "spy.us"
    assert request.url.params["f"] == "sd2t2ohlcv"
    assert request.url.params["e"] == "csv"
    assert observation.series_key == "stooq:spy.us"
    assert observation.observed_at == "2026-05-20"
    assert observation.value == EXPECTED_CLOSE
    assert observation.source_ts == "2026-05-20T22:00:25"
    assert observation.provenance == [{"provider": "stooq", "source_url": STOOQ_QUOTE_URL}]


@respx.mock
def test_stooq_detects_api_key_instruction_response() -> None:
    respx.get(STOOQ_URL).mock(
        return_value=Response(
            200,
            text=(
                "<html><body>Access to this data requires an API key. "
                "Please visit Stooq for instructions.</body></html>"
            ),
        )
    )
    provider = StooqProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("spy.us", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "missing_api_key"
    assert raised.value.provider == "stooq"
    assert raised.value.retryable is False
    assert "API key" in raised.value.message


@respx.mock
def test_stooq_rejects_malformed_close_as_parse_error() -> None:
    respx.get(STOOQ_URL).mock(
        return_value=Response(200, text="Date,Open,High,Low,Close,Volume\n2026-05-20,600,605,598,bad,1000\n")
    )
    provider = StooqProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("spy.us", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.provider == "stooq"
    assert raised.value.retryable is False
