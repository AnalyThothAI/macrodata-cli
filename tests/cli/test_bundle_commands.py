from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
import respx
from httpx import Request, Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
SOFR_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"
RRP_URL = "https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json"
SRF_URL = "https://markets.newyorkfed.org/api/rp/results/search.json"
OPERATING_CASH_BALANCE_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
)
TREASURY_AUCTION_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
)
CFTC_URL = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BEA_RELEASE_DATES_URL = "https://apps.bea.gov/API/signup/release_dates.json"
TGA_CLOSING_BALANCE_ACCOUNT_TYPE = "Treasury General Account (TGA) Closing Balance"
EXPECTED_RATES_REQUESTED = 9
EXPECTED_LIQUIDITY_REQUESTED = 7
EXPECTED_MACRO_CALENDAR_REQUESTED = 3
EXPECTED_TREASURY_AUCTION_REQUESTED = 9
EXPECTED_MIN_MACRO_REQUESTED = 20
VALIDATION_EXIT_CODE = 2
YAHOO_CLOSE = 604.25


def mock_fred() -> None:
    respx.get(FRED_URL).mock(
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


def mock_fred_public_csv() -> None:
    def respond(request: Request) -> Response:
        dataset = request.url.params["id"]
        return Response(200, text=f"observation_date,{dataset}\n2026-05-20,4.57\n")

    respx.get(FRED_CSV_URL).mock(side_effect=respond)


def mock_fred_public_csv_http_error() -> None:
    respx.get(FRED_CSV_URL).mock(return_value=Response(503, text="temporarily unavailable"))


def mock_nyfed() -> None:
    respx.get(SOFR_URL).mock(
        return_value=Response(
            200,
            json={"refRates": [{"effectiveDate": "2026-05-20", "percentRate": "4.31"}]},
        )
    )
    respx.get(RRP_URL).mock(
        return_value=Response(
            200,
            json={
                "repo": {
                    "operations": [
                        {
                            "operationId": "RP 052026 27",
                            "operationDate": "2026-05-20",
                            "operationType": "Reverse Repo",
                            "totalAmtAccepted": 24867000000,
                        }
                    ]
                }
            },
        )
    )
    respx.get(SRF_URL).mock(
        return_value=Response(
            200,
            json={
                "repo": {
                    "operations": [
                        {
                            "operationId": "RP 052026 28",
                            "operationDate": "2026-05-20",
                            "operationType": "Repo",
                            "totalAmtAccepted": 4000000,
                        }
                    ]
                }
            },
        )
    )


def mock_nyfed_http_error() -> None:
    respx.get(SOFR_URL).mock(return_value=Response(503, json={"error": "temporarily unavailable"}))


def mock_treasury_fiscal() -> None:
    respx.get(OPERATING_CASH_BALANCE_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-20",
                        "account_type": TGA_CLOSING_BALANCE_ACCOUNT_TYPE,
                        "open_today_bal": "822275",
                        "close_today_bal": "null",
                    }
                ]
            },
        )
    )


def mock_treasury_auction() -> None:
    def respond(request: Request) -> Response:
        params = request.url.params
        term = str(params.get("filter", "")).split("security_term:eq:", 1)[1]
        security_type = "Bond" if term == "30-Year" else "Note"
        return Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-15",
                        "cusip": "91282CQQ7",
                        "security_type": security_type,
                        "security_term": term,
                        "auction_date": "2026-05-12",
                        "issue_date": "2026-05-15",
                        "maturity_date": "2036-05-15",
                        "high_yield": "4.4680",
                        "bid_to_cover_ratio": "2.400000",
                        "indirect_bidder_accepted": "26775518000",
                        "total_accepted": "51972791100",
                        "total_tendered": "110863591100",
                        "offering_amt": "42000000000",
                    }
                ]
            },
        )

    respx.get(TREASURY_AUCTION_URL).mock(side_effect=respond)


