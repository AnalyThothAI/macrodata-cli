from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.app.runtime import build_runtime
from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.treasury_fiscal import TreasuryFiscalProvider

OPERATING_CASH_BALANCE_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
)
EXPECTED_BALANCE = 812345.0
EXPECTED_LATEST_BALANCE = 2.0
UNKNOWN_SERIES_EXIT_CODE = 2


@respx.mock
def test_treasury_operating_cash_balance_parses_data_and_request_params() -> None:
    route = respx.get(OPERATING_CASH_BALANCE_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-20",
                        "account_type": "Treasury General Account (TGA)",
                        "close_today_bal": "812345",
                    }
                ]
            },
        )
    )
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("operating_cash_balance", start="2026-05-20", end="2026-05-20")

    assert route.called
    request = route.calls.last.request
    assert request.url.params["filter"] == "record_date:gte:2026-05-20,record_date:lte:2026-05-20"
    assert request.url.params["sort"] == "record_date"
    assert request.url.params["page[size]"] == "10000"
    assert observations[0].series_key == "treasury_fiscal:operating_cash_balance"
    assert observations[0].provider == "treasury_fiscal"
    assert observations[0].dataset == "operating_cash_balance"
    assert observations[0].observed_at == "2026-05-20"
    assert observations[0].value == EXPECTED_BALANCE
    assert observations[0].unit == "millions_usd"
    assert observations[0].frequency == "daily"
    assert observations[0].source_ts == "2026-05-20"
    assert observations[0].realtime_start is None
    assert observations[0].realtime_end is None
    assert observations[0].latency_class == "daily"
    assert observations[0].data_quality == "ok"
    assert observations[0].provenance == [{"provider": "treasury_fiscal", "source_url": OPERATING_CASH_BALANCE_URL}]


@respx.mock
def test_treasury_sorts_range_and_latest_selects_newest_observation() -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-20",
                        "account_type": "Treasury General Account (TGA)",
                        "close_today_bal": "2",
                    },
                    {
                        "record_date": "2026-05-19",
                        "account_type": "Treasury General Account (TGA)",
                        "close_today_bal": "1",
                    },
                ]
            },
        )
    )
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("operating_cash_balance", start="2026-05-19", end="2026-05-20")
    latest = provider.get_latest("operating_cash_balance")

    assert [observation.observed_at for observation in observations] == ["2026-05-19", "2026-05-20"]
    assert latest.observed_at == "2026-05-20"
    assert latest.value == EXPECTED_LATEST_BALANCE


@respx.mock
def test_treasury_smoke_returns_ok_result() -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-20",
                        "account_type": "Treasury General Account (TGA)",
                        "close_today_bal": "812345",
                    }
                ]
            },
        )
    )
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    result = provider.smoke()

    assert result.provider == "treasury_fiscal"
    assert result.ok is True
    assert result.sample_dataset == "operating_cash_balance"
    assert result.sample_source_ts == "2026-05-20"


def test_treasury_rejects_unsupported_dataset_structured() -> None:
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("bad_dataset", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "unknown_series"
    assert raised.value.provider == "treasury_fiscal"
    assert raised.value.exit_code == UNKNOWN_SERIES_EXIT_CODE
    assert "bad_dataset" in raised.value.message


@respx.mock
def test_treasury_rejects_non_list_data() -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(return_value=Response(200, json={"data": {"bad": "shape"}}))
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("operating_cash_balance", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.provider == "treasury_fiscal"


@respx.mock
def test_treasury_rejects_non_object_row() -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(return_value=Response(200, json={"data": ["bad"]}))
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("operating_cash_balance", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.provider == "treasury_fiscal"


@respx.mock
def test_treasury_rejects_malformed_numeric_balance() -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-20",
                        "account_type": "Treasury General Account (TGA)",
                        "close_today_bal": "bad",
                    }
                ]
            },
        )
    )
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("operating_cash_balance", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "treasury_fiscal"
    assert "2026-05-20" in raised.value.message


@pytest.mark.parametrize(
    ("row", "expected_fragment"),
    [
        ({"close_today_bal": "812345"}, "missing"),
        ({"record_date": "", "close_today_bal": "812345"}, "missing"),
        ({"record_date": "05/20/2026", "close_today_bal": "812345"}, "invalid"),
    ],
)
@respx.mock
def test_treasury_rejects_missing_blank_or_malformed_record_date(
    row: dict[str, str], expected_fragment: str
) -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(return_value=Response(200, json={"data": [row]}))
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("operating_cash_balance", start="2026-05-20", end="2026-05-20")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "treasury_fiscal"
    assert expected_fragment in raised.value.message


def test_runtime_wires_treasury_fiscal_provider() -> None:
    runtime = build_runtime()

    provider = runtime.gateway.provider("treasury_fiscal")

    assert isinstance(provider, TreasuryFiscalProvider)
