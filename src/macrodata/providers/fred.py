from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class FredSeriesProvider:
    provider_name = "fred"
    base_url = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, *, http_client: MacrodataHttpClient, api_key: str | None) -> None:
        self._http_client = http_client
        self._api_key = (api_key or "").strip()

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
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
            raise MacrodataError(
                code="missing_api_key",
                message="FRED_API_KEY is required",
                provider="fred",
                exit_code=2,
            )
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
        return [self._parse_observation(dataset, item) for item in raw_observations if isinstance(item, dict)]

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
        value = None if raw_value in {None, "."} else float(str(raw_value))
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
