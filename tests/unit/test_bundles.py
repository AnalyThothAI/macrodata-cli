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
    def __init__(self, *, failed_series: set[str] | None = None) -> None:
        self.failed_series = failed_series or set()
        self.requested: list[str] = []

    def fetch_latest(self, series_key: str) -> MacroObservation:
        self.requested.append(series_key)
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
    assert snapshot.reason_codes == ["missing_series"]


def test_unknown_bundle_raises_structured_validation_error() -> None:
    service = MacrodataService(gateway=cast(MacrodataGateway, FakeGateway()))

    with pytest.raises(MacrodataError) as raised:
        service.bundle("unknown-core", asof="2026-05-21")

    assert raised.value.code == "unknown_bundle"
    assert raised.value.exit_code == VALIDATION_EXIT_CODE
