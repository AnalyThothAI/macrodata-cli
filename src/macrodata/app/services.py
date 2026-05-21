from __future__ import annotations

from macrodata.core.errors import MacrodataError, ValidationError
from macrodata.core.models import BundleSnapshot, DataQuality, MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway

RATES_CORE = [
    "fred:DGS2",
    "fred:DGS10",
    "fred:DGS30",
    "fred:T10Y2Y",
    "fred:T10YIE",
    "fred:DFEDTARU",
    "fred:DFEDTARL",
    "fred:IORB",
    "nyfed:SOFR",
]

LIQUIDITY_CORE = [
    "fred:WALCL",
    "fred:WRBWFRBL",
    "fred:RRPONTSYD",
    "nyfed:SOFR",
    "treasury_fiscal:operating_cash_balance",
]


class MacrodataService:
    def __init__(self, *, gateway: MacrodataGateway) -> None:
        self._gateway = gateway

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        return self._gateway.fetch_series(series_key, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        return self._gateway.fetch_latest(series_key)

    def bundle(self, bundle: str, *, asof: str) -> BundleSnapshot:
        bundle_name = _normalize_bundle_name(bundle)
        requested = _bundle_series(bundle_name)
        observations: list[MacroObservation] = []
        missing_series: list[str] = []
        source_chain: list[str] = []

        for series_key in requested:
            try:
                observation = self.fetch_latest(series_key)
            except MacrodataError:
                missing_series.append(series_key)
                continue
            observations.append(observation)
            if observation.provider not in source_chain:
                source_chain.append(observation.provider)

        data_quality: DataQuality = "ok" if not missing_series else "partial"
        return BundleSnapshot(
            bundle=bundle_name,
            asof=asof,
            observations=observations,
            coverage={"requested": len(requested), "available": len(observations)},
            missing_series=missing_series,
            source_chain=source_chain,
            data_quality=data_quality,
            reason_codes=["missing_series"] if missing_series else [],
        )


def _normalize_bundle_name(bundle: str) -> str:
    return bundle.strip().lower()


def _bundle_series(bundle: str) -> list[str]:
    if bundle == "rates-core":
        return list(RATES_CORE)
    if bundle == "liquidity-core":
        return list(LIQUIDITY_CORE)
    raise ValidationError(code="unknown_bundle", message=f"unknown bundle: {bundle or '<blank>'}")
