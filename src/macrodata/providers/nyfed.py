from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class NyFedMarketsProvider:
    provider_name = "nyfed"
    sofr_url = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(
                code="no_data",
                message=f"NY Fed returned no data for {dataset}",
                provider="nyfed",
                exit_code=4,
            )
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        if dataset != "SOFR":
            raise MacrodataError(
                code="unknown_series",
                message=f"NY Fed dataset is not supported: {dataset}",
                provider="nyfed",
                exit_code=2,
            )
        payload = self._http_client.get_json(
            self.sofr_url,
            params={"startDate": start, "endDate": end, "type": "rate"},
            provider="nyfed",
        )
        rows = payload.get("refRates", [])
        if not isinstance(rows, list):
            raise MacrodataError(
                code="provider_parse_error",
                message="NY Fed refRates must be a list",
                provider="nyfed",
            )
        observations: list[MacroObservation] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise MacrodataError(
                    code="provider_parse_error",
                    message=f"NY Fed refRates row {index} for SOFR must be an object",
                    provider="nyfed",
                )
            observations.append(self._parse_sofr(row))
        return observations

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("SOFR")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider="nyfed",
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider="nyfed",
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="SOFR",
            sample_source_ts=latest.source_ts,
        )

    def _parse_sofr(self, row: dict[str, Any]) -> MacroObservation:
        observed_at = str(row.get("effectiveDate", "")).strip()
        value = self._parse_percent_rate(observed_at=observed_at, raw_value=row.get("percentRate"))
        return MacroObservation(
            series_key="nyfed:SOFR",
            provider="nyfed",
            dataset="SOFR",
            observed_at=observed_at,
            value=value,
            unit="percent",
            frequency="daily",
            source_ts=observed_at,
            realtime_start=None,
            realtime_end=None,
            latency_class="daily",
            data_quality="ok",
            provenance=[{"provider": "nyfed", "source_url": self.sofr_url}],
        )

    def _parse_percent_rate(self, *, observed_at: str, raw_value: Any) -> float:
        try:
            return float(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"NY Fed SOFR value on {observed_at or 'unknown date'} is not numeric",
                retryable=False,
                provider="nyfed",
            ) from exc
