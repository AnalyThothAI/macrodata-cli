from __future__ import annotations

from typing import cast

import pytest

from macrodata.app.services import LIQUIDITY_CORE, RATES_CORE, MacrodataService
from macrodata.core.errors import MacrodataError
from macrodata.core.models import BundleSnapshot, MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway

EXPECTED_SINGLE_REQUESTED = 1
EXPECTED_SINGLE_AVAILABLE = 1
EXPECTED_RATES_CORE_SIZE = 9
EXPECTED_LIQUIDITY_CORE_SIZE = 5
EXPECTED_FRED_RATE_FAILURES = 8
VALIDATION_EXIT_CODE = 2


def make_observation(series_key: str) -> MacroObservation:
    provider, dataset = series_key.split(":", 1)
    return MacroObservation(
        series_key=series_key,
        provider=provider,
        dataset=dataset,
        observed_at="2026-05-20",
        value=1.0,
        unit=None,
        frequency=None,
        source_ts="2026-05-20",
        realtime_start=None,
        realtime_end=None,
        latency_class="eod",
        data_quality="ok",
        provenance=[],
    )


class FakeGateway:
    def __init__(
        self,
        *,
        failed_series: set[str] | None = None,
        series_errors: dict[str, MacrodataError] | None = None,
    ) -> None:
        self.failed_series = failed_series or set()
        self.series_errors = series_errors or {}
        self.requested: list[str] = []

    def fetch_latest(self, series_key: str) -> MacroObservation:
        self.requested.append(series_key)
        if series_key in self.series_errors:
            raise self.series_errors[series_key]
        if series_key in self.failed_series:
            raise MacrodataError(code="no_data", message=f"missing {series_key}", provider=series_key.split(":", 1)[0])
        return make_observation(series_key)


def test_bundle_snapshot_model() -> None:
    snapshot = BundleSnapshot(
        bundle="rates-core",
        asof="2026-05-21",
        observations=[make_observation("fred:DGS10")],
        coverage={"requested": EXPECTED_SINGLE_REQUESTED, "available": EXPECTED_SINGLE_AVAILABLE},
        missing_series=[],
        source_chain=["fred"],
        data_quality="ok",
        reason_codes=[],
    )

    assert snapshot.coverage["available"] == EXPECTED_SINGLE_AVAILABLE
    assert snapshot.model_dump(mode="json")["observations"][0]["idempotency_key"] == "fred:DGS10:2026-05-20"


def test_bundle_constants_include_supported_core_series() -> None:
    assert len(RATES_CORE) == EXPECTED_RATES_CORE_SIZE
    assert "nyfed:SOFR" in RATES_CORE
    assert len(LIQUIDITY_CORE) == EXPECTED_LIQUIDITY_CORE_SIZE
    assert "treasury_fiscal:operating_cash_balance" in LIQUIDITY_CORE


def test_rates_core_bundle_collects_observations_and_source_chain() -> None:
    fake_gateway = FakeGateway()
    service = MacrodataService(gateway=cast(MacrodataGateway, fake_gateway))

    snapshot = service.bundle("rates-core", asof="2026-05-21")

    assert fake_gateway.requested == RATES_CORE
    assert snapshot.bundle == "rates-core"
    assert snapshot.coverage == {"requested": EXPECTED_RATES_CORE_SIZE, "available": EXPECTED_RATES_CORE_SIZE}
    assert snapshot.missing_series == []
    assert snapshot.source_chain == ["fred", "nyfed"]
    assert snapshot.data_quality == "ok"
    assert snapshot.reason_codes == []


def test_liquidity_core_bundle_marks_missing_series_partial() -> None:
    missing_series = {"fred:RRPONTSYD", "treasury_fiscal:operating_cash_balance"}
    service = MacrodataService(gateway=cast(MacrodataGateway, FakeGateway(failed_series=missing_series)))

    snapshot = service.bundle("liquidity-core", asof="2026-05-21")

    assert snapshot.coverage == {
        "requested": EXPECTED_LIQUIDITY_CORE_SIZE,
        "available": EXPECTED_LIQUIDITY_CORE_SIZE - len(missing_series),
    }
    assert snapshot.missing_series == ["fred:RRPONTSYD", "treasury_fiscal:operating_cash_balance"]
    assert snapshot.source_chain == ["fred", "nyfed"]
    assert snapshot.data_quality == "partial"
    assert snapshot.reason_codes == ["missing_series", "no_data"]
    assert snapshot.series_errors == [
        {
            "series_key": "fred:RRPONTSYD",
            "provider": "fred",
            "code": "no_data",
            "retryable": False,
            "message": "missing fred:RRPONTSYD",
        },
        {
            "series_key": "treasury_fiscal:operating_cash_balance",
            "provider": "treasury_fiscal",
            "code": "no_data",
            "retryable": False,
            "message": "missing treasury_fiscal:operating_cash_balance",
        },
    ]


def test_rates_core_bundle_exposes_missing_api_key_diagnostics() -> None:
    fred_errors = {
        series_key: MacrodataError(
            code="missing_api_key",
            message="FRED_API_KEY is required",
            provider="fred",
            retryable=False,
            exit_code=2,
        )
        for series_key in RATES_CORE
        if series_key.startswith("fred:")
    }
    service = MacrodataService(gateway=cast(MacrodataGateway, FakeGateway(series_errors=fred_errors)))

    snapshot = service.bundle("rates-core", asof="2026-05-21")

    assert snapshot.data_quality == "partial"
    assert snapshot.coverage == {
        "requested": EXPECTED_RATES_CORE_SIZE,
        "available": EXPECTED_RATES_CORE_SIZE - EXPECTED_FRED_RATE_FAILURES,
    }
    assert "missing_series" in snapshot.reason_codes
    assert "missing_api_key" in snapshot.reason_codes
    assert "all_series_missing" not in snapshot.reason_codes
    assert len(snapshot.series_errors) == EXPECTED_FRED_RATE_FAILURES
    assert snapshot.series_errors[0] == {
        "series_key": "fred:DGS2",
        "provider": "fred",
        "code": "missing_api_key",
        "retryable": False,
        "message": "FRED_API_KEY is required",
    }


def test_rates_core_bundle_marks_all_series_missing_unavailable() -> None:
    series_errors = {
        series_key: MacrodataError(
            code="provider_timeout",
            message=f"{series_key} timed out",
            provider=series_key.split(":", 1)[0],
            retryable=True,
        )
        for series_key in RATES_CORE
    }
    service = MacrodataService(gateway=cast(MacrodataGateway, FakeGateway(series_errors=series_errors)))

    snapshot = service.bundle("rates-core", asof="2026-05-21")

    assert snapshot.coverage == {"requested": EXPECTED_RATES_CORE_SIZE, "available": 0}
    assert snapshot.missing_series == RATES_CORE
    assert snapshot.observations == []
    assert snapshot.data_quality == "unavailable"
    assert snapshot.reason_codes == ["missing_series", "provider_timeout", "all_series_missing"]
    assert len(snapshot.series_errors) == EXPECTED_RATES_CORE_SIZE


def test_unknown_bundle_raises_structured_validation_error() -> None:
    service = MacrodataService(gateway=cast(MacrodataGateway, FakeGateway()))

    with pytest.raises(MacrodataError) as raised:
        service.bundle("unknown-core", asof="2026-05-21")

    assert raised.value.code == "unknown_bundle"
    assert raised.value.exit_code == VALIDATION_EXIT_CODE
