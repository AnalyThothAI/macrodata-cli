from __future__ import annotations

import threading
import time
from typing import cast

import pytest

from macrodata.app.services import (
    ASSETS_CORE,
    CREDIT_CORE,
    ECONOMY_CORE,
    LIQUIDITY_CORE,
    MACRO_CORE,
    RATES_CORE,
    RATES_MARKET_CORE,
    VOLATILITY_CORE,
    MacrodataService,
)
from macrodata.core.errors import MacrodataError
from macrodata.core.models import BundleSnapshot, MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway

EXPECTED_SINGLE_REQUESTED = 1
EXPECTED_SINGLE_AVAILABLE = 1
EXPECTED_RATES_CORE_SIZE = 9
EXPECTED_RATES_MARKET_CORE_SIZE = 28
EXPECTED_LIQUIDITY_CORE_SIZE = 7
EXPECTED_ECONOMY_CORE_SIZE = 20
EXPECTED_VOLATILITY_CORE_SIZE = 8
EXPECTED_CREDIT_CORE_SIZE = 17
EXPECTED_ASSETS_CORE_SIZE = 48
EXPECTED_FRED_RATE_FAILURES = 8
EXPECTED_MIN_MACRO_CORE_SIZE = 90
VALIDATION_EXIT_CODE = 2


def make_observation(series_key: str, *, observed_at: str = "2026-05-20") -> MacroObservation:
    provider, dataset = series_key.split(":", 1)
    return MacroObservation(
        series_key=series_key,
        provider=provider,
        dataset=dataset,
        observed_at=observed_at,
        value=1.0,
        unit=None,
        frequency=None,
        source_ts=observed_at,
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
        range_observations: dict[str, list[MacroObservation]] | None = None,
    ) -> None:
        self.failed_series = failed_series or set()
        self.series_errors = series_errors or {}
        self.range_observations = range_observations or {}
        self.requested: list[str] = []

    def fetch_latest(self, series_key: str) -> MacroObservation:
        self.requested.append(series_key)
        if series_key in self.series_errors:
            raise self.series_errors[series_key]
        if series_key in self.failed_series:
            raise MacrodataError(code="no_data", message=f"missing {series_key}", provider=series_key.split(":", 1)[0])
        return make_observation(series_key)

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        self.requested.append(series_key)
        if series_key in self.series_errors:
            raise self.series_errors[series_key]
        if series_key in self.failed_series:
            raise MacrodataError(code="no_data", message=f"missing {series_key}", provider=series_key.split(":", 1)[0])
        return self.range_observations.get(series_key, [make_observation(series_key)])


