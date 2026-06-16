from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from macrodata.core.errors import MacrodataError, ValidationError
from macrodata.core.models import BundleSnapshot, DataQuality, MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway


def _unique(series: list[str]) -> list[str]:
    return list(dict.fromkeys(series))


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
    "nyfed:RRP",
    "nyfed:SRF",
    "nyfed:SOFR",
    "treasury_fiscal:operating_cash_balance",
]


RATES_MARKET_CORE = _unique(
    [
        "fred:DFF",
        "fred:FEDFUNDS",
        "fred:SOFR30DAYAVG",
        "fred:EFFR",
        "fred:DFEDTARU",
        "fred:DFEDTARL",
        "fred:IORB",
        "nyfed:SOFR",
        "fred:DGS1MO",
        "fred:DGS3MO",
        "fred:DGS6MO",
        "fred:DGS1",
        "fred:DGS2",
        "fred:DGS3",
        "fred:DGS5",
        "fred:DGS7",
        "fred:DGS10",
        "fred:DGS20",
        "fred:DGS30",
        "fred:T10Y2Y",
        "fred:T10Y3M",
        "fred:DFII5",
        "fred:DFII10",
        "fred:DFII30",
        "fred:T5YIE",
        "fred:T10YIE",
        "fred:T5YIFR",
        "fred:MICH",
    ]
)

ECONOMY_CORE = [
    "fred:GDP",
    "fred:GDPC1",
    "fred:GDPDEF",
    "fred:PAYEMS",
    "fred:UNRATE",
    "fred:CIVPART",
    "fred:ICSA",
    "fred:JTSJOL",
    "fred:CES0500000003",
    "fred:CPIAUCSL",
    "fred:CPILFESL",
    "fred:PPIACO",
    "fred:PCEPI",
    "fred:PCEPILFE",
    "fred:PCE",
    "fred:PCEC96",
    "fred:RSAFS",
    "fred:INDPRO",
    "fred:HOUST",
    "fred:UMCSENT",
    "fred:PSAVERT",
]

VOLATILITY_CORE = [
    "fred:VIXCLS",
    "fred:VXVCLS",
    "fred:VXNCLS",
    "fred:RVXCLS",
    "fred:GVZCLS",
    "fred:OVXCLS",
    "fred:EVZCLS",
    "yahoo:^MOVE",
    "yahoo:VIXY",
    "yahoo:VIXM",
]

CREDIT_CORE = [
    "fred:BAMLC0A0CM",
    "fred:BAMLC0A1CAAA",
    "fred:BAMLC0A2CAA",
    "fred:BAMLC0A3CA",
    "fred:BAMLC0A4CBBB",
    "fred:BAMLH0A0HYM2",
    "fred:BAMLH0A1HYBB",
    "fred:BAMLH0A2HYB",
    "fred:BAMLH0A3HYC",
    "fred:BAMLC0A0CMEY",
    "fred:BAMLH0A0HYM2EY",
    "fred:STLFSI4",
    "fred:NFCI",
    "fred:ANFCI",
    "fred:DRTSCILM",
    "fred:DRTSCIS",
    "fred:DRSDCILM",
    "fred:DRSDCIS",
    "fred:DRBLACBS",
    "fred:DRCLACBS",
    "fred:CORBLACBS",
    "fred:CORCACBS",
    "yahoo:HYG",
    "yahoo:JNK",
    "yahoo:LQD",
]

