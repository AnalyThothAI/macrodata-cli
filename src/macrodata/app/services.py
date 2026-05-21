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

MACRO_CORE = [
    *LIQUIDITY_CORE,
    "fred:DGS2",
    "fred:DGS5",
    "fred:DGS10",
    "fred:DGS30",
    "fred:T10Y2Y",
    "fred:T10Y3M",
    "fred:DFII10",
    "fred:T10YIE",
    "fred:T5YIFR",
    "fred:DFEDTARU",
    "fred:DFEDTARL",
    "fred:EFFR",
    "fred:IORB",
    "fred:BAMLC0A0CM",
    "fred:BAMLH0A0HYM2",
    "fred:VIXCLS",
    "fred:SP500",
    "fred:DCOILWTICO",
    "fred:DTWEXBGS",
    "stooq:spy.us",
    "stooq:qqq.us",
    "stooq:iwm.us",
    "stooq:tlt.us",
    "stooq:hyg.us",
    "stooq:lqd.us",
    "stooq:gld.us",
    "stooq:uso.us",
    "cftc:financial_futures:sp500_net_noncommercial",
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
        series_errors: list[dict[str, object]] = []
        source_chain: list[str] = []

        for series_key in requested:
            try:
                observation = self.fetch_latest(series_key)
            except MacrodataError as exc:
                missing_series.append(series_key)
                series_errors.append(_series_error(series_key=series_key, error=exc))
                continue
            observations.append(observation)
            if observation.provider not in source_chain:
                source_chain.append(observation.provider)

        return _bundle_snapshot(
            bundle_name=bundle_name,
            asof=asof,
            requested=requested,
            observations=observations,
            missing_series=missing_series,
            series_errors=series_errors,
            source_chain=source_chain,
        )

    def bundle_history(self, bundle: str, *, start: str, end: str) -> BundleSnapshot:
        bundle_name = _normalize_bundle_name(bundle)
        requested = _bundle_series(bundle_name)
        observations: list[MacroObservation] = []
        missing_series: list[str] = []
        series_errors: list[dict[str, object]] = []
        source_chain: list[str] = []
        available_series = 0

        for series_key in requested:
            try:
                series_observations = self.fetch_series(series_key, start=start, end=end)
            except MacrodataError as exc:
                missing_series.append(series_key)
                series_errors.append(_series_error(series_key=series_key, error=exc))
                continue
            if series_observations:
                available_series += 1
            observations.extend(series_observations)
            for observation in series_observations:
                if observation.provider not in source_chain:
                    source_chain.append(observation.provider)

        return _bundle_snapshot(
            bundle_name=bundle_name,
            asof=end,
            requested=requested,
            observations=observations,
            missing_series=missing_series,
            series_errors=series_errors,
            source_chain=source_chain,
            available_count=available_series,
        )


def _normalize_bundle_name(bundle: str) -> str:
    return bundle.strip().lower()


def _bundle_series(bundle: str) -> list[str]:
    if bundle == "rates-core":
        return list(RATES_CORE)
    if bundle == "liquidity-core":
        return list(LIQUIDITY_CORE)
    if bundle == "macro-core":
        return list(MACRO_CORE)
    raise ValidationError(code="unknown_bundle", message=f"unknown bundle: {bundle or '<blank>'}")


def _series_error(*, series_key: str, error: MacrodataError) -> dict[str, object]:
    provider = error.provider or series_key.split(":", 1)[0]
    return {
        "series_key": series_key,
        "provider": provider,
        "code": error.code,
        "retryable": error.retryable,
        "message": error.message,
    }


def _bundle_snapshot(
    *,
    bundle_name: str,
    asof: str,
    requested: list[str],
    observations: list[MacroObservation],
    missing_series: list[str],
    series_errors: list[dict[str, object]],
    source_chain: list[str],
    available_count: int | None = None,
) -> BundleSnapshot:
    data_quality = _bundle_data_quality(observations=observations, missing_series=missing_series)
    available = available_count if available_count is not None else len(observations)
    return BundleSnapshot(
        bundle=bundle_name,
        asof=asof,
        observations=observations,
        coverage={"requested": len(requested), "available": available},
        missing_series=missing_series,
        series_errors=series_errors,
        source_chain=source_chain,
        data_quality=data_quality,
        reason_codes=_bundle_reason_codes(
            observations=observations,
            missing_series=missing_series,
            errors=series_errors,
        ),
    )


def _bundle_data_quality(*, observations: list[MacroObservation], missing_series: list[str]) -> DataQuality:
    if not missing_series:
        return "ok"
    if not observations:
        return "unavailable"
    return "partial"


def _bundle_reason_codes(
    *,
    observations: list[MacroObservation],
    missing_series: list[str],
    errors: list[dict[str, object]],
) -> list[str]:
    if not missing_series:
        return []
    reason_codes = ["missing_series"]
    for error in errors:
        code = error["code"]
        if isinstance(code, str) and code not in reason_codes:
            reason_codes.append(code)
    if not observations:
        reason_codes.append("all_series_missing")
    return reason_codes
