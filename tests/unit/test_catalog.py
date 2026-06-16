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


def test_catalog_contains_nyfed_repo_depth_series() -> None:
    catalog = default_catalog()

    expected = {
        "nyfed:BGCR": ("Broad General Collateral Rate", "percent"),
        "nyfed:TGCR": ("Tri-Party General Collateral Rate", "percent"),
        "nyfed:SOFR_VOLUME": ("SOFR Underlying Volume", "millions_usd"),
        "nyfed:BGCR_VOLUME": ("BGCR Underlying Volume", "millions_usd"),
        "nyfed:TGCR_VOLUME": ("TGCR Underlying Volume", "millions_usd"),
    }
    for series_key, (name, unit) in expected.items():
        entry = catalog.get(series_key)
        assert entry.provider == "nyfed"
        assert entry.name == name
        assert entry.unit == unit
        assert entry.frequency == "daily"
        assert entry.requires_api_key is False


def test_catalog_contains_nyfed_unsecured_funding_series() -> None:
    catalog = default_catalog()

    expected = {
        "nyfed:EFFR": ("Effective Federal Funds Rate", "percent"),
        "nyfed:OBFR": ("Overnight Bank Funding Rate", "percent"),
        "nyfed:EFFR_VOLUME": ("EFFR Underlying Volume", "millions_usd"),
        "nyfed:OBFR_VOLUME": ("OBFR Underlying Volume", "millions_usd"),
    }
    for series_key, (name, unit) in expected.items():
        entry = catalog.get(series_key)
        assert entry.provider == "nyfed"
        assert entry.name == name
        assert entry.unit == unit
        assert entry.frequency == "daily"
        assert entry.requires_api_key is False


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
        "nyfed:BGCR",
        "nyfed:TGCR",
        "nyfed:SOFR_VOLUME",
        "nyfed:BGCR_VOLUME",
        "nyfed:TGCR_VOLUME",
        "nyfed:EFFR",
        "nyfed:OBFR",
        "nyfed:EFFR_VOLUME",
        "nyfed:OBFR_VOLUME",
        "fred:MICH",
        "fred:GDP",
        "fred:GDPC1",
        "fred:GDPNOW",
        "fred:PAYEMS",
        "fred:UNRATE",
        "fred:ICSA",
        "fred:JTSJOL",
        "fred:CES0500000003",
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


def test_catalog_contains_gdpnow_nowcast_series() -> None:
    catalog = default_catalog()
    gdpnow = catalog.get("fred:GDPNOW")

    assert gdpnow.name == "GDPNow"
    assert gdpnow.provider == "fred"
    assert gdpnow.dataset == "GDPNOW"
    assert gdpnow.unit == "percent_saar"
    assert "Atlanta Fed" in gdpnow.description


def test_catalog_contains_official_calendar_event_series() -> None:
    catalog = default_catalog()
    keys = {entry.series_key for entry in catalog.list_entries()}

    fomc = catalog.get("official_calendar:fomc_decision_next")
    gdp = catalog.get("official_calendar:bea_gdp_next")
    pce = catalog.get("official_calendar:bea_pce_next")
    cpi = catalog.get("official_calendar:bls_cpi_next")
    employment = catalog.get("official_calendar:bls_employment_next")
    ppi = catalog.get("official_calendar:bls_ppi_next")

    assert fomc.provider == "official_calendar"
    assert fomc.unit == "days_until"
    assert fomc.frequency == "event"
    assert fomc.requires_api_key is False
    assert fomc.source_url == "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    assert "FOMC" in fomc.description
    assert gdp.source_url == "https://apps.bea.gov/API/signup/release_dates.json"
    assert pce.provider == "official_calendar"
    assert cpi.source_url == "https://www.bls.gov/schedule/news_release/cpi.htm"
    assert employment.source_url == "https://www.bls.gov/schedule/news_release/empsit.htm"
    assert ppi.source_url == "https://www.bls.gov/schedule/news_release/ppi.htm"
    assert "official_calendar:bls_cpi_next" in keys
    assert "official_calendar:bls_employment_next" in keys
    assert "official_calendar:bls_ppi_next" in keys


