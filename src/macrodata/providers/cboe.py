from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import StringIO
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

CBOE_INDEX_HISTORY_URLS = {
    "VIX9D": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv",
    "VVIX": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv",
    "SKEW": "https://cdn.cboe.com/api/global/us_indices/daily_prices/SKEW_History.csv",
}


class CboeIndexProvider:
    provider_name = "cboe"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self._fetch_observations(dataset)
        if observations:
            return observations[-1]
        raise MacrodataError(
            code="no_data",
            message=f"Cboe returned no usable observations for {dataset}",
            provider=self.provider_name,
            exit_code=4,
        )

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        start_date = _parse_request_date("start", start)
        end_date = _parse_request_date("end", end)
        return [
            observation
            for observation in self._fetch_observations(dataset)
            if start_date <= date.fromisoformat(observation.observed_at) <= end_date
        ]

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("VVIX")
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
            sample_dataset="VVIX",
            sample_source_ts=latest.source_ts,
        )

    def _fetch_observations(self, dataset: str) -> list[MacroObservation]:
        source_url = _source_url(dataset)
        text = self._http_client.get_text(source_url, provider=self.provider_name)
        return _parse_history_csv(dataset=dataset, source_url=source_url, text=text)


def _source_url(dataset: str) -> str:
    source_url = CBOE_INDEX_HISTORY_URLS.get(dataset)
    if source_url is not None:
        return source_url
    raise MacrodataError(
        code="unknown_series",
        message=f"Cboe index dataset is not supported: {dataset}",
        provider="cboe",
        exit_code=2,
    )


def _parse_history_csv(*, dataset: str, source_url: str, text: str) -> list[MacroObservation]:
    try:
        reader = csv.DictReader(StringIO(text))
        fieldnames = reader.fieldnames or []
        value_column = _value_column(dataset, fieldnames)
        if "DATE" not in fieldnames or value_column is None:
            raise _parse_error(f"Cboe {dataset} history CSV is missing DATE or value column")
        observations = [
            _parse_row(
                dataset=dataset,
                source_url=source_url,
                row_number=row_number,
                row=row,
                value_column=value_column,
            )
            for row_number, row in enumerate(reader, start=2)
            if _has_data(row)
        ]
    except csv.Error as exc:
        raise _parse_error(f"Cboe {dataset} history CSV could not be parsed") from exc
    return sorted(observations, key=lambda observation: observation.observed_at)


def _parse_row(
    *,
    dataset: str,
    source_url: str,
    row_number: int,
    row: dict[str, Any],
    value_column: str,
) -> MacroObservation:
    observed_at = _parse_observed_at(dataset=dataset, row_number=row_number, raw_value=row.get("DATE"))
    value = _parse_value(dataset=dataset, observed_at=observed_at, raw_value=row.get(value_column))
    return MacroObservation(
        series_key=f"cboe:{dataset}",
        provider="cboe",
        dataset=dataset,
        observed_at=observed_at,
        value=value,
        unit="index",
        frequency="daily",
        source_ts=observed_at,
        realtime_start=None,
        realtime_end=None,
        latency_class="daily",
        data_quality="ok",
        provenance=[{"provider": "cboe", "source_url": source_url}],
    )


def _parse_observed_at(*, dataset: str, row_number: int, raw_value: Any) -> str:
    raw_text = "" if raw_value is None else str(raw_value).strip()
    if not raw_text:
        raise _parse_error(f"Cboe {dataset} date is missing at row {row_number}")
    try:
        return datetime.strptime(raw_text, "%m/%d/%Y").date().isoformat()
    except ValueError as exc:
        raise _parse_error(f"Cboe {dataset} date is invalid at row {row_number}: {raw_text}") from exc


def _parse_value(*, dataset: str, observed_at: str, raw_value: Any) -> float:
    raw_text = "" if raw_value is None else str(raw_value).strip()
    try:
        return float(raw_text)
    except (TypeError, ValueError) as exc:
        raise _parse_error(f"Cboe {dataset} value at {observed_at} is not numeric: {raw_text}") from exc


def _value_column(dataset: str, fieldnames: list[str]) -> str | None:
    if dataset in fieldnames:
        return dataset
    if "CLOSE" in fieldnames:
        return "CLOSE"
    return None


def _parse_request_date(label: str, raw_value: str) -> date:
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"Cboe {label} date is invalid: {raw_value}",
            retryable=False,
            provider="cboe",
        ) from exc


def _has_data(row: dict[str, Any]) -> bool:
    return any(str(value or "").strip() for value in row.values())


def _parse_error(message: str) -> MacrodataError:
    return MacrodataError(
        code="provider_parse_error",
        message=message,
        retryable=False,
        provider="cboe",
    )
