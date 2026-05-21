from __future__ import annotations

import csv
from datetime import UTC, date, datetime
from io import StringIO
from typing import Any

import httpx

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class StooqProvider:
    provider_name = "stooq"
    daily_csv_url = "https://stooq.com/q/d/l/"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(
                code="no_data",
                message=f"Stooq returned no data for {dataset}",
                provider="stooq",
                exit_code=4,
            )
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        text = self._get_text(
            params={"s": dataset, "i": "d", "d1": start.replace("-", ""), "d2": end.replace("-", "")}
        )
        observations = [self._parse_row(dataset, row) for row in self._parse_rows(dataset, text)]
        return sorted(observations, key=lambda observation: observation.observed_at)

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("spy.us")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider="stooq",
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider="stooq",
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="spy.us",
            sample_source_ts=latest.source_ts,
        )

    def _get_text(self, *, params: dict[str, str]) -> str:
        try:
            with httpx.Client(timeout=self._http_client.timeout_sec) as client:
                response = client.get(self.daily_csv_url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MacrodataError(
                code="provider_timeout",
                message=f"stooq request timed out after {self._http_client.timeout_sec:.1f} seconds",
                retryable=True,
                provider="stooq",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MacrodataError(
                code="provider_http_error",
                message=f"stooq returned HTTP {exc.response.status_code}",
                retryable=exc.response.status_code in {429, 500, 502, 503, 504},
                provider="stooq",
            ) from exc
        except httpx.InvalidURL as exc:
            raise MacrodataError(
                code="provider_invalid_request",
                message="stooq request URL is invalid",
                retryable=False,
                provider="stooq",
            ) from exc
        except httpx.RequestError as exc:
            raise MacrodataError(
                code="provider_request_error",
                message=f"stooq request failed: {type(exc).__name__}",
                retryable=not isinstance(exc, (httpx.UnsupportedProtocol, httpx.LocalProtocolError)),
                provider="stooq",
            ) from exc
        return response.text

    def _parse_rows(self, dataset: str, text: str) -> list[dict[str, str]]:
        if self._is_access_instruction_response(text):
            raise MacrodataError(
                code="provider_unavailable",
                message=f"Stooq access instructions returned for {dataset}; API key may be required",
                retryable=False,
                provider="stooq",
            )
        try:
            rows = list(csv.DictReader(StringIO(text)))
        except csv.Error as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Stooq CSV for {dataset} could not be parsed",
                retryable=False,
                provider="stooq",
            ) from exc
        if not rows:
            return []
        required_columns = {"Date", "Close"}
        if not required_columns.issubset(rows[0]):
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Stooq CSV for {dataset} is missing required columns",
                retryable=False,
                provider="stooq",
            )
        return rows

    def _is_access_instruction_response(self, text: str) -> bool:
        normalized = text.lower()
        return "api key" in normalized or "apikey" in normalized or "access to this data" in normalized

    def _parse_row(self, dataset: str, row: dict[str, Any]) -> MacroObservation:
        observed_at = self._parse_observed_at(dataset, row.get("Date"))
        value = self._parse_close(dataset=dataset, observed_at=observed_at, raw_value=row.get("Close"))
        return MacroObservation(
            series_key=f"stooq:{dataset}",
            provider="stooq",
            dataset=dataset,
            observed_at=observed_at,
            value=value,
            unit="price",
            frequency="daily",
            source_ts=observed_at,
            realtime_start=None,
            realtime_end=None,
            latency_class="daily",
            data_quality="ok",
            provenance=[{"provider": "stooq", "source_url": self.daily_csv_url}],
        )

    def _parse_observed_at(self, dataset: str, raw_value: Any) -> str:
        observed_at = "" if raw_value is None else str(raw_value).strip()
        if not observed_at:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Stooq date for {dataset} is missing",
                retryable=False,
                provider="stooq",
            )
        try:
            return date.fromisoformat(observed_at).isoformat()
        except ValueError as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Stooq date for {dataset} is invalid: {observed_at}",
                retryable=False,
                provider="stooq",
            ) from exc

    def _parse_close(self, *, dataset: str, observed_at: str, raw_value: Any) -> float:
        try:
            return float(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Stooq close for {dataset} on {observed_at or 'unknown date'} is not numeric",
                retryable=False,
                provider="stooq",
            ) from exc