def test_catalog_contains_official_fed_text_series_without_legacy_page_aliases() -> None:
    catalog = default_catalog()
    keys = {entry.series_key for entry in catalog.list_entries()}

    statement = catalog.get("official_fed_text:fomc_statement_latest")
    minutes = catalog.get("official_fed_text:fomc_minutes_latest")
    speech = catalog.get("official_fed_text:speech_latest")

    assert {
        "official_fed_text:fomc_statement_latest",
        "official_fed_text:fomc_minutes_latest",
        "official_fed_text:monetary_policy_press_release_latest",
        "official_fed_text:speech_latest",
    }.issubset(keys)
    assert statement.provider == "official_fed_text"
    assert statement.unit == "document"
    assert statement.frequency == "event"
    assert statement.requires_api_key is False
    assert statement.source_url == "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    assert "FOMC statement" in statement.description
    assert minutes.source_url == "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    assert speech.source_url == "https://www.federalreserve.gov/feeds/speeches.xml"
    assert "official_fed_text:fed_page_latest" not in keys
    assert "official_fed_text:fomc_statement_page" not in keys


def test_catalog_contains_treasury_auction_result_series() -> None:
    catalog = default_catalog()
    keys = {entry.series_key for entry in catalog.list_entries()}

    two_year_next = catalog.get("treasury_auction:2y_next_auction_days")
    ten_year_bid_to_cover = catalog.get("treasury_auction:10y_bid_to_cover")
    thirty_year_indirect = catalog.get("treasury_auction:30y_indirect_bidder_pct")

    assert {
        "treasury_auction:2y_next_auction_days",
        "treasury_auction:10y_next_auction_days",
        "treasury_auction:30y_next_auction_days",
        "treasury_auction:2y_high_yield",
        "treasury_auction:2y_bid_to_cover",
        "treasury_auction:2y_indirect_bidder_pct",
        "treasury_auction:10y_high_yield",
        "treasury_auction:10y_bid_to_cover",
        "treasury_auction:10y_indirect_bidder_pct",
        "treasury_auction:30y_high_yield",
        "treasury_auction:30y_bid_to_cover",
        "treasury_auction:30y_indirect_bidder_pct",
    }.issubset(keys)
    assert two_year_next.provider == "treasury_auction"
    assert two_year_next.unit == "days_until"
    assert two_year_next.frequency == "event"
    assert two_year_next.requires_api_key is False
    assert two_year_next.source_url == "https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.xml"
    assert "next official 2-year" in two_year_next.description.lower()
    assert ten_year_bid_to_cover.provider == "treasury_auction"
    assert ten_year_bid_to_cover.unit == "ratio"
    assert ten_year_bid_to_cover.frequency == "event"
    assert ten_year_bid_to_cover.requires_api_key is False
    assert ten_year_bid_to_cover.source_url == (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
    )
    assert "bid-to-cover" in ten_year_bid_to_cover.description
    assert thirty_year_indirect.unit == "percent"
    assert "indirect bidder" in thirty_year_indirect.description


def test_catalog_documents_public_macro_terminal_proxies() -> None:
    catalog = default_catalog()

    vix_3m = catalog.get("fred:VXVCLS")
    vix_1d = catalog.get("cboe:VIX1D")
    vix_9d = catalog.get("cboe:VIX9D")
    vvix = catalog.get("cboe:VVIX")
    skew = catalog.get("cboe:SKEW")
    bbb_oas = catalog.get("fred:BAMLC0A4CBBB")
    jobless_claims = catalog.get("fred:ICSA")
    credit_proxy = catalog.get("yahoo:JNK")
    move_proxy = catalog.get("yahoo:^MOVE")
    vix_mid_term_proxy = catalog.get("yahoo:VIXM")

    assert vix_3m.name == "CBOE S&P 500 3-Month Volatility Index"
    assert vix_3m.unit == "index"
    assert vix_3m.frequency == "daily"
    assert "term structure" in vix_3m.description
    assert vix_1d.name == "Cboe 1-Day Volatility Index"
    assert vix_1d.provider == "cboe"
    assert vix_1d.dataset == "VIX1D"
    assert vix_1d.source_url == "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX1D_History.csv"
    assert "one-day" in vix_1d.description
    assert vix_9d.name == "Cboe 9-Day Volatility Index"
    assert vix_9d.provider == "cboe"
    assert vix_9d.dataset == "VIX9D"
    assert vix_9d.source_url == "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv"
    assert "short-horizon" in vix_9d.description
    assert vvix.name == "Cboe VIX of VIX Index"
    assert vvix.provider == "cboe"
    assert vvix.dataset == "VVIX"
    assert vvix.source_url == "https://cdn.cboe.com/api/global/us_indices/daily_prices/VVIX_History.csv"
    assert skew.name == "Cboe SKEW Index"
    assert skew.provider == "cboe"
    assert skew.dataset == "SKEW"
    assert "tail risk" in skew.description
    assert bbb_oas.unit == "percent"
    assert bbb_oas.frequency == "daily"
    assert "BBB" in bbb_oas.name
    assert jobless_claims.frequency == "weekly"
    assert credit_proxy.provider == "yahoo"
    assert credit_proxy.dataset == "JNK"
    assert move_proxy.name == "ICE BofA MOVE Index"
    assert move_proxy.provider == "yahoo"
    assert move_proxy.dataset == "^MOVE"
    assert "rates volatility" in move_proxy.description
    assert "unofficial library" in move_proxy.license_note
    assert vix_mid_term_proxy.name == "ProShares VIX Mid-Term Futures ETF"
    assert vix_mid_term_proxy.provider == "yahoo"
    assert vix_mid_term_proxy.dataset == "VIXM"
    assert "Mid-term VIX futures" in vix_mid_term_proxy.description