def mock_official_calendar() -> None:
    respx.get(FOMC_CALENDAR_URL).mock(
        return_value=Response(
            200,
            text="""
            <html><body>
            <h4>2026 FOMC Meetings</h4>
            <p>June</p><p>16-17*</p>
            <p>July</p><p>28-29</p>
            <p>* Meeting associated with a Summary of Economic Projections.</p>
            </body></html>
            """,
        )
    )
    respx.get(BEA_RELEASE_DATES_URL).mock(
        return_value=Response(
            200,
            json={
                "Gross Domestic Product": {"release_dates": ["2026-06-25T12:30:00+00:00"]},
                "Personal Income and Outlays": {"release_dates": ["2026-06-25T12:30:00+00:00"]},
            },
        )
    )


class FakeYahooTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, **kwargs: Any) -> FakeYahooHistory:
        return FakeYahooHistory([(date(2026, 5, 20), {"Close": YAHOO_CLOSE})])


class FakeYahooHistory:
    def __init__(self, rows: list[tuple[date, dict[str, float]]]) -> None:
        self._rows = rows
        self.empty = not rows

    def iterrows(self) -> list[tuple[date, dict[str, float]]]:
        return self._rows


def mock_yahoo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("macrodata.providers.yahoo.yf.Ticker", FakeYahooTicker)


def mock_cftc() -> None:
    respx.get(CFTC_URL).mock(
        return_value=Response(
            200,
            text=(
                "Report_Date_as_YYYY-MM-DD,Market_and_Exchange_Names,"
                "NonComm_Positions_Long_All,NonComm_Positions_Short_All\n"
                "2026-05-19,S&P 500 Consolidated - CHICAGO MERCANTILE EXCHANGE,2500,1250\n"
            ),
        )
    )