ASSETS_CORE = [
    "fred:SP500",
    "fred:NASDAQCOM",
    "fred:DCOILWTICO",
    "fred:DCOILBRENTEU",
    "fred:DHHNGSP",
    "fred:DTWEXBGS",
    "fred:DEXUSEU",
    "fred:DEXJPUS",
    "fred:DEXCHUS",
    "fred:DEXUSUK",
    "yahoo:^GSPC",
    "yahoo:^NDX",
    "yahoo:^DJI",
    "yahoo:^RUT",
    "yahoo:SPY",
    "yahoo:QQQ",
    "yahoo:DIA",
    "yahoo:IWM",
    "yahoo:EFA",
    "yahoo:EEM",
    "yahoo:TLT",
    "yahoo:IEF",
    "yahoo:SHY",
    "yahoo:TIP",
    "yahoo:BND",
    "yahoo:GLD",
    "yahoo:SLV",
    "yahoo:GC=F",
    "yahoo:SI=F",
    "yahoo:USO",
    "yahoo:CL=F",
    "yahoo:UNG",
    "yahoo:NG=F",
    "yahoo:CPER",
    "yahoo:HG=F",
    "yahoo:SMH",
    "yahoo:SOXX",
    "yahoo:UUP",
    "yahoo:FXE",
    "yahoo:FXY",
    "yahoo:DX-Y.NYB",
    "yahoo:EURUSD=X",
    "yahoo:GBPUSD=X",
    "yahoo:USDJPY=X",
    "yahoo:USDCNY=X",
    "yahoo:USDKRW=X",
    "yahoo:BTC-USD",
    "yahoo:ETH-USD",
]

MACRO_CALENDAR_CORE = [
    "official_calendar:fomc_decision_next",
    "official_calendar:bea_gdp_next",
    "official_calendar:bea_pce_next",
    "official_calendar:bls_cpi_next",
    "official_calendar:bls_employment_next",
    "official_calendar:bls_ppi_next",
]

FED_TEXT_CORE = [
    "official_fed_text:fomc_statement_latest",
    "official_fed_text:fomc_minutes_latest",
    "official_fed_text:monetary_policy_press_release_latest",
    "official_fed_text:speech_latest",
]

TREASURY_AUCTION_CORE = [
    "treasury_auction:2y_next_auction_days",
    "treasury_auction:10y_next_auction_days",
    "treasury_auction:30y_next_auction_days",
    "treasury_auction:2y_high_yield",
    "treasury_auction:2y_bid_to_cover",
    "treasury_auction:2y_indirect_bidder_pct",
    "treasury_auction:10y_high_yield",
    "treasury_auction:10y_bid_to_cover",
    "treasury_auction:10y_indirect_bidder_pct",
    "treasury_auction:30y_high_yield",
    "treasury_auction:30y_bid_to_cover",
    "treasury_auction:30y_indirect_bidder_pct",
]

MACRO_CORE = _unique(
    [
        *LIQUIDITY_CORE,
        *RATES_MARKET_CORE,
        *ECONOMY_CORE,
        *VOLATILITY_CORE,
        *CREDIT_CORE,
        *ASSETS_CORE,
        "cftc:financial_futures:sp500_net_noncommercial",
    ]
)

BUNDLES = {
    "rates-core": RATES_CORE,
    "rates-market-core": RATES_MARKET_CORE,
    "liquidity-core": LIQUIDITY_CORE,
    "economy-core": ECONOMY_CORE,
    "volatility-core": VOLATILITY_CORE,
    "credit-core": CREDIT_CORE,
    "assets-core": ASSETS_CORE,
    "macro-calendar-core": MACRO_CALENDAR_CORE,
    "fed-text-core": FED_TEXT_CORE,
    "treasury-auction-core": TREASURY_AUCTION_CORE,
    "macro-core": MACRO_CORE,
}


@dataclass(frozen=True)
class _SeriesFetchResult:
    series_key: str
    observations: list[MacroObservation]
    error: MacrodataError | None = None


