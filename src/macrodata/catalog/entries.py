from __future__ import annotations

from macrodata.core.models import SourceCatalogEntry


def _fred(dataset: str, name: str, description: str, unit: str | None, frequency: str | None) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        series_key=f"fred:{dataset}",
        name=name,
        provider="fred",
        dataset=dataset,
        description=description,
        unit=unit,
        frequency=frequency,
        latency_class="eod",
        requires_api_key=False,
        source_url=f"https://fred.stlouisfed.org/series/{dataset}",
        license_note=(
            "FRED terms and upstream source terms apply; "
            "API key is optional because the public CSV endpoint is supported."
        ),
    )


def _stooq(symbol: str, name: str, description: str) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        series_key=f"stooq:{symbol}",
        name=name,
        provider="stooq",
        dataset=symbol,
        description=description,
        unit="price",
        frequency="daily",
        latency_class="eod",
        requires_api_key=False,
        source_url=f"https://stooq.com/q/d/l/?s={symbol}&i=d",
        license_note="Stooq public data terms apply.",
    )


def _cftc(dataset: str, name: str, description: str) -> SourceCatalogEntry:
    return SourceCatalogEntry(
        series_key=f"cftc:{dataset}",
        name=name,
        provider="cftc",
        dataset=dataset,
        description=description,
        unit="contracts",
        frequency="weekly",
        latency_class="weekly",
        requires_api_key=False,
        source_url="https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm",
        license_note="CFTC public data terms apply.",
    )


CATALOG_ENTRIES: list[SourceCatalogEntry] = [
    _fred("DGS2", "2-Year Treasury Constant Maturity Rate", "US 2-year Treasury yield.", "percent", "daily"),
    _fred("DGS5", "5-Year Treasury Constant Maturity Rate", "US 5-year Treasury yield.", "percent", "daily"),
    _fred("DGS10", "10-Year Treasury Constant Maturity Rate", "US 10-year Treasury yield.", "percent", "daily"),
    _fred("DGS30", "30-Year Treasury Constant Maturity Rate", "US 30-year Treasury yield.", "percent", "daily"),
    _fred("T10Y2Y", "10-Year Minus 2-Year Treasury Spread", "Treasury curve slope.", "percent", "daily"),
    _fred(
        "T10Y3M",
        "10-Year Minus 3-Month Treasury Spread",
        "Treasury recession-risk curve slope.",
        "percent",
        "daily",
    ),
    _fred("DFII10", "10-Year Treasury Inflation-Indexed Security", "US 10-year real yield.", "percent", "daily"),
    _fred("T10YIE", "10-Year Breakeven Inflation Rate", "Market implied inflation compensation.", "percent", "daily"),
    _fred(
        "T5YIFR",
        "5-Year, 5-Year Forward Inflation Expectation Rate",
        "Forward inflation expectation proxy.",
        "percent",
        "daily",
    ),
    _fred("DFEDTARU", "Federal Funds Target Range Upper Limit", "Fed target range upper bound.", "percent", "daily"),
    _fred("DFEDTARL", "Federal Funds Target Range Lower Limit", "Fed target range lower bound.", "percent", "daily"),
    _fred("EFFR", "Effective Federal Funds Rate", "Effective overnight federal funds rate.", "percent", "daily"),
    _fred("IORB", "Interest Rate on Reserve Balances", "Fed administered reserve rate.", "percent", "daily"),
    _fred("WALCL", "Fed Total Assets", "Federal Reserve balance sheet total assets.", "millions_usd", "weekly"),
    _fred("WRBWFRBL", "Reserve Balances", "Reserve balances with Federal Reserve Banks.", "millions_usd", "weekly"),
    _fred("RRPONTSYD", "Overnight Reverse Repo", "Overnight reverse repurchase agreements.", "billions_usd", "daily"),
    _fred("BAMLC0A0CM", "ICE BofA US Corporate OAS", "Investment-grade corporate OAS proxy.", "percent", "daily"),
    _fred("BAMLH0A0HYM2", "ICE BofA US High Yield OAS", "High-yield OAS proxy.", "percent", "daily"),
    _fred("VIXCLS", "CBOE VIX Close", "Equity volatility proxy.", "index", "daily"),
    _fred("SP500", "S&P 500 Index", "US large-cap equity index level.", "index", "daily"),
    _fred(
        "DCOILWTICO",
        "WTI Crude Oil Price",
        "West Texas Intermediate crude oil spot price.",
        "usd_per_barrel",
        "daily",
    ),
    _fred(
        "DTWEXBGS",
        "Nominal Broad US Dollar Index",
        "Trade-weighted US dollar broad goods and services index.",
        "index",
        "daily",
    ),
    _stooq("spy.us", "SPDR S&P 500 ETF Trust", "S&P 500 ETF price proxy."),
    _stooq("qqq.us", "Invesco QQQ Trust", "Nasdaq 100 ETF price proxy."),
    _stooq("iwm.us", "iShares Russell 2000 ETF", "US small-cap ETF price proxy."),
    _stooq("tlt.us", "iShares 20+ Year Treasury Bond ETF", "Long-duration Treasury ETF price proxy."),
    _stooq("hyg.us", "iShares iBoxx High Yield Corporate Bond ETF", "High-yield credit ETF price proxy."),
    _stooq("lqd.us", "iShares iBoxx Investment Grade Corporate Bond ETF", "Investment-grade credit ETF price proxy."),
    _stooq("gld.us", "SPDR Gold Shares", "Gold ETF price proxy."),
    _stooq("uso.us", "United States Oil Fund", "Oil ETF price proxy."),
    _cftc(
        "financial_futures:sp500_net_noncommercial",
        "S&P 500 Net Noncommercial Positioning",
        "CFTC financial futures net noncommercial positioning for S&P 500 futures.",
    ),
    SourceCatalogEntry(
        series_key="nyfed:SOFR",
        name="Secured Overnight Financing Rate",
        provider="nyfed",
        dataset="SOFR",
        description="SOFR from NY Fed Markets API.",
        unit="percent",
        frequency="daily",
        latency_class="daily",
        requires_api_key=False,
        source_url="https://markets.newyorkfed.org/api/rates/secured/sofr/search.json",
        license_note="NY Fed public data terms apply.",
    ),
    SourceCatalogEntry(
        series_key="nyfed:RRP",
        name="Overnight Reverse Repo Operations",
        provider="nyfed",
        dataset="RRP",
        description="NY Fed overnight reverse repo operation usage.",
        unit="millions_usd",
        frequency="daily",
        latency_class="daily",
        requires_api_key=False,
        source_url="https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json",
        license_note="NY Fed public data terms apply.",
    ),
    SourceCatalogEntry(
        series_key="nyfed:SRF",
        name="Standing Repo Facility Operations",
        provider="nyfed",
        dataset="SRF",
        description="NY Fed standing repo facility usage.",
        unit="millions_usd",
        frequency="daily",
        latency_class="daily",
        requires_api_key=False,
        source_url="https://markets.newyorkfed.org/api/rp/srf/propositions/search.json",
        license_note="NY Fed public data terms apply.",
    ),
    SourceCatalogEntry(
        series_key="treasury_fiscal:operating_cash_balance",
        name="Treasury Operating Cash Balance",
        provider="treasury_fiscal",
        dataset="operating_cash_balance",
        description="Treasury General Account proxy from Daily Treasury Statement.",
        unit="millions_usd",
        frequency="daily",
        latency_class="daily",
        requires_api_key=False,
        source_url="https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance",
        license_note="US Treasury Fiscal Data public data terms apply.",
    ),
]
