from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

OKX_BASE_URL = "https://www.okx.com"


@dataclass(frozen=True, slots=True)
class _OkxDataset:
    inst_id: str
    metric: str
    unit: str


OKX_PUBLIC_DATASETS: dict[str, _OkxDataset] = {
    "BTC-USDT-SWAP:open_interest_usd": _OkxDataset("BTC-USDT-SWAP", "open_interest_usd", "usd"),
    "BTC-USDT-SWAP:funding_rate": _OkxDataset("BTC-USDT-SWAP", "funding_rate", "rate"),
    "BTC-USDT-SWAP:basis_pct": _OkxDataset("BTC-USDT-SWAP", "basis_pct", "percent"),
    "ETH-USDT-SWAP:open_interest_usd": _OkxDataset("ETH-USDT-SWAP", "open_interest_usd", "usd"),
    "ETH-USDT-SWAP:funding_rate": _OkxDataset("ETH-USDT-SWAP", "funding_rate", "rate"),
    "ETH-USDT-SWAP:basis_pct": _OkxDataset("ETH-USDT-SWAP", "basis_pct", "percent"),
}


class OkxPublicDataProvider:
    provider_name = "okx"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        spec = _dataset_spec(dataset)
        if spec.metric == "open_interest_usd":
            row = self._fetch_open_interest(spec.inst_id)
            return _observation(
                dataset=dataset,
                metric=spec.metric,
                value=_number_field(row, "oiUsd", dataset=dataset),
                unit=spec.unit,
                timestamp_ms=_timestamp_field(row, ("ts",), dataset=dataset),
                source_url=f"{OKX_BASE_URL}/api/v5/public/open-interest",
            )
        if spec.metric == "funding_rate":
            row = self._fetch_funding(spec.inst_id)
            return _observation(
                dataset=dataset,
                metric=spec.metric,
                value=_number_field(row, "fundingRate", dataset=dataset),
                unit=spec.unit,
                timestamp_ms=_timestamp_field(row, ("fundingTime", "ts"), dataset=dataset),
                source_url=f"{OKX_BASE_URL}/api/v5/public/funding-rate",
            )
        if spec.metric == "basis_pct":
            mark_row = self._fetch_mark_price(spec.inst_id)
            index_row = self._fetch_index_ticker(_index_id(spec.inst_id))
            mark = _number_field(mark_row, "markPx", dataset=dataset)
            index = _number_field(index_row, "idxPx", dataset=dataset)
            if index == 0:
                raise _parse_error(f"OKX index price is zero for {dataset}")
            timestamp_ms = max(
                _timestamp_field(mark_row, ("ts",), dataset=dataset),
                _timestamp_field(index_row, ("ts",), dataset=dataset),
            )
            return _observation(
                dataset=dataset,
                metric=spec.metric,
                value=round(((mark - index) / index) * 100.0, 6),
                unit=spec.unit,
                timestamp_ms=timestamp_ms,
                source_url=f"{OKX_BASE_URL}/api/v5/public/mark-price",
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
            latest = self.get_latest("BTC-USDT-SWAP:open_interest_usd")
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
            sample_dataset="BTC-USDT-SWAP:open_interest_usd",
            sample_source_ts=latest.source_ts,
        )

    def _fetch_open_interest(self, inst_id: str) -> dict[str, Any]:
        return _single_data_row(
            self._http_client.get_json(
                f"{OKX_BASE_URL}/api/v5/public/open-interest",
                params={"instType": "SWAP", "instId": inst_id},
                provider=self.provider_name,
            ),
            dataset=inst_id,
        )

    def _fetch_funding(self, inst_id: str) -> dict[str, Any]:
        return _single_data_row(
            self._http_client.get_json(
                f"{OKX_BASE_URL}/api/v5/public/funding-rate",
                params={"instId": inst_id},
                provider=self.provider_name,
            ),
            dataset=inst_id,
        )

    def _fetch_mark_price(self, inst_id: str) -> dict[str, Any]:
        return _single_data_row(
            self._http_client.get_json(
                f"{OKX_BASE_URL}/api/v5/public/mark-price",
                params={"instType": "SWAP", "instId": inst_id},
                provider=self.provider_name,
            ),
            dataset=inst_id,
        )

    def _fetch_index_ticker(self, inst_id: str) -> dict[str, Any]:
        return _single_data_row(
            self._http_client.get_json(
                f"{OKX_BASE_URL}/api/v5/market/index-tickers",
                params={"instId": inst_id},
                provider=self.provider_name,
            ),
            dataset=inst_id,
        )


def _dataset_spec(dataset: str) -> _OkxDataset:
    normalized = _normalize_dataset(dataset)
    spec = OKX_PUBLIC_DATASETS.get(normalized)
    if spec is None:
        raise _unknown_dataset(dataset)
    return spec


def _normalize_dataset(dataset: str) -> str:
    market, separator, metric = str(dataset or "").strip().partition(":")
    if not separator:
        return market.upper()
    return f"{market.upper()}:{metric.strip().lower()}"


def _single_data_row(payload: dict[str, Any], *, dataset: str) -> dict[str, Any]:
    code = str(payload.get("code") or "").strip()
    if code and code != "0":
        raise MacrodataError(
            code="provider_response_error",
            message=f"OKX returned code {code} for {dataset}",
            retryable=False,
            provider="okx",
        )
    data = payload.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise _parse_error(f"OKX returned no data row for {dataset}")
    return dict(data[0])


def _number_field(row: dict[str, Any], field: str, *, dataset: str) -> float:
    raw_value = row.get(field)
    try:
        return float(str(raw_value).strip())
    except (TypeError, ValueError) as exc:
        raise _parse_error(f"OKX {field} is not numeric for {dataset}: {raw_value}") from exc


def _timestamp_field(row: dict[str, Any], fields: tuple[str, ...], *, dataset: str) -> int:
    for field in fields:
        raw_value = row.get(field)
        if raw_value is None or str(raw_value).strip() == "":
            continue
        try:
            return int(str(raw_value).strip())
        except ValueError as exc:
            raise _parse_error(f"OKX {field} timestamp is invalid for {dataset}: {raw_value}") from exc
    joined = ", ".join(fields)
    raise _parse_error(f"OKX timestamp is missing for {dataset}: {joined}")


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
        series_key=f"okx:{dataset}",
        provider="okx",
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
                "provider": "okx",
                "source_url": source_url,
                "metric": metric,
                "access_mode": "public_rest",
            }
        ],
    )


def _index_id(inst_id: str) -> str:
    if inst_id.endswith("-SWAP"):
        return inst_id.removesuffix("-SWAP")
    return inst_id


def _parse_request_date(label: str, raw_value: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"OKX {label} date is invalid: {raw_value}",
            retryable=False,
            provider="okx",
        ) from exc


def _unknown_dataset(dataset: str) -> MacrodataError:
    return MacrodataError(
        code="unknown_series",
        message=f"OKX public dataset is not supported: {dataset}",
        provider="okx",
        exit_code=2,
    )


def _parse_error(message: str) -> MacrodataError:
    return MacrodataError(code="provider_parse_error", message=message, retryable=False, provider="okx")