class DelayedRangeGateway(FakeGateway):
    def __init__(self, *, delay_seconds: float) -> None:
        super().__init__()
        self.delay_seconds = delay_seconds
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        with self._lock:
            self.requested.append(series_key)
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)
        try:
            time.sleep(self.delay_seconds)
            return [make_observation(series_key)]
        finally:
            with self._lock:
                self._in_flight -= 1


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
    assert len(RATES_MARKET_CORE) == EXPECTED_RATES_MARKET_CORE_SIZE
    assert "fred:DFF" in RATES_MARKET_CORE
    assert "fred:DGS3MO" in RATES_MARKET_CORE
    assert "fred:DGS20" in RATES_MARKET_CORE
    assert "fred:DFII5" in RATES_MARKET_CORE
    assert "fred:MICH" in RATES_MARKET_CORE
    assert "nyfed:SOFR" in RATES_MARKET_CORE
    assert "fred:SOFR30DAYAVG" in RATES_MARKET_CORE
    assert len(LIQUIDITY_CORE) == EXPECTED_LIQUIDITY_CORE_SIZE
    assert "nyfed:RRP" in LIQUIDITY_CORE
    assert "nyfed:SRF" in LIQUIDITY_CORE
    assert "treasury_fiscal:operating_cash_balance" in LIQUIDITY_CORE
    assert len(ECONOMY_CORE) == EXPECTED_ECONOMY_CORE_SIZE
    assert "fred:GDP" in ECONOMY_CORE
    assert "fred:PAYEMS" in ECONOMY_CORE
    assert "fred:ICSA" in ECONOMY_CORE
    assert "fred:PCEPI" in ECONOMY_CORE
    assert "fred:UMCSENT" in ECONOMY_CORE
    assert len(VOLATILITY_CORE) == EXPECTED_VOLATILITY_CORE_SIZE
    assert "fred:VIXCLS" in VOLATILITY_CORE
    assert "fred:VXVCLS" in VOLATILITY_CORE
    assert "fred:VXNCLS" in VOLATILITY_CORE
    assert len(CREDIT_CORE) == EXPECTED_CREDIT_CORE_SIZE
    assert "fred:BAMLC0A4CBBB" in CREDIT_CORE
    assert "fred:BAMLH0A3HYC" in CREDIT_CORE
    assert "fred:STLFSI4" in CREDIT_CORE
    assert "yahoo:JNK" in CREDIT_CORE
    assert len(ASSETS_CORE) == EXPECTED_ASSETS_CORE_SIZE
    assert "fred:NASDAQCOM" in ASSETS_CORE
    assert "fred:DEXUSEU" in ASSETS_CORE
    assert "yahoo:DIA" in ASSETS_CORE
    assert "yahoo:EEM" in ASSETS_CORE
    assert "yahoo:UUP" in ASSETS_CORE
    assert "yahoo:^GSPC" in ASSETS_CORE
    assert "yahoo:^NDX" in ASSETS_CORE
    assert "yahoo:SI=F" in ASSETS_CORE
    assert "yahoo:HG=F" in ASSETS_CORE
    assert "yahoo:USDCNY=X" in ASSETS_CORE


def test_macro_core_bundle_contains_70_point_categories() -> None:
    assert set(RATES_CORE).issubset(MACRO_CORE)
    assert set(RATES_MARKET_CORE).issubset(MACRO_CORE)
    assert set(LIQUIDITY_CORE).issubset(MACRO_CORE)
    assert set(ECONOMY_CORE).issubset(MACRO_CORE)
    assert set(VOLATILITY_CORE).issubset(MACRO_CORE)
    assert set(CREDIT_CORE).issubset(MACRO_CORE)
    assert set(ASSETS_CORE).issubset(MACRO_CORE)
    assert "fred:WALCL" in MACRO_CORE
    assert "fred:DGS10" in MACRO_CORE
    assert "fred:IORB" in MACRO_CORE
    assert "nyfed:SOFR" in MACRO_CORE
    assert "nyfed:SRF" in MACRO_CORE
    assert "fred:VIXCLS" in MACRO_CORE
    assert "fred:BAMLH0A0HYM2" in MACRO_CORE
    assert "yahoo:SPY" in MACRO_CORE
    assert "yahoo:HYG" in MACRO_CORE
    assert "yahoo:BTC-USD" in MACRO_CORE
    assert "stooq:spy.us" not in MACRO_CORE
    assert "fred:WILL5000INDFC" not in MACRO_CORE
    assert "cftc:financial_futures:sp500_net_noncommercial" in MACRO_CORE
    assert len(MACRO_CORE) == len(set(MACRO_CORE))
    assert len(MACRO_CORE) >= EXPECTED_MIN_MACRO_CORE_SIZE


