from __future__ import annotations

from dataclasses import dataclass

from macrodata.core.errors import ValidationError


@dataclass(frozen=True)
class SeriesKey:
    provider: str
    dataset: str

    @property
    def value(self) -> str:
        return f"{self.provider}:{self.dataset}"


def parse_series_key(value: str) -> SeriesKey:
    normalized = value.strip()
    if ":" not in normalized:
        raise ValidationError(code="invalid_series_key", message="series key must use '<provider>:<dataset>'")
    provider, dataset = normalized.split(":", 1)
    provider = provider.strip().lower()
    dataset = dataset.strip()
    if not provider or not dataset:
        raise ValidationError(code="invalid_series_key", message="provider and dataset are required")
    return SeriesKey(provider=provider, dataset=dataset)
