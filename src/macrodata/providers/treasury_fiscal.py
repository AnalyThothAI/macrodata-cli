from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class TreasuryFiscalProvider:
    provider_name = "treasury_fiscal"
    operating_cash_balance_url = (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
    )

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(
                code="no_data",
                message=f"Treasury Fiscal returned no data for {dataset}",
                provider="treasury_fiscal",
                exit_code=4,
            )
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        if dataset != "operating_cash_balance":
            raise MacrodataError(
                code="unknown_series",
                message=f"Treasury Fiscal dataset is not supported: {dataset}",
                provider="treasury_fiscal",
                exit_code=2,
            )
        payload = self._http_client.get_json(
            self.operating_cash_balance_url,
            params={
                "filter": f"record_date:gte:{start},record_date:lte:{end}",
                "sort": "record_date",
                "page[size]": "10000",
            },
            provider="treasury_fiscal",
        )
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise MacrodataError(
                code="provider_parse_error",
                message="Treasury Fiscal data must be a list",
                provider="treasury_fiscal",
            )
        observations: list[MacroObservation] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise MacrodataError(
                    code="provider_parse_error",
                    message=f"Treasury Fiscal data row {index} for operating_cash_balance must be an object",
                    provider="treasury_fiscal",
                )
            observations.append(self._parse_row(row))
        return sorted(observations, key=lambda observation: observation.observed_at)

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("operating_cash_balance")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider="treasury_fiscal",
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider="treasury_fiscal",
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="operating_cash_balance",
            sample_source_ts=latest.source_ts,
        )

    def _parse_row(self, row: dict[str, Any]) -> MacroObservation:
        observed_at = self._parse_record_date(row.get("record_date"))
        value = self._parse_close_today_bal(observed_at=observed_at, raw_value=row.get("close_today_bal"))
        return MacroObservation(
            series_key="treasury_fiscal:operating_cash_balance",
            provider="treasury_fiscal",
            dataset="operating_cash_balance",
            observed_at=observed_at,
            value=value,
            unit="millions_usd",
            frequency="daily",
            source_ts=observed_at,
            realtime_start=None,
            realtime_end=None,
            latency_class="daily",
            data_quality="ok",
            provenance=[{"provider": "treasury_fiscal", "source_url": self.operating_cash_balance_url}],
        )

    def _parse_record_date(self, raw_value: Any) -> str:
        observed_at = "" if raw_value is None else str(raw_value).strip()
        if not observed_at:
            raise MacrodataError(
                code="provider_parse_error",
                message="Treasury Fiscal operating_cash_balance record_date is missing",
                retryable=False,
                provider="treasury_fiscal",
            )
        try:
            return date.fromisoformat(observed_at).isoformat()
        except ValueError as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"Treasury Fiscal operating_cash_balance record_date is invalid: {observed_at}",
                retryable=False,
                provider="treasury_fiscal",
            ) from exc

    def _parse_close_today_bal(self, *, observed_at: str, raw_value: Any) -> float:
        try:
            return float(str(raw_value))
        except (TypeError, ValueError) as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=(
                    f"Treasury Fiscal operating_cash_balance value on {observed_at or 'unknown date'} is not numeric"
                ),
                retryable=False,
                provider="treasury_fiscal",
            ) from exc
