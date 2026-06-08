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
        "fred:DFF",
        "fred:FEDFUNDS",
        "fred:DGS3MO",
        "fred:DGS5",
        "fred:DGS7",
        "fred:DGS20",
        "fred:T10Y3M",
        "fred:DFII5",
        "fred:DFII10",
        "fred:DFII30",
        "fred:T5YIE",
        "fred:T5YIFR",
        "fred:EFFR",
        "fred:MICH",
        "fred:GDP",
        "fred:GDPC1",
        "fred:PAYEMS",
        "fred:UNRATE",
        "fred:ICSA",
        "fred:JTSJOL",
        "fred:CPIAUCSL",
        "fred:CPILFESL",
        "fred:PCEPI",
        "fred:PCEPILFE",
        "fred:RSAFS",
        "fred:INDPRO",
        "fred:HOUST",
        "fred:UMCSENT",
        "fred:PSAVERT",
        "fred:VXVCLS",
        "fred:VXNCLS",
        "fred:BAMLC0A4CBBB",
        "fred:BAMLH0A1HYBB",
        "fred:BAMLH0A2HYB",
        "fred:BAMLH0A3HYC",
        "fred:STLFSI4",
        "fred:NFCI",
        "fred:SP500",
        "fred:NASDAQCOM",
        "fred:DCOILWTICO",
        "fred:DCOILBRENTEU",
        "fred:DHHNGSP",
        "fred:DTWEXBGS",
        "fred:DEXUSEU",
        "fred:DEXJPUS",
        "fred:DEXCHUS",
        "fred:DEXUSUK",
        "yahoo:SPY",
        "yahoo:DIA",
        "yahoo:EFA",
        "yahoo:EEM",
        "yahoo:SHY",
        "yahoo:IEF",
        "yahoo:TIP",
        "yahoo:BND",
        "yahoo:HYG",
        "yahoo:JNK",
        "yahoo:SLV",
        "yahoo:UNG",
        "yahoo:CPER",
        "yahoo:UUP",
        "yahoo:FXE",
        "yahoo:FXY",
        "yahoo:BTC-USD",
        "cftc:financial_futures:sp500_net_noncommercial",
    }.issubset(keys)
    assert "stooq:spy.us" not in keys
    assert "fred:WILL5000INDFC" not in keys


def test_catalog_documents_public_macro_terminal_proxies() -> None:
    catalog = default_catalog()

    vix_3m = catalog.get("fred:VXVCLS")
    bbb_oas = catalog.get("fred:BAMLC0A4CBBB")
    jobless_claims = catalog.get("fred:ICSA")
    credit_proxy = catalog.get("yahoo:JNK")

    assert vix_3m.name == "CBOE S&P 500 3-Month Volatility Index"
    assert vix_3m.unit == "index"
    assert vix_3m.frequency == "daily"
    assert "term structure" in vix_3m.description
    assert bbb_oas.unit == "percent"
    assert bbb_oas.frequency == "daily"
    assert "BBB" in bbb_oas.name
    assert jobless_claims.frequency == "weekly"
    assert credit_proxy.provider == "yahoo"
    assert credit_proxy.dataset == "JNK"


def test_yahoo_catalog_entry_documents_unofficial_personal_use_provenance() -> None:
    catalog = default_catalog()

    entry = catalog.get("yahoo:SPY")

    assert entry.provider == "yahoo"
    assert entry.dataset == "SPY"
    assert entry.unit == "price"
    assert entry.frequency == "daily"
    assert entry.source_url == "https://finance.yahoo.com/quote/SPY"
    assert "Yahoo Finance" in entry.license_note
    assert "unofficial" in entry.license_note
    assert "personal use" in entry.license_note


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


def test_fred_catalog_entries_do_not_require_api_keys() -> None:
    catalog = default_catalog()

    entry = catalog.get("fred:DGS10")

    assert entry.requires_api_key is False
    assert "API key is optional" in entry.license_note


def test_catalog_unknown_series_raises_validation_error() -> None:
    catalog = CatalogRegistry(entries=[])

    with pytest.raises(ValidationError) as exc:
        catalog.get("fred:UNKNOWN")

    assert exc.value.code == "unknown_series"
