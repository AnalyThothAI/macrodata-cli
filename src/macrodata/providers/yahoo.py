from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import yfinance as yf  # type: ignore[import-untyped]

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult

YAHOO_LICENSE_NOTE = (
    "Yahoo Finance data is accessed through yfinance, an unofficial library not affiliated with Yahoo; "
    "Yahoo API usage is intended for personal use."
)


class YahooPriceProvider:
    provider_name = "yahoo"

    def __init__(self, *, timeout_sec: float = 10.0) -> None:
        self._timeout_sec = timeout_sec

    def get_latest(self, dataset: str) -> MacroObservation:
        end = datetime.now(UTC).date() + timedelta(days=1)
        start = end - timedelta(days=14)
        observations = self.get_range(dataset, start=start.isoformat(), end=end.isoformat())
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        try:
            history = yf.Ticker(dataset).history(
                start=start,
                end=end,
                interval="1d",
                auto_adjust=True,
                repair=False,
                timeout=self._timeout_sec,
                raise_errors=True,
            )
        except Exception as exc:
            raise MacrodataError(
                code="provider_request_error",
                message=f"yahoo request failed for {dataset}: {type(exc).__name__}",
                retryable=True,
                provider="yahoo",
            ) from exc

        if history.empty:
            raise MacrodataError(
                code="no_data",
                message=f"Yahoo Finance returned no daily history for {dataset}",
                provider="yahoo",
                exit_code=4,
            )

        observations = [
            self._parse_row(dataset=dataset, index_value=index_value, row=row)
            for index_value, row in history.iterrows()
        ]
        return sorted(observations, key=lambda observation: observation.observed_at)

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("SPY")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider="yahoo",
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider="yahoo",
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="SPY",
            sample_source_ts=latest.source_ts,
        )

    def _parse_row(self, *, dataset: str, index_value: Any, row: Any) -> MacroObservation:
        observed_at = self._parse_observed_at(dataset=dataset, raw_value=index_value)
        value = self._parse_close(dataset=dataset, observed_at=observed_at, raw_value=row["Close"])
        return MacroObservation(
            series_key=f"yahoo:{dataset}",
            provider="yahoo",
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
            provenance=[
                {
                    "provider": "yahoo",
                    "upstream": "Yahoo Finance",
                    "source_url": f"https://finance.yahoo.com/quote/{dataset}",
                    "license_note": YAHOO_LICENSE_NOTE,
                }
            ],
        )

    def _parse_observed_at(self, *, dataset: str, raw_value: Any) -> str:
        if isinstance(raw_value, datetime):
            return raw_value.date().isoformat()
        if isinstance(raw_value, date):
            return raw_value.isoformat()
        if hasattr(raw_value, "date"):
            parsed_date = raw_value.date()
            if isinstance(parsed_date, date):
                return parsed_date.isoformat()
        raw_text = str(raw_value).strip()
        if not raw_text:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Yahoo Finance date for {dataset} is missing",
                retryable=False,
                provider="yahoo",
            )
        try:
            return date.fromisoformat(raw_text[:10]).isoformat()
        except ValueError as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Yahoo Finance date for {dataset} is invalid: {raw_text}",
                retryable=False,
                provider="yahoo",
            ) from exc

    def _parse_close(self, *, dataset: str, observed_at: str, raw_value: Any) -> float:
        try:
            return float(raw_value)
        except (TypeError, ValueError) as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Yahoo Finance close for {dataset} at {observed_at} is invalid",
                retryable=False,
                provider="yahoo",
            ) from exc
