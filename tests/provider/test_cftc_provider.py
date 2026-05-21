from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.cftc import CftcProvider

CFTC_URL = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
SUPPORTED_DATASET = "financial_futures:sp500_net_noncommercial"
EXPECTED_NET_CONTRACTS = 1250.0
EXPECTED_HEADERLESS_NET_CONTRACTS = -736034.0


@respx.mock
def test_cftc_financial_futures_parses_sp500_net_noncommercial() -> None:
    route = respx.get(CFTC_URL).mock(
        return_value=Response(
            200,
            text=(
                "Report_Date_as_YYYY-MM-DD,Market_and_Exchange_Names,"
                "NonComm_Positions_Long_All,NonComm_Positions_Short_All\n"
                "2026-05-19,S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE,2500,1250\n"
            ),
        )
    )
    provider = CftcProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range(SUPPORTED_DATASET, start="2026-05-01", end="2026-05-31")

    assert route.called
    assert observations[0].series_key == "cftc:financial_futures:sp500_net_noncommercial"
    assert observations[0].provider == "cftc"
    assert observations[0].dataset == SUPPORTED_DATASET
    assert observations[0].observed_at == "2026-05-19"
    assert observations[0].value == EXPECTED_NET_CONTRACTS
    assert observations[0].unit == "contracts"
    assert observations[0].frequency == "weekly"
    assert observations[0].latency_class == "weekly"
    assert observations[0].data_quality == "ok"
    assert observations[0].provenance == [{"provider": "cftc", "source_url": CFTC_URL}]


@respx.mock
def test_cftc_financial_futures_parses_live_headerless_layout() -> None:
    respx.get(CFTC_URL).mock(
        return_value=Response(
            200,
            text=(
                '"S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE",260512,2026-05-12,13874+,CME ,00,138 ,'
                " 2078428,  138126,  874160,   55876, 1242976,  184926,   98129,  148141,  577496,"
                '   62219,   64306,   46709,     660,"(S&P 500 INDEX X $50.00)","13874+","CME ",'
                '"138 ","F20","FutOnly"\n'
            ),
        )
    )
    provider = CftcProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range(SUPPORTED_DATASET, start="2026-05-01", end="2026-05-31")

    assert observations[0].observed_at == "2026-05-12"
    assert observations[0].value == EXPECTED_HEADERLESS_NET_CONTRACTS


@respx.mock
def test_cftc_headerless_layout_selects_exact_consolidated_contract_per_report_date() -> None:
    respx.get(CFTC_URL).mock(
        return_value=Response(
            200,
            text=(
                '"S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE",260512,2026-05-12,13874+,CME ,00,138 ,'
                " 2078428,  138126,  874160,   55876, 1242976,  184926,   98129,  148141,  577496,"
                '   62219,   64306,   46709,     660,"(S&P 500 INDEX X $50.00)","13874+","CME ",'
                '"138 ","F20","FutOnly"\n'
                '"E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",260512,2026-05-12,13874A,CME ,00,138 ,'
                " 2056229,  137266,  873539,   55767, 1239798,  184926,   97750,  148507,  580945,"
                '   51162,   64306,   46490,     654,"($50 X S&P 500 INDEX)","13874A","CME ",'
                '"138 ","F20","FutOnly"\n'
                '"MICRO E-MINI S&P 500 INDEX - CHICAGO MERCANTILE EXCHANGE",260512,2026-05-12,13874U,'
                "CME ,00,138 ,  221994,    9690,    7305,       0,   31999,     219,    3566,"
                '   99863,   69032,"($5 X S&P 500 INDEX)","13874U","CME ","138 ","F20","FutOnly"\n'
            ),
        )
    )
    provider = CftcProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range(SUPPORTED_DATASET, start="2026-05-01", end="2026-05-31")

    assert len(observations) == 1
    assert observations[0].observed_at == "2026-05-12"
    assert observations[0].value == EXPECTED_HEADERLESS_NET_CONTRACTS


@respx.mock
def test_cftc_skips_unrelated_financial_futures_markets() -> None:
    respx.get(CFTC_URL).mock(
        return_value=Response(
            200,
            text=(
                "Report_Date_as_YYYY-MM-DD,Market_and_Exchange_Names,"
                "NonComm_Positions_Long_All,NonComm_Positions_Short_All\n"
                "2026-05-19,AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE,10,9\n"
                "2026-05-19,S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE,2500,1250\n"
            ),
        )
    )
    provider = CftcProvider(http_client=MacrodataHttpClient())

    observations = provider.get_latest(SUPPORTED_DATASET)

    assert observations.observed_at == "2026-05-19"
    assert observations.value == EXPECTED_NET_CONTRACTS


@respx.mock
def test_cftc_missing_response_raises_provider_unavailable() -> None:
    respx.get(CFTC_URL).mock(return_value=Response(503, text="unavailable"))
    provider = CftcProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_latest(SUPPORTED_DATASET)

    assert raised.value.code == "provider_unavailable"
    assert raised.value.provider == "cftc"
    assert raised.value.retryable is True


@respx.mock
def test_cftc_unparseable_response_raises_parse_error() -> None:
    respx.get(CFTC_URL).mock(return_value=Response(200, text="not,a,known,schema\n1,2,3,4\n"))
    provider = CftcProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_latest(SUPPORTED_DATASET)

    assert raised.value.code == "provider_parse_error"
    assert raised.value.provider == "cftc"
    assert raised.value.retryable is False
