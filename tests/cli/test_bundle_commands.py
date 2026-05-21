from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
SOFR_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"
OPERATING_CASH_BALANCE_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
)
TGA_CLOSING_BALANCE_ACCOUNT_TYPE = "Treasury General Account (TGA) Closing Balance"
EXPECTED_RATES_REQUESTED = 9
EXPECTED_LIQUIDITY_REQUESTED = 5
EXPECTED_FRED_RATE_FAILURES = 8
VALIDATION_EXIT_CODE = 2


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


def mock_nyfed() -> None:
    respx.get(SOFR_URL).mock(
        return_value=Response(
            200,
            json={"refRates": [{"effectiveDate": "2026-05-20", "percentRate": "4.31"}]},
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
def test_rates_core_without_fred_api_key_exposes_missing_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    mock_nyfed()

    result = CliRunner().invoke(app, ["bundle", "rates-core", "--asof", "2026-05-21"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    snapshot = payload["data"]["snapshot"]
    assert payload["ok"] is True
    assert snapshot["data_quality"] == "partial"
    assert snapshot["coverage"] == {
        "requested": EXPECTED_RATES_REQUESTED,
        "available": EXPECTED_RATES_REQUESTED - EXPECTED_FRED_RATE_FAILURES,
    }
    assert "missing_series" in snapshot["reason_codes"]
    assert "missing_api_key" in snapshot["reason_codes"]
    assert "all_series_missing" not in snapshot["reason_codes"]
    assert len(snapshot["series_errors"]) == EXPECTED_FRED_RATE_FAILURES
    assert snapshot["series_errors"][0]["series_key"] == "fred:DGS2"
    assert snapshot["series_errors"][0]["code"] == "missing_api_key"
    assert snapshot["series_errors"][0]["provider"] == "fred"
    assert snapshot["series_errors"][0]["retryable"] is False
    assert "test-key" not in result.stdout
    assert "secret" not in result.stdout


@respx.mock
def test_rates_core_all_series_failing_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
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
    assert "missing_api_key" in snapshot["reason_codes"]
    assert "provider_http_error" in snapshot["reason_codes"]
    assert "all_series_missing" in snapshot["reason_codes"]
    assert len(snapshot["series_errors"]) == EXPECTED_RATES_REQUESTED
    assert snapshot["series_errors"][-1]["series_key"] == "nyfed:SOFR"
    assert snapshot["series_errors"][-1]["provider"] == "nyfed"
    assert snapshot["series_errors"][-1]["code"] == "provider_http_error"
    assert snapshot["series_errors"][-1]["retryable"] is True


def test_unknown_bundle_returns_structured_error_from_service() -> None:
    result = CliRunner().invoke(app, ["bundle", "fetch", "unknown-core", "--asof", "2026-05-21"])

    assert result.exit_code == VALIDATION_EXIT_CODE
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unknown_bundle"