@pytest.mark.parametrize(
    ("bundle_name", "expected_series", "expected_source_chain"),
    [
        ("rates-market-core", RATES_MARKET_CORE, ["fred", "nyfed"]),
        ("economy-core", ECONOMY_CORE, ["fred"]),
        ("volatility-core", VOLATILITY_CORE, ["fred", "yahoo"]),
        ("credit-core", CREDIT_CORE, ["fred", "yahoo"]),
        ("assets-core", ASSETS_CORE, ["fred", "yahoo"]),
    ],
)
def test_focused_macro_terminal_bundles_collect_observations(
    bundle_name: str,
    expected_series: list[str],
    expected_source_chain: list[str],
) -> None:
    fake_gateway = FakeGateway()
    service = MacrodataService(gateway=cast(MacrodataGateway, fake_gateway))

    snapshot = service.bundle(bundle_name, asof="2026-05-21")

    assert fake_gateway.requested == expected_series
    assert snapshot.bundle == bundle_name
    assert snapshot.coverage == {"requested": len(expected_series), "available": len(expected_series)}
    assert snapshot.source_chain == expected_source_chain
    assert snapshot.data_quality == "ok"


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


def test_macro_core_bundle_collects_contract_series_without_real_providers() -> None:
    fake_gateway = FakeGateway()
    service = MacrodataService(gateway=cast(MacrodataGateway, fake_gateway))

    snapshot = service.bundle("macro-core", asof="2026-05-21")

    assert fake_gateway.requested == MACRO_CORE
    assert snapshot.bundle == "macro-core"
    assert snapshot.coverage == {"requested": len(MACRO_CORE), "available": len(MACRO_CORE)}
    assert snapshot.missing_series == []
    assert snapshot.source_chain == ["fred", "nyfed", "treasury_fiscal", "yahoo", "cftc"]
    assert "stooq" not in snapshot.source_chain
    assert snapshot.data_quality == "ok"


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


def test_rates_core_history_coverage_counts_available_series_not_observation_rows() -> None:
    missing_series = {"fred:DGS10"}
    range_observations = {
        "fred:DGS2": [
            make_observation("fred:DGS2", observed_at="2026-05-20"),
            make_observation("fred:DGS2", observed_at="2026-05-21"),
        ]
    }
    service = MacrodataService(
        gateway=cast(
            MacrodataGateway,
            FakeGateway(failed_series=missing_series, range_observations=range_observations),
        )
    )

    snapshot = service.bundle_history("rates-core", start="2026-05-20", end="2026-05-21")

    assert snapshot.coverage == {"requested": EXPECTED_RATES_CORE_SIZE, "available": EXPECTED_RATES_CORE_SIZE - 1}
    assert len(snapshot.observations) == EXPECTED_RATES_CORE_SIZE
    assert snapshot.missing_series == ["fred:DGS10"]
    assert snapshot.series_errors == [
        {
            "series_key": "fred:DGS10",
            "provider": "fred",
            "code": "no_data",
            "retryable": False,
            "message": "missing fred:DGS10",
        }
    ]
    assert snapshot.data_quality == "partial"
    assert snapshot.reason_codes == ["missing_series", "no_data"]


def test_bundle_history_can_fetch_series_concurrently_for_runtime_sync() -> None:
    fake_gateway = DelayedRangeGateway(delay_seconds=0.02)
    service = MacrodataService(gateway=cast(MacrodataGateway, fake_gateway), max_workers=4)

    snapshot = service.bundle_history("rates-core", start="2026-05-20", end="2026-05-21")

    assert fake_gateway.max_in_flight > 1
    assert [observation.series_key for observation in snapshot.observations] == RATES_CORE
    assert snapshot.coverage == {"requested": EXPECTED_RATES_CORE_SIZE, "available": EXPECTED_RATES_CORE_SIZE}
    assert snapshot.source_chain == ["fred", "nyfed"]


def test_unknown_bundle_raises_structured_validation_error() -> None:
    service = MacrodataService(gateway=cast(MacrodataGateway, FakeGateway()))

    with pytest.raises(MacrodataError) as raised:
        service.bundle("unknown-core", asof="2026-05-21")

    assert raised.value.code == "unknown_bundle"
    assert raised.value.exit_code == VALIDATION_EXIT_CODE
