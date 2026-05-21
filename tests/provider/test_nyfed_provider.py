from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.app.runtime import build_runtime
from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.nyfed import NyFedMarketsProvider

SOFR_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"
EXPECTED_SOFR = 4.31
UNKNOWN_SERIES_EXIT_CODE = 2


@respx.mock
def test_nyfed_sofr_parses_latest_rate() -> None:
    route = respx.get(SOFR_URL).mock(
        return_value=Response(
            200,
            json={
                "refRates": [
                    {
                        "effectiveDate": "2026-05-20",
                        "percentRate": "4.31",
                    }
                ]
            },
        )
    )
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("SOFR", start="2026-05-20", end="2026-05-20")

    assert route.called
    assert observations[0].series_key == "nyfed:SOFR"
    assert observations[0].provider == "nyfed"
    assert observations[0].dataset == "SOFR"
    assert observations[0].observed_at == "2026-05-20"
    assert observations[0].value == EXPECTED_SOFR
    assert observations[0].source_ts == "2026-05-20"
    assert observations[0].unit == "percent"
    assert observations[0].frequency == "daily"
    assert observations[0].latency_class == "daily"
    assert observations[0].data_quality == "ok"
    assert observations[0].provenance == [{"provider": "nyfed", "source_url": SOFR_URL}]


@respx.mock
def test_nyfed_latest_returns_last_rate() -> None:
    respx.get(SOFR_URL).mock(
        return_value=Response(
            200,
            json={
                "refRates": [
                    {"effectiveDate": "2026-05-19", "percentRate": "4.30"},
                    {"effectiveDate": "2026-05-20", "percentRate": "4.31"},
                ]
            },
        )
    )
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    observation = provider.get_latest("SOFR")

    assert observation.observed_at == "2026-05-20"
    assert observation.value == EXPECTED_SOFR


@respx.mock
def test_nyfed_sorts_newest_first_rows_before_latest_selection() -> None:
    respx.get(SOFR_URL).mock(
        return_value=Response(
            200,
            json={
                "refRates": [
                    {"effectiveDate": "2026-05-20", "percentRate": "4.31"},
                    {"effectiveDate": "2026-05-19", "percentRate": "4.30"},
                ]
            },
        )
    )
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("SOFR", start="2026-05-19", end="2026-05-20")
    latest = provider.get_latest("SOFR")

    assert [observation.observed_at for observation in observations] == ["2026-05-19", "2026-05-20"]
    assert latest.observed_at == "2026-05-20"


@respx.mock
def test_nyfed_smoke_returns_ok_result() -> None:
    respx.get(SOFR_URL).mock(
        return_value=Response(
            200,
            json={"refRates": [{"effectiveDate": "2026-05-20", "percentRate": "4.31"}]},
        )
    )
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    result = provider.smoke()

    assert result.provider == "nyfed"
    assert result.ok is True
    assert result.sample_dataset == "SOFR"
    assert result.sample_source_ts == "2026-05-20"


def test_nyfed_rejects_unsupported_dataset_structured() -> None:
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("RRP", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "unknown_series"
    assert raised.value.provider == "nyfed"
    assert raised.value.exit_code == UNKNOWN_SERIES_EXIT_CODE
    assert "RRP" in raised.value.message


@respx.mock
def test_nyfed_rejects_non_list_ref_rates() -> None:
    respx.get(SOFR_URL).mock(return_value=Response(200, json={"refRates": {"bad": "shape"}}))
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("SOFR", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.provider == "nyfed"


@respx.mock
def test_nyfed_rejects_malformed_numeric_rate() -> None:
    respx.get(SOFR_URL).mock(
        return_value=Response(200, json={"refRates": [{"effectiveDate": "2026-05-20", "percentRate": "bad"}]})
    )
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("SOFR", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "nyfed"
    assert "SOFR" in raised.value.message
    assert "2026-05-20" in raised.value.message


@pytest.mark.parametrize(
    ("row", "expected_fragment"),
    [
        ({"percentRate": "4.31"}, "missing"),
        ({"effectiveDate": "", "percentRate": "4.31"}, "missing"),
        ({"effectiveDate": "05/20/2026", "percentRate": "4.31"}, "invalid"),
    ],
)
@respx.mock
def test_nyfed_rejects_missing_blank_or_malformed_effective_date(
    row: dict[str, str], expected_fragment: str
) -> None:
    respx.get(SOFR_URL).mock(return_value=Response(200, json={"refRates": [row]}))
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("SOFR", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "nyfed"
    assert expected_fragment in raised.value.message


def test_runtime_wires_nyfed_provider() -> None:
    runtime = build_runtime()

    provider = runtime.gateway.provider("nyfed")

    assert isinstance(provider, NyFedMarketsProvider)
