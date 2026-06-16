from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

DERIBIT_BASE_URL = "https://www.deribit.com"
DERIBIT_VOLATILITY_CANDLE_FIELDS = 5


@dataclass(frozen=True, slots=True)
class _DeribitDataset:
    instrument_name: str | None
    currency: str | None
    metric: str
    unit: str


DERIBIT_PUBLIC_DATASETS: dict[str, _DeribitDataset] = {
    "BTC-PERPETUAL:open_interest_usd": _DeribitDataset("BTC-PERPETUAL", None, "open_interest_usd", "usd"),
    "BTC-PERPETUAL:funding_8h": _DeribitDataset("BTC-PERPETUAL", None, "funding_8h", "rate"),
    "BTC-PERPETUAL:basis_pct": _DeribitDataset("BTC-PERPETUAL", None, "basis_pct", "percent"),
    "BTC:volatility_index": _DeribitDataset(None, "BTC", "volatility_index", "index"),
    "ETH-PERPETUAL:open_interest_usd": _DeribitDataset("ETH-PERPETUAL", None, "open_interest_usd", "usd"),
    "ETH-PERPETUAL:funding_8h": _DeribitDataset("ETH-PERPETUAL", None, "funding_8h", "rate"),
    "ETH-PERPETUAL:basis_pct": _DeribitDataset("ETH-PERPETUAL", None, "basis_pct", "percent"),
    "ETH:volatility_index": _DeribitDataset(None, "ETH", "volatility_index", "index"),
}


