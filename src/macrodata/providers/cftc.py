from __future__ import annotations

import csv
import re
from datetime import UTC, date, datetime
from io import StringIO
from typing import Any

import httpx

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

SUPPORTED_DATASET = "financial_futures:sp500_net_noncommercial"
CFTC_MARKET_INDEX = 0
CFTC_REPORT_DATE_INDEX = 2
CFTC_LEGACY_CONTRACT_CODE_INDEX = 3
CFTC_LEGACY_NONCOMMERCIAL_LONG_INDEX = 8
CFTC_LEGACY_NONCOMMERCIAL_SHORT_INDEX = 9
CFTC_MIN_HEADERLESS_COLUMNS = 10
CFTC_SP500_CONSOLIDATED_CONTRACT_CODE = "13874+"
CFTC_SP500_CONSOLIDATED_MARKET_PREFIX = "S&P 500 CONSOLIDATED -"


class CftcProvider:
    provider_name = "cftc"
    financial_futures_url = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(
                code="provider_unavailable",
                message=f"CFTC returned no usable data for {dataset}",
                retryable=True,
                provider="cftc",
            )
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        self._ensure_supported_dataset(dataset)
        start_date = self._parse_query_date("start", start)
        end_date = self._parse_query_date("end", end)
        rows = self._parse_rows(self._get_text())
        observations = [
            observation
            for observation in (self._parse_row(row) for row in rows if self._is_sp500_market(row))
            if start_date <= date.fromisoformat(observation.observed_at) <= end_date
        ]
        return sorted(observations, key=lambda observation: observation.observed_at)

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest(SUPPORTED_DATASET)
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider="cftc",
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider="cftc",
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset=SUPPORTED_DATASET,
            sample_source_ts=latest.source_ts,
        )

    def _ensure_supported_dataset(self, dataset: str) -> None:
        if dataset == SUPPORTED_DATASET:
            return
        raise MacrodataError(
            code="unknown_series",
            message=f"CFTC dataset is not supported: {dataset}",
            provider="cftc",
            exit_code=2,
        )

    def _get_text(self) -> str:
        try:
            with httpx.Client(timeout=self._http_client.timeout_sec) as client:
                response = client.get(self.financial_futures_url)
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
            raise MacrodataError(
                code="provider_unavailable",
                message="CFTC financial futures source is unavailable",
                retryable=True,
                provider="cftc",
            ) from exc
        return response.text

    def _parse_rows(self, text: str) -> list[dict[str, str]]:
        try:
            csv_rows = list(csv.reader(StringIO(text)))
        except csv.Error as exc:
            raise self._parse_error("CFTC financial futures response could not be parsed") from exc
        if not csv_rows:
            raise MacrodataError(
                code="provider_unavailable",
                message="CFTC financial futures response is empty",
                retryable=True,
                provider="cftc",
            )

        first_row = csv_rows[0]
        normalized_header = [_normalize_column(column) for column in first_row]
        required_columns = {"reportdateasyyyymmdd", "marketandexchangenames"}
        if required_columns.issubset(normalized_header):
            return self._parse_headered_rows(header=first_row, data_rows=csv_rows[1:])
        return [self._parse_headerless_row(row) for row in csv_rows]

    def _parse_headered_rows(self, *, header: list[str], data_rows: list[list[str]]) -> list[dict[str, str]]:
        normalized_rows: list[dict[str, str]] = []
        normalized_header = [_normalize_column(column) for column in header]
        for data_row in data_rows:
            normalized_rows.append(dict(zip(normalized_header, data_row, strict=False)))
        return normalized_rows

    def _parse_headerless_row(self, row: list[str]) -> dict[str, str]:
        if len(row) < CFTC_MIN_HEADERLESS_COLUMNS:
            raise self._parse_error("CFTC financial futures response is missing required legacy columns")
        return {
            "marketandexchangenames": row[CFTC_MARKET_INDEX],
            "reportdateasyyyymmdd": row[CFTC_REPORT_DATE_INDEX],
            "cftccontractmarketcode": row[CFTC_LEGACY_CONTRACT_CODE_INDEX],
            "noncommpositionslongall": row[CFTC_LEGACY_NONCOMMERCIAL_LONG_INDEX],
            "noncommpositionsshortall": row[CFTC_LEGACY_NONCOMMERCIAL_SHORT_INDEX],
        }

    def _parse_row(self, row: dict[str, str]) -> MacroObservation:
        observed_at = self._parse_observed_at(row.get("reportdateasyyyymmdd"))
        long_value = self._parse_contracts(
            observed_at=observed_at,
            raw_value=_first_present(row, "noncommpositionslongall", "noncommerciallongall"),
            side="long",
        )
        short_value = self._parse_contracts(
            observed_at=observed_at,
            raw_value=_first_present(row, "noncommpositionsshortall", "noncommercialshortall"),
            side="short",
        )
        return MacroObservation(
            series_key=f"cftc:{SUPPORTED_DATASET}",
            provider="cftc",
            dataset=SUPPORTED_DATASET,
            observed_at=observed_at,
            value=long_value - short_value,
            unit="contracts",
            frequency="weekly",
            source_ts=observed_at,
            realtime_start=None,
            realtime_end=None,
            latency_class="weekly",
            data_quality="ok",
            provenance=[{"provider": "cftc", "source_url": self.financial_futures_url}],
        )

    def _is_sp500_market(self, row: dict[str, str]) -> bool:
        contract_code = row.get("cftccontractmarketcode", "").strip()
        if contract_code == CFTC_SP500_CONSOLIDATED_CONTRACT_CODE:
            return True
        market = row.get("marketandexchangenames", "").strip().upper()
        return market.startswith(CFTC_SP500_CONSOLIDATED_MARKET_PREFIX)

    def _parse_query_date(self, name: str, raw_value: str) -> date:
        try:
            return date.fromisoformat(raw_value)
        except ValueError as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"CFTC {name} date is invalid: {raw_value}",
                retryable=False,
                provider="cftc",
            ) from exc

    def _parse_observed_at(self, raw_value: Any) -> str:
        observed_at = "" if raw_value is None else str(raw_value).strip()
        if not observed_at:
            raise self._parse_error("CFTC financial futures report date is missing")
        try:
            return date.fromisoformat(observed_at).isoformat()
        except ValueError as exc:
            raise self._parse_error(f"CFTC financial futures report date is invalid: {observed_at}") from exc

    def _parse_contracts(self, *, observed_at: str, raw_value: Any, side: str) -> float:
        try:
            return float(str(raw_value).replace(",", ""))
        except (TypeError, ValueError) as exc:
            raise self._parse_error(f"CFTC noncommercial {side} contracts on {observed_at} are not numeric") from exc

    def _parse_error(self, message: str) -> MacrodataError:
        return MacrodataError(
            code="provider_parse_error",
            message=message,
            retryable=False,
            provider="cftc",
        )


def _normalize_column(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _first_present(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return value
    return None