class MacrodataService:
    def __init__(self, *, gateway: MacrodataGateway, max_workers: int = 1) -> None:
        self._gateway = gateway
        self._max_workers = max(1, int(max_workers))

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        return self._gateway.fetch_series(series_key, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        return self._gateway.fetch_latest(series_key)

    def bundle(self, bundle: str, *, asof: str) -> BundleSnapshot:
        bundle_name = _normalize_bundle_name(bundle)
        requested = _bundle_series(bundle_name)
        observations, missing_series, series_errors, source_chain, _ = self._collect_bundle_results(
            requested,
            lambda series_key: [self.fetch_latest(series_key)],
            count_available_series=False,
        )

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
        observations, missing_series, series_errors, source_chain, available_series = self._collect_bundle_results(
            requested,
            lambda series_key: self.fetch_series(series_key, start=start, end=end),
            count_available_series=True,
        )

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

    def _collect_bundle_results(
        self,
        requested: list[str],
        fetch: Callable[[str], list[MacroObservation]],
        *,
        count_available_series: bool,
    ) -> tuple[list[MacroObservation], list[str], list[dict[str, object]], list[str], int | None]:
        results = self._fetch_bundle_series(requested, fetch)
        observations: list[MacroObservation] = []
        missing_series: list[str] = []
        series_errors: list[dict[str, object]] = []
        source_chain: list[str] = []
        available_series = 0

        for result in results:
            if result.error is not None:
                missing_series.append(result.series_key)
                series_errors.append(_series_error(series_key=result.series_key, error=result.error))
                continue
            if not result.observations:
                missing_series.append(result.series_key)
                continue
            if count_available_series and result.observations:
                available_series += 1
            observations.extend(result.observations)
            for observation in result.observations:
                if observation.provider not in source_chain:
                    source_chain.append(observation.provider)

        return (
            observations,
            missing_series,
            series_errors,
            source_chain,
            available_series if count_available_series else None,
        )

    def _fetch_bundle_series(
        self,
        requested: list[str],
        fetch: Callable[[str], list[MacroObservation]],
    ) -> list[_SeriesFetchResult]:
        if self._max_workers <= 1 or len(requested) <= 1:
            return [_fetch_one_series(series_key, fetch) for series_key in requested]

        results: list[_SeriesFetchResult | None] = [None] * len(requested)
        worker_count = min(self._max_workers, len(requested))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_fetch_one_series, series_key, fetch): index
                for index, series_key in enumerate(requested)
            }
            for future in as_completed(futures):
                results[futures[future]] = future.result()

        return [result for result in results if result is not None]


def _fetch_one_series(
    series_key: str,
    fetch: Callable[[str], list[MacroObservation]],
) -> _SeriesFetchResult:
    try:
        return _SeriesFetchResult(series_key=series_key, observations=fetch(series_key))
    except MacrodataError as exc:
        return _SeriesFetchResult(series_key=series_key, observations=[], error=exc)


def _normalize_bundle_name(bundle: str) -> str:
    return bundle.strip().lower()


def _bundle_series(bundle: str) -> list[str]:
    series = BUNDLES.get(bundle)
    if series is not None:
        return list(series)
    raise ValidationError(code="unknown_bundle", message=f"unknown bundle: {bundle or '<blank>'}")


def _series_error(*, series_key: str, error: MacrodataError) -> dict[str, object]:
    provider = error.provider or series_key.split(":", 1)[0]
    payload: dict[str, object] = {
        "series_key": series_key,
        "provider": provider,
        "code": error.code,
        "retryable": error.retryable,
        "message": error.message,
    }
    access_mode = error.details.get("access_mode")
    if not access_mode and provider == "fred" and error.code == "missing_api_key":
        access_mode = "api_key"
    if isinstance(access_mode, str) and access_mode:
        payload["access_mode"] = access_mode
    return payload


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
        source_health=_source_health(
            requested=requested,
            observations=observations,
            series_errors=series_errors,
        ),
        source_chain=source_chain,
        data_quality=data_quality,
        reason_codes=_bundle_reason_codes(
            observations=observations,
            missing_series=missing_series,
            errors=series_errors,
        ),
    )


