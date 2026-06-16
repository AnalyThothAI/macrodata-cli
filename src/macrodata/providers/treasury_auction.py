from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

TREASURY_AUCTION_QUERY_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
)


@dataclass(frozen=True)
class _AuctionMetricConfig:
    tenor: str
    security_type: str
    metric: str
    label: str
    unit: str
    parse_value: Callable[[dict[str, Any]], float]


def _metric_configs() -> dict[str, _AuctionMetricConfig]:
    configs: dict[str, _AuctionMetricConfig] = {}
    for prefix, tenor, security_type in (
        ("2y", "2-Year", "Note"),
        ("10y", "10-Year", "Note"),
        ("30y", "30-Year", "Bond"),
    ):
        configs[f"{prefix}_high_yield"] = _AuctionMetricConfig(
            tenor=tenor,
            security_type=security_type,
            metric="high_yield",
            label="high yield",
            unit="percent",
            parse_value=lambda row: _parse_number(row.get("high_yield")),
        )
        configs[f"{prefix}_bid_to_cover"] = _AuctionMetricConfig(
            tenor=tenor,
            security_type=security_type,
            metric="bid_to_cover_ratio",
            label="bid-to-cover",
            unit="ratio",
            parse_value=lambda row: _parse_number(row.get("bid_to_cover_ratio")),
        )
        configs[f"{prefix}_indirect_bidder_pct"] = _AuctionMetricConfig(
            tenor=tenor,
            security_type=security_type,
            metric="indirect_bidder_accepted_pct",
            label="indirect bidder accepted percentage",
            unit="percent",
            parse_value=_parse_indirect_bidder_pct,
        )
    return configs


class TreasuryAuctionProvider:
    provider_name = "treasury_auction"
    auction_query_url = TREASURY_AUCTION_QUERY_URL

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        config = self._config(dataset)
        rows = self._fetch_rows(
            config,
            params={
                "filter": _filter(config),
                "sort": "-auction_date",
                "page[size]": "25",
            },
        )
        observations = self._parse_observations(dataset=dataset, config=config, rows=rows)
        if observations:
            return observations[0]
        raise MacrodataError(
            code="no_data",
            message=f"Treasury auction returned no completed {config.tenor} {config.label} result",
            provider=self.provider_name,
            exit_code=4,
        )

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        config = self._config(dataset)
        rows = self._fetch_rows(
            config,
            params={
                "filter": f"{_filter(config)},auction_date:gte:{start},auction_date:lte:{end}",
                "sort": "auction_date",
                "page[size]": "10000",
            },
        )
        return self._parse_observations(dataset=dataset, config=config, rows=rows)

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("10y_bid_to_cover")
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
            sample_dataset="10y_bid_to_cover",
            sample_source_ts=latest.source_ts,
        )

    def _config(self, dataset: str) -> _AuctionMetricConfig:
        config = AUCTION_METRIC_CONFIGS.get(dataset)
        if config is not None:
            return config
        raise MacrodataError(
            code="unknown_series",
            message=f"Treasury auction dataset is not supported: {dataset}",
            provider=self.provider_name,
            exit_code=2,
        )

    def _fetch_rows(self, config: _AuctionMetricConfig, *, params: dict[str, str]) -> list[dict[str, Any]]:
        payload = self._http_client.get_json(self.auction_query_url, params=params, provider=self.provider_name)
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise MacrodataError(
                code="provider_parse_error",
                message="Treasury auction data must be a list",
                retryable=False,
                provider=self.provider_name,
            )
        parsed: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise MacrodataError(
                    code="provider_parse_error",
                    message=f"Treasury auction row {index} for {config.tenor} must be an object",
                    retryable=False,
                    provider=self.provider_name,
                )
            parsed.append(row)
        return parsed

    def _parse_observations(
        self,
        *,
        dataset: str,
        config: _AuctionMetricConfig,
        rows: list[dict[str, Any]],
    ) -> list[MacroObservation]:
        observations: list[MacroObservation] = []
        for row in rows:
            try:
                value = config.parse_value(row)
            except MacrodataError:
                continue
            observations.append(_observation(dataset=dataset, config=config, row=row, value=value))
        return sorted(observations, key=lambda observation: observation.observed_at, reverse=True)


def _filter(config: _AuctionMetricConfig) -> str:
    return f"security_type:eq:{config.security_type},security_term:eq:{config.tenor}"


def _observation(
    *,
    dataset: str,
    config: _AuctionMetricConfig,
    row: dict[str, Any],
    value: float,
) -> MacroObservation:
    observed_at = _parse_date(row.get("auction_date"), field="auction_date")
    record_date = _parse_date(row.get("record_date"), field="record_date")
    return MacroObservation(
        series_key=f"treasury_auction:{dataset}",
        provider="treasury_auction",
        dataset=dataset,
        observed_at=observed_at,
        value=value,
        unit=config.unit,
        frequency="event",
        source_ts=record_date,
        realtime_start=None,
        realtime_end=None,
        latency_class="event",
        data_quality="ok",
        provenance=[
            {
                "provider": "treasury_auction",
                "source_url": TREASURY_AUCTION_QUERY_URL,
                "security_type": _string(row.get("security_type")),
                "security_term": _string(row.get("security_term")),
                "cusip": _string(row.get("cusip")),
                "issue_date": _string(row.get("issue_date")),
                "maturity_date": _string(row.get("maturity_date")),
                "total_accepted": _string(row.get("total_accepted")),
                "total_tendered": _string(row.get("total_tendered")),
                "offering_amt": _string(row.get("offering_amt")),
            }
        ],
    )


def _parse_indirect_bidder_pct(row: dict[str, Any]) -> float:
    indirect = _parse_number(row.get("indirect_bidder_accepted"))
    total = _parse_number(row.get("total_accepted"))
    if total <= 0:
        raise MacrodataError(
            code="provider_parse_error",
            message="Treasury auction total_accepted must be positive for indirect bidder percentage",
            retryable=False,
            provider="treasury_auction",
        )
    return round((indirect / total) * 100.0, 6)


def _parse_number(raw_value: Any) -> float:
    value = _string(raw_value)
    if not value or value.lower() == "null":
        raise MacrodataError(
            code="provider_parse_error",
            message="Treasury auction metric is missing",
            retryable=False,
            provider="treasury_auction",
        )
    try:
        return float(value)
    except ValueError as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"Treasury auction metric is not numeric: {value}",
            retryable=False,
            provider="treasury_auction",
        ) from exc


def _parse_date(raw_value: Any, *, field: str) -> str:
    value = _string(raw_value)
    if not value:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"Treasury auction {field} is missing",
            retryable=False,
            provider="treasury_auction",
        )
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"Treasury auction {field} is invalid: {value}",
            retryable=False,
            provider="treasury_auction",
        ) from exc


def _string(raw_value: Any) -> str:
    return "" if raw_value is None else str(raw_value).strip()


AUCTION_METRIC_CONFIGS = _metric_configs()
