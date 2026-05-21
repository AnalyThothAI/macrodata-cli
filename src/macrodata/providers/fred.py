from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from io import StringIO
from typing import Any

import httpx

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class FredSeriesProvider:
    provider_name = "fred"
    base_url = "https://api.stlouisfed.org/fred/series/observations"
    public_csv_url = "https://fred.stlouisfed.org/graph/fredgraph.csv"

    def __init__(self, *, http_client: MacrodataHttpClient, api_key: str | None) -> None:
        self._http_client = http_client
        self._api_key = (api_key or "").strip()

    def get_latest(self, dataset: str) -> MacroObservation:
        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=3650)
        observations = self.get_range(dataset, start=start_date.isoformat(), end=end_date.isoformat())
        if not observations:
            raise MacrodataError(
                code="no_data",
                message=f"FRED returned no data for {dataset}",
                provider="fred",
                exit_code=4,
            )
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        if not self._api_key:
            return self._get_range_from_public_csv(dataset, start=start, end=end)

        payload = self._http_client.get_json(
            self.base_url,
            params={
                "series_id": dataset,
                "api_key": self._api_key,
                "file_type": "json",
                "observation_start": start,
                "observation_end": end,
                "sort_order": "asc",
            },
            provider="fred",
        )
        raw_observations = payload.get("observations", [])
        if not isinstance(raw_observations, list):
            raise MacrodataError(
                code="provider_parse_error",
                message="FRED observations must be a list",
                provider="fred",
            )
        observations: list[MacroObservation] = []
        for index, item in enumerate(raw_observations):
            if not isinstance(item, dict):
                raise MacrodataError(
                    code="provider_parse_error",
                    message=f"FRED observation row {index} for {dataset} must be an object",
                    provider="fred",
                )
            observations.append(self._parse_observation(dataset, item))
        return observations

    def _get_range_from_public_csv(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        text = self._get_public_csv_text(dataset, start=start, end=end)
        rows = self._parse_public_csv_rows(dataset, text)
        observations: list[MacroObservation] = []
        for row in rows:
            observed_at = str(row.get("observation_date", "")).strip()
            if not observed_at or observed_at < start or observed_at > end:
                continue
            observations.append(self._parse_observation(dataset, {"date": observed_at, "value": row.get(dataset)}))
        return observations

    def _get_public_csv_text(self, dataset: str, *, start: str, end: str) -> str:
        try:
            with httpx.Client(timeout=self._http_client.timeout_sec, follow_redirects=True) as client:
                response = client.get(
                    self.public_csv_url,
                    params={"id": dataset, "cosd": start, "coed": end},
                    headers={"User-Agent": "macrodata-cli/0.1"},
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MacrodataError(
                code="provider_timeout",
                message=f"fred request timed out after {self._http_client.timeout_sec:.1f} seconds",
                retryable=True,
                provider="fred",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MacrodataError(
                code="provider_http_error",
                message=f"fred returned HTTP {exc.response.status_code}",
                retryable=exc.response.status_code in {429, 500, 502, 503, 504},
                provider="fred",
            ) from exc
        except httpx.InvalidURL as exc:
            raise MacrodataError(
                code="provider_invalid_request",
                message="fred request URL is invalid",
                retryable=False,
                provider="fred",
            ) from exc
        except httpx.RequestError as exc:
            raise MacrodataError(
                code="provider_request_error",
                message=f"fred request failed: {type(exc).__name__}",
                retryable=not isinstance(exc, (httpx.UnsupportedProtocol, httpx.LocalProtocolError)),
                provider="fred",
            ) from exc
        return response.text

    def _parse_public_csv_rows(self, dataset: str, text: str) -> list[dict[str, str]]:
        try:
            rows = list(csv.DictReader(StringIO(text)))
        except csv.Error as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"FRED CSV for {dataset} could not be parsed",
                retryable=False,
                provider="fred",
            ) from exc
        if not rows:
            return []
        required_columns = {"observation_date", dataset}
        if not required_columns.issubset(rows[0]):
            raise MacrodataError(
                code="provider_parse_error",
                message=f"FRED CSV for {dataset} is missing required columns",
                retryable=False,
                provider="fred",
            )
        return rows

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("DGS10")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider="fred",
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider="fred",
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="DGS10",
            sample_source_ts=latest.source_ts,
        )

    def _parse_observation(self, dataset: str, item: dict[str, Any]) -> MacroObservation:
        observed_at = str(item.get("date", "")).strip()
        raw_value = item.get("value")
        value = self._parse_value(dataset=dataset, observed_at=observed_at, raw_value=raw_value)
        return MacroObservation(
            series_key=f"fred:{dataset}",
            provider="fred",
            dataset=dataset,
            observed_at=observed_at,
            value=value,
            unit=None,
            frequency=None,
            source_ts=observed_at,
            realtime_start=item.get("realtime_start"),
            realtime_end=item.get("realtime_end"),
            latency_class="eod",
            data_quality="ok" if value is not None else "partial",
            provenance=[{"provider": "fred", "source_url": f"https://fred.stlouisfed.org/series/{dataset}"}],
        )

    def _parse_value(self, *, dataset: str, observed_at: str, raw_value: Any) -> float | None:
        if raw_value is None or str(raw_value).strip() in {"", "."}:
            return None
        try:
            return float(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"FRED value for {dataset} on {observed_at or 'unknown date'} is not numeric",
                retryable=False,
                provider="fred",
            ) from exc