def _source_health(
    *,
    requested: list[str],
    observations: list[MacroObservation],
    series_errors: list[dict[str, object]],
) -> list[dict[str, object]]:
    provider_order: list[str] = []
    requested_by_provider: dict[str, int] = {}
    for series_key in requested:
        provider = series_key.split(":", 1)[0]
        if provider not in requested_by_provider:
            provider_order.append(provider)
            requested_by_provider[provider] = 0
        requested_by_provider[provider] += 1

    available_by_provider: dict[str, set[str]] = {}
    access_modes_by_provider: dict[str, list[str]] = {}
    for observation in observations:
        available_by_provider.setdefault(observation.provider, set()).add(observation.series_key)
        access_mode = _observation_access_mode(observation)
        if access_mode is not None:
            access_modes_by_provider.setdefault(observation.provider, [])
            if access_mode not in access_modes_by_provider[observation.provider]:
                access_modes_by_provider[observation.provider].append(access_mode)

    error_codes_by_provider: dict[str, list[str]] = {}
    retryable_by_provider: dict[str, bool] = {}
    for error in series_errors:
        error_provider = _provider_from_error_payload(error)
        if error_provider not in requested_by_provider:
            provider_order.append(error_provider)
            requested_by_provider[error_provider] = 0

        code = error.get("code")
        if isinstance(code, str) and code:
            error_codes_by_provider.setdefault(error_provider, [])
            if code not in error_codes_by_provider[error_provider]:
                error_codes_by_provider[error_provider].append(code)

        retryable_by_provider[error_provider] = bool(retryable_by_provider.get(error_provider)) or bool(
            error.get("retryable")
        )

        raw_access_mode = error.get("access_mode")
        if isinstance(raw_access_mode, str) and raw_access_mode:
            access_modes_by_provider.setdefault(error_provider, [])
            if raw_access_mode not in access_modes_by_provider[error_provider]:
                access_modes_by_provider[error_provider].append(raw_access_mode)

    return [
        _provider_health_entry(
            provider=provider,
            requested=requested_by_provider[provider],
            available=len(available_by_provider.get(provider, set())),
            access_modes=access_modes_by_provider.get(provider, []),
            error_codes=error_codes_by_provider.get(provider, []),
            retryable=retryable_by_provider.get(provider, False),
        )
        for provider in provider_order
    ]


def _provider_from_error_payload(error: dict[str, object]) -> str:
    raw_provider = error.get("provider")
    if isinstance(raw_provider, str) and raw_provider:
        return raw_provider
    raw_series_key = error.get("series_key")
    return raw_series_key.split(":", 1)[0] if isinstance(raw_series_key, str) else "unknown"


def _provider_health_entry(
    *,
    provider: str,
    requested: int,
    available: int,
    access_modes: list[str],
    error_codes: list[str],
    retryable: bool,
) -> dict[str, object]:
    missing = max(requested - available, 0)
    if missing == 0:
        status: DataQuality = "ok"
    elif available > 0:
        status = "partial"
    else:
        status = "unavailable"

    return {
        "provider": provider,
        "requested": requested,
        "available": available,
        "missing": missing,
        "status": status,
        "access_mode": _access_mode_summary(access_modes),
        "error_codes": error_codes,
        "retryable": retryable,
    }


def _observation_access_mode(observation: MacroObservation) -> str | None:
    for provenance in observation.provenance:
        provider = provenance.get("provider")
        if provider not in {None, observation.provider}:
            continue
        access_mode = provenance.get("access_mode")
        if isinstance(access_mode, str) and access_mode:
            return access_mode
    return None


def _access_mode_summary(access_modes: list[str]) -> str | None:
    unique_modes = list(dict.fromkeys(access_modes))
    if not unique_modes:
        return None
    if len(unique_modes) == 1:
        return unique_modes[0]
    return "mixed"


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
    error_series = {str(error.get("series_key")) for error in errors if error.get("series_key")}
    if any(series_key not in error_series for series_key in missing_series):
        reason_codes.append("no_observations")
    for error in errors:
        code = error["code"]
        if isinstance(code, str) and code not in reason_codes:
            reason_codes.append(code)
    if not observations:
        reason_codes.append("all_series_missing")
    return reason_codes