class DeribitPublicMarketProvider:
    provider_name = "deribit"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        spec = _dataset_spec(dataset)
        if spec.metric == "volatility_index":
            if spec.currency is None:
                raise _unknown_dataset(dataset)
            return self._volatility_index_observation(dataset=dataset, currency=spec.currency)
        if spec.instrument_name is None:
            raise _unknown_dataset(dataset)
        ticker = self._fetch_ticker(spec.instrument_name)
        if spec.metric == "open_interest_usd":
            return _observation(
                dataset=dataset,
                metric=spec.metric,
                value=_number_field(ticker, "open_interest", dataset=dataset),
                unit=spec.unit,
                timestamp_ms=_timestamp_field(ticker, dataset=dataset),
                source_url=f"{DERIBIT_BASE_URL}/api/v2/public/ticker",
            )
        if spec.metric == "funding_8h":
            return _observation(
                dataset=dataset,
                metric=spec.metric,
                value=_number_field(ticker, "funding_8h", dataset=dataset),
                unit=spec.unit,
                timestamp_ms=_timestamp_field(ticker, dataset=dataset),
                source_url=f"{DERIBIT_BASE_URL}/api/v2/public/ticker",
            )
        if spec.metric == "basis_pct":
            mark = _number_field(ticker, "mark_price", dataset=dataset)
            index = _number_field(ticker, "index_price", dataset=dataset)
            if index == 0:
                raise _parse_error(f"Deribit index price is zero for {dataset}")
            return _observation(
                dataset=dataset,
                metric=spec.metric,
                value=round(((mark - index) / index) * 100.0, 6),
                unit=spec.unit,
                timestamp_ms=_timestamp_field(ticker, dataset=dataset),
                source_url=f"{DERIBIT_BASE_URL}/api/v2/public/ticker",
            )
        raise _unknown_dataset(dataset)

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        start_date = _parse_request_date("start", start)
        end_date = _parse_request_date("end", end)
        observation = self.get_latest(dataset)
        observed_at = date.fromisoformat(observation.observed_at)
        return [observation] if start_date <= observed_at <= end_date else []

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("BTC-PERPETUAL:open_interest_usd")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider=self.provider_name,
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider=self.provider_name,
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="BTC-PERPETUAL:open_interest_usd",
            sample_source_ts=latest.source_ts,
        )

    def _fetch_ticker(self, instrument_name: str) -> dict[str, Any]:
        payload = self._http_client.get_json(
            f"{DERIBIT_BASE_URL}/api/v2/public/ticker",
            params={"instrument_name": instrument_name},
            provider=self.provider_name,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise _parse_error(f"Deribit returned no ticker result for {instrument_name}")
        return dict(result)

    def _volatility_index_observation(self, *, dataset: str, currency: str) -> MacroObservation:
        now = datetime.now(UTC)
        payload = self._http_client.get_json(
            f"{DERIBIT_BASE_URL}/api/v2/public/get_volatility_index_data",
            params={
                "currency": currency,
                "start_timestamp": int((now - timedelta(days=1)).timestamp() * 1000),
                "end_timestamp": int(now.timestamp() * 1000),
                "resolution": "60",
            },
            provider=self.provider_name,
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise _parse_error(f"Deribit returned no volatility result for {currency}")
        data = result.get("data")
        if not isinstance(data, list) or not data:
            raise _parse_error(f"Deribit returned no volatility index candles for {currency}")
        latest = data[-1]
        if not isinstance(latest, list) or len(latest) < DERIBIT_VOLATILITY_CANDLE_FIELDS:
            raise _parse_error(f"Deribit volatility index candle is malformed for {currency}")
        timestamp_ms = _int_value(latest[0], field="timestamp", dataset=dataset)
        value = _float_value(latest[4], field="close", dataset=dataset)
        return _observation(
            dataset=dataset,
            metric="volatility_index",
            value=value,
            unit="index",
            timestamp_ms=timestamp_ms,
            source_url=f"{DERIBIT_BASE_URL}/api/v2/public/get_volatility_index_data",
        )


def _dataset_spec(dataset: str) -> _DeribitDataset:
    normalized = _normalize_dataset(dataset)
    spec = DERIBIT_PUBLIC_DATASETS.get(normalized)
    if spec is None:
        raise _unknown_dataset(dataset)
    return spec


def _normalize_dataset(dataset: str) -> str:
    market, separator, metric = str(dataset or "").strip().partition(":")
    if not separator:
        return market.upper()
    return f"{market.upper()}:{metric.strip().lower()}"


def _number_field(row: dict[str, Any], field: str, *, dataset: str) -> float:
    return _float_value(row.get(field), field=field, dataset=dataset)


def _float_value(raw_value: Any, *, field: str, dataset: str) -> float:
    try:
        return float(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise _parse_error(f"Deribit {field} is not numeric for {dataset}: {raw_value}") from exc


def _int_value(raw_value: Any, *, field: str, dataset: str) -> int:
    try:
        return int(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise _parse_error(f"Deribit {field} is not an integer for {dataset}: {raw_value}") from exc


def _timestamp_field(row: dict[str, Any], *, dataset: str) -> int:
    return _int_value(row.get("timestamp"), field="timestamp", dataset=dataset)


def _observation(
    *,
    dataset: str,
    metric: str,
    value: float,
    unit: str,
    timestamp_ms: int,
    source_url: str,
) -> MacroObservation:
    observed_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    source_ts = observed_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
    return MacroObservation(
        series_key=f"deribit:{dataset}",
        provider="deribit",
        dataset=dataset,
        observed_at=observed_dt.date().isoformat(),
        value=value,
        unit=unit,
        frequency="intraday",
        source_ts=source_ts,
        realtime_start=None,
        realtime_end=None,
        latency_class="realtime",
        data_quality="ok",
        provenance=[
            {
                "provider": "deribit",
                "source_url": source_url,
                "metric": metric,
                "access_mode": "public_rest",
            }
        ],
    )


def _parse_request_date(label: str, raw_value: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"Deribit {label} date is invalid: {raw_value}",
            retryable=False,
            provider="deribit",
        ) from exc


def _unknown_dataset(dataset: str) -> MacrodataError:
    return MacrodataError(
        code="unknown_series",
        message=f"Deribit public dataset is not supported: {dataset}",
        provider="deribit",
        exit_code=2,
    )


def _parse_error(message: str) -> MacrodataError:
    return MacrodataError(code="provider_parse_error", message=message, retryable=False, provider="deribit")