def test_catalog_contains_sloos_credit_supply_and_demand_series() -> None:
    catalog = default_catalog()

    large_standards = catalog.get("fred:DRTSCILM")
    small_standards = catalog.get("fred:DRTSCIS")
    large_demand = catalog.get("fred:DRSDCILM")
    small_demand = catalog.get("fred:DRSDCIS")

    assert large_standards.frequency == "quarterly"
    assert large_standards.unit == "percent"
    assert "Large and Middle-Market" in large_standards.name
    assert "tightening standards" in large_standards.description
    assert small_standards.frequency == "quarterly"
    assert "Small Firms" in small_standards.name
    assert "stronger demand" in large_demand.description
    assert small_demand.unit == "percent"


def test_catalog_contains_loan_quality_credit_series() -> None:
    catalog = default_catalog()

    business_delinquency = catalog.get("fred:DRBLACBS")
    consumer_delinquency = catalog.get("fred:DRCLACBS")
    business_charge_off = catalog.get("fred:CORBLACBS")
    consumer_charge_off = catalog.get("fred:CORCACBS")

    assert business_delinquency.frequency == "quarterly"
    assert business_delinquency.unit == "percent"
    assert business_delinquency.name == "Delinquency Rate on Business Loans, All Commercial Banks"
    assert "loan quality" in business_delinquency.description
    assert consumer_delinquency.name == "Delinquency Rate on Consumer Loans, All Commercial Banks"
    assert business_charge_off.frequency == "quarterly"
    assert "charge-off" in business_charge_off.description
    assert consumer_charge_off.unit == "percent"


def test_catalog_contains_average_hourly_earnings_labor_series() -> None:
    catalog = default_catalog()

    wages = catalog.get("fred:CES0500000003")

    assert wages.name == "Average Hourly Earnings of All Employees, Total Private"
    assert wages.frequency == "monthly"
    assert wages.unit == "dollars_per_hour"
    assert "wage pressure" in wages.description


def test_catalog_contains_timsun_asset_coverage_extensions() -> None:
    catalog = default_catalog()
    keys = {entry.series_key for entry in catalog.list_entries()}

    assert {
        "yahoo:^GSPC",
        "yahoo:^NDX",
        "yahoo:^DJI",
        "yahoo:^RUT",
        "yahoo:SI=F",
        "yahoo:NG=F",
        "yahoo:HG=F",
        "yahoo:SMH",
        "yahoo:SOXX",
        "yahoo:GBPUSD=X",
        "yahoo:USDCNY=X",
        "yahoo:USDKRW=X",
    }.issubset(keys)
    assert catalog.get("yahoo:^GSPC").name == "S&P 500 Index"
    assert catalog.get("yahoo:USDCNY=X").description == "US dollar to Chinese yuan spot FX proxy."


def test_catalog_documents_nyfed_srf_results_endpoint() -> None:
    catalog = default_catalog()

    assert catalog.get("nyfed:SRF").source_url == "https://markets.newyorkfed.org/api/rp/results/search.json"


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
