from __future__ import annotations

import pytest

from macrodata.catalog.registry import CatalogRegistry, default_catalog
from macrodata.core.errors import ValidationError


def test_default_catalog_contains_rates_core_series() -> None:
    catalog = default_catalog()

    keys = {entry.series_key for entry in catalog.list_entries()}
    assert "fred:DGS10" in keys
    assert "nyfed:SOFR" in keys
    assert "treasury_fiscal:operating_cash_balance" in keys


def test_catalog_contains_macro_core_series() -> None:
    catalog = default_catalog()
    keys = {entry.series_key for entry in catalog.list_entries()}

    assert {
        "fred:DGS5",
        "fred:T10Y3M",
        "fred:DFII10",
        "fred:T5YIFR",
        "fred:EFFR",
        "fred:SP500",
        "fred:DCOILWTICO",
        "fred:DTWEXBGS",
        "stooq:spy.us",
        "stooq:hyg.us",
        "cftc:financial_futures:sp500_net_noncommercial",
    }.issubset(keys)


def test_catalog_show_known_series() -> None:
    catalog = default_catalog()

    entry = catalog.get("fred:DGS10")

    assert entry.provider == "fred"
    assert entry.dataset == "DGS10"
    assert entry.frequency == "daily"


def test_catalog_pins_rrp_fred_unit_as_billions() -> None:
    catalog = default_catalog()

    entry = catalog.get("fred:RRPONTSYD")

    assert entry.unit == "billions_usd"


def test_catalog_unknown_series_raises_validation_error() -> None:
    catalog = CatalogRegistry(entries=[])

    with pytest.raises(ValidationError) as exc:
        catalog.get("fred:UNKNOWN")

    assert exc.value.code == "unknown_series"