@respx.mock
def test_rates_core_bundle_command() -> None:
    mock_fred()
    mock_nyfed()

    result = CliRunner().invoke(
        app,
        ["bundle", "rates-core", "--asof", "2026-05-21", "--fred-api-key", "test-key"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["bundle"] == "rates-core"
    assert snapshot["coverage"] == {"requested": EXPECTED_RATES_REQUESTED, "available": EXPECTED_RATES_REQUESTED}
    assert snapshot["source_chain"] == ["fred", "nyfed"]
    assert snapshot["observations"][0]["idempotency_key"] == "fred:DGS2:2026-05-20"
    assert "test-key" not in result.stdout


@respx.mock
def test_liquidity_core_bundle_command() -> None:
    mock_fred()
    mock_nyfed()
    mock_treasury_fiscal()

    result = CliRunner().invoke(
        app,
        ["bundle", "liquidity-core", "--asof", "2026-05-21", "--fred-api-key", "test-key"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["bundle"] == "liquidity-core"
    assert snapshot["coverage"] == {
        "requested": EXPECTED_LIQUIDITY_REQUESTED,
        "available": EXPECTED_LIQUIDITY_REQUESTED,
    }
    assert snapshot["source_chain"] == ["fred", "nyfed", "treasury_fiscal"]
    assert snapshot["missing_series"] == []
    assert snapshot["data_quality"] == "ok"


@respx.mock
def test_macro_core_bundle_command(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_fred()
    mock_nyfed()
    mock_treasury_fiscal()
    mock_yahoo(monkeypatch)
    mock_cftc()

    result = CliRunner().invoke(
        app,
        ["bundle", "macro-core", "--asof", "2026-05-21", "--fred-api-key", "test-key"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["bundle"] == "macro-core"
    assert snapshot["coverage"]["requested"] >= EXPECTED_MIN_MACRO_REQUESTED
    assert "yahoo" in snapshot["source_chain"]
    assert "stooq" not in snapshot["source_chain"]
    assert "series_errors" in snapshot
    assert "test-key" not in result.stdout


@respx.mock
def test_macro_calendar_core_bundle_fetch_uses_official_sources() -> None:
    mock_official_calendar()

    result = CliRunner().invoke(
        app,
        ["bundle", "fetch", "macro-calendar-core", "--asof", "2026-06-16"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["bundle"] == "macro-calendar-core"
    assert snapshot["coverage"] == {
        "requested": EXPECTED_MACRO_CALENDAR_REQUESTED,
        "available": EXPECTED_MACRO_CALENDAR_REQUESTED,
    }
    assert snapshot["source_chain"] == ["official_calendar"]
    assert snapshot["missing_series"] == []
    assert snapshot["data_quality"] == "ok"
    assert snapshot["observations"][0]["series_key"] == "official_calendar:fomc_decision_next"
    assert snapshot["observations"][0]["observed_at"] == "2026-06-17"
    assert snapshot["observations"][0]["provenance"][0]["event_time_et"] == "2:00 PM"
    assert {item["series_key"] for item in snapshot["observations"]} == {
        "official_calendar:fomc_decision_next",
        "official_calendar:bea_gdp_next",
        "official_calendar:bea_pce_next",
    }


@respx.mock
def test_treasury_auction_core_bundle_fetch_uses_official_fiscaldata() -> None:
    mock_treasury_auction()

    result = CliRunner().invoke(
        app,
        ["bundle", "fetch", "treasury-auction-core", "--asof", "2026-06-16"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["bundle"] == "treasury-auction-core"
    assert snapshot["coverage"] == {
        "requested": EXPECTED_TREASURY_AUCTION_REQUESTED,
        "available": EXPECTED_TREASURY_AUCTION_REQUESTED,
    }
    assert snapshot["source_chain"] == ["treasury_auction"]
    assert snapshot["missing_series"] == []
    assert snapshot["data_quality"] == "ok"
    assert {item["series_key"] for item in snapshot["observations"]} == {
        "treasury_auction:2y_high_yield",
        "treasury_auction:2y_bid_to_cover",
        "treasury_auction:2y_indirect_bidder_pct",
        "treasury_auction:10y_high_yield",
        "treasury_auction:10y_bid_to_cover",
        "treasury_auction:10y_indirect_bidder_pct",
        "treasury_auction:30y_high_yield",
        "treasury_auction:30y_bid_to_cover",
        "treasury_auction:30y_indirect_bidder_pct",
    }


@respx.mock
def test_macro_core_bundle_history_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    mock_fred_public_csv()
    mock_nyfed()
    mock_treasury_fiscal()
    mock_yahoo(monkeypatch)
    mock_cftc()

    result = CliRunner().invoke(
        app,
        ["bundle", "history", "macro-core", "--start", "2026-05-01", "--end", "2026-05-21"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["bundle"] == "macro-core"
    assert isinstance(snapshot["observations"], list)
    assert snapshot["coverage"]["requested"] >= EXPECTED_MIN_MACRO_REQUESTED
    assert snapshot["coverage"]["available"] == snapshot["coverage"]["requested"]
    assert "yahoo" in snapshot["source_chain"]
    assert "stooq" not in snapshot["source_chain"]
    assert "coverage" in snapshot
    assert "missing_series" in snapshot
    assert "series_errors" in snapshot
    assert snapshot["reason_codes"] == []


@respx.mock
def test_event_bundle_history_commands_are_first_class_sync_surfaces() -> None:
    mock_official_calendar()
    mock_treasury_auction()

    calendar_result = CliRunner().invoke(
        app,
        ["bundle", "history", "macro-calendar-core", "--start", "2026-06-16", "--end", "2026-07-31"],
    )
    auction_result = CliRunner().invoke(
        app,
        ["bundle", "history", "treasury-auction-core", "--start", "2026-06-01", "--end", "2026-06-30"],
    )

    assert calendar_result.exit_code == 0
    calendar_snapshot = json.loads(calendar_result.stdout)["data"]["snapshot"]
    assert calendar_snapshot["bundle"] == "macro-calendar-core"
    assert calendar_snapshot["coverage"] == {
        "requested": EXPECTED_MACRO_CALENDAR_REQUESTED,
        "available": EXPECTED_MACRO_CALENDAR_REQUESTED,
    }
    assert {item["series_key"] for item in calendar_snapshot["observations"]} == {
        "official_calendar:fomc_decision_next",
        "official_calendar:bea_gdp_next",
        "official_calendar:bea_pce_next",
    }

    assert auction_result.exit_code == 0
    auction_snapshot = json.loads(auction_result.stdout)["data"]["snapshot"]
    assert auction_snapshot["bundle"] == "treasury-auction-core"
    assert auction_snapshot["coverage"] == {
        "requested": EXPECTED_TREASURY_AUCTION_REQUESTED,
        "available": EXPECTED_TREASURY_AUCTION_REQUESTED,
    }
    assert {item["series_key"] for item in auction_snapshot["observations"]} == {
        "treasury_auction:2y_high_yield",
        "treasury_auction:2y_bid_to_cover",
        "treasury_auction:2y_indirect_bidder_pct",
        "treasury_auction:10y_high_yield",
        "treasury_auction:10y_bid_to_cover",
        "treasury_auction:10y_indirect_bidder_pct",
        "treasury_auction:30y_high_yield",
        "treasury_auction:30y_bid_to_cover",
        "treasury_auction:30y_indirect_bidder_pct",
    }


@respx.mock
def test_rates_core_without_fred_api_key_uses_public_csv(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    mock_fred_public_csv()
    mock_nyfed()

    result = CliRunner().invoke(app, ["bundle", "rates-core", "--asof", "2026-05-21"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["data_quality"] == "ok"
    assert snapshot["coverage"] == {
        "requested": EXPECTED_RATES_REQUESTED,
        "available": EXPECTED_RATES_REQUESTED,
    }
    assert snapshot["missing_series"] == []
    assert snapshot["reason_codes"] == []
    assert snapshot["series_errors"] == []
    assert snapshot["source_health"][0] == {
        "provider": "fred",
        "requested": EXPECTED_RATES_REQUESTED - 1,
        "available": EXPECTED_RATES_REQUESTED - 1,
        "missing": 0,
        "status": "ok",
        "access_mode": "public_csv",
        "error_codes": [],
        "retryable": False,
    }
    assert "test-key" not in result.stdout
    assert "secret" not in result.stdout


@respx.mock
def test_rates_core_all_series_failing_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    mock_fred_public_csv_http_error()
    mock_nyfed_http_error()

    result = CliRunner().invoke(app, ["bundle", "rates-core", "--asof", "2026-05-21"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["data_quality"] == "unavailable"
    assert snapshot["coverage"] == {"requested": EXPECTED_RATES_REQUESTED, "available": 0}
    assert snapshot["observations"] == []
    assert "missing_series" in snapshot["reason_codes"]
    assert "provider_http_error" in snapshot["reason_codes"]
    assert "all_series_missing" in snapshot["reason_codes"]
    assert len(snapshot["series_errors"]) == EXPECTED_RATES_REQUESTED
    assert snapshot["series_errors"][-1]["series_key"] == "nyfed:SOFR"
    assert snapshot["series_errors"][-1]["provider"] == "nyfed"
    assert snapshot["series_errors"][-1]["code"] == "provider_http_error"
    assert snapshot["series_errors"][-1]["retryable"] is True
    assert snapshot["source_health"][0] == {
        "provider": "fred",
        "requested": EXPECTED_RATES_REQUESTED - 1,
        "available": 0,
        "missing": EXPECTED_RATES_REQUESTED - 1,
        "status": "unavailable",
        "access_mode": "public_csv",
        "error_codes": ["provider_http_error"],
        "retryable": True,
    }


def test_unknown_bundle_returns_structured_error_from_service() -> None:
    result = CliRunner().invoke(app, ["bundle", "fetch", "unknown-core", "--asof", "2026-05-21"])

    assert result.exit_code == VALIDATION_EXIT_CODE
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unknown_bundle"
