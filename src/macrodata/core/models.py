from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DataQuality = Literal["ok", "stale", "partial", "unavailable"]


class MacroObservation(BaseModel):
    series_key: str
    provider: str
    dataset: str
    observed_at: str
    value: float | int | str | None
    unit: str | None
    frequency: str | None
    source_ts: str | None
    realtime_start: str | None
    realtime_end: str | None
    latency_class: str
    data_quality: DataQuality
    provenance: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def idempotency_key(self) -> str:
        return f"{self.series_key}:{self.observed_at}"


class SourceCatalogEntry(BaseModel):
    series_key: str
    name: str
    provider: str
    dataset: str
    description: str
    unit: str | None
    frequency: str | None
    latency_class: str
    requires_api_key: bool
    source_url: str
    license_note: str


class ProviderSmokeResult(BaseModel):
    provider: str
    ok: bool
    latency_ms: int
    checked_at: str
    sample_dataset: str | None = None
    sample_source_ts: str | None = None
    error_code: str | None = None
    message: str | None = None


class BundleSnapshot(BaseModel):
    bundle: str
    asof: str
    observations: list[MacroObservation]
    coverage: dict[str, int]
    missing_series: list[str]
    source_chain: list[str]
    data_quality: DataQuality
    reason_codes: list[str]
