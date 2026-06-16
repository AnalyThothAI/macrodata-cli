# Catalog

Series keys use:

```text
<provider>:<dataset>
```

The provider segment is normalized to lowercase. The dataset segment is
provider-specific and case-sensitive where the upstream source is case-sensitive.

Examples:

- `fred:DGS10`
- `nyfed:SOFR`
- `yahoo:SPY`
- `cftc:financial_futures:sp500_net_noncommercial`
- `treasury_fiscal:operating_cash_balance`
- `treasury_auction:10y_bid_to_cover`
- `official_calendar:fomc_decision_next`

Use the catalog before fetching:

```bash
uv run macrodata catalog list
uv run macrodata catalog show fred:DGS10
```

## Provider Runtime Status

Current implemented providers:

- `fred`: Generic FRED series observations for cataloged datasets. Requires
  `FRED_API_KEY`.
- `nyfed`: NY Fed Markets SOFR, reverse repo, and standing repo observations.
  No API key.
- `treasury_fiscal`: Treasury Fiscal Daily Treasury Statement operating cash
  balance. No API key.
- `treasury_auction`: Treasury FiscalData auction query results for latest
  completed 2Y/10Y/30Y auction high yield, bid-to-cover, and indirect bidder
  accepted share. No API key.
- `yahoo`: Yahoo Finance daily adjusted price series through yfinance. No API
  key. yfinance is unofficial, not affiliated with Yahoo, and Yahoo API usage
  is intended for personal use.
- `cftc`: CFTC public Commitment of Traders positioning proxies. No API key.
- `official_calendar`: Fed FOMC and BEA release-date calendars normalized into
  next-event catalyst observations. No API key.

## Curated Catalog

| Series key | Name | Unit | Frequency | API key | Fetch status |
| --- | --- | --- | --- | --- | --- |
| `fred:DGS2` | 2-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:DGS5` | 5-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:DGS10` | 10-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:DGS30` | 30-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:T10Y2Y` | 10-Year Minus 2-Year Treasury Spread | percent | daily | yes | implemented |
| `fred:T10Y3M` | 10-Year Minus 3-Month Treasury Spread | percent | daily | yes | implemented |
| `fred:DFII10` | 10-Year Treasury Inflation-Indexed Security | percent | daily | yes | implemented |
| `fred:T10YIE` | 10-Year Breakeven Inflation Rate | percent | daily | yes | implemented |
| `fred:T5YIFR` | 5-Year, 5-Year Forward Inflation Expectation Rate | percent | daily | yes | implemented |
| `fred:DFEDTARU` | Federal Funds Target Range Upper Limit | percent | daily | yes | implemented |
| `fred:DFEDTARL` | Federal Funds Target Range Lower Limit | percent | daily | yes | implemented |
| `fred:EFFR` | Effective Federal Funds Rate | percent | daily | yes | implemented |
| `fred:IORB` | Interest Rate on Reserve Balances | percent | daily | yes | implemented |
| `fred:JTSJOL` | Job Openings: Total Nonfarm | thousands | monthly | yes | implemented |
| `fred:CES0500000003` | Average Hourly Earnings of All Employees, Total Private | dollars_per_hour | monthly | yes | implemented |
| `fred:WALCL` | Fed Total Assets | millions_usd | weekly | yes | implemented |
| `fred:WRBWFRBL` | Reserve Balances | millions_usd | weekly | yes | implemented |
| `fred:RRPONTSYD` | Overnight Reverse Repo | billions_usd | daily | yes | implemented |
| `fred:BAMLC0A0CM` | ICE BofA US Corporate OAS | percent | daily | yes | implemented |
| `fred:BAMLH0A0HYM2` | ICE BofA US High Yield OAS | percent | daily | yes | implemented |
| `fred:DRTSCILM` | SLOOS C&I Large/Middle-Market Tightening Standards | percent | quarterly | yes | implemented |
| `fred:DRTSCIS` | SLOOS C&I Small-Firm Tightening Standards | percent | quarterly | yes | implemented |
| `fred:DRSDCILM` | SLOOS C&I Large/Middle-Market Stronger Demand | percent | quarterly | yes | implemented |
| `fred:DRSDCIS` | SLOOS C&I Small-Firm Stronger Demand | percent | quarterly | yes | implemented |
| `fred:DRBLACBS` | Business Loan Delinquency Rate | percent | quarterly | yes | implemented |
| `fred:DRCLACBS` | Consumer Loan Delinquency Rate | percent | quarterly | yes | implemented |
| `fred:CORBLACBS` | Business Loan Charge-Off Rate | percent | quarterly | yes | implemented |
| `fred:CORCACBS` | Consumer Loan Charge-Off Rate | percent | quarterly | yes | implemented |
| `fred:VIXCLS` | CBOE VIX Close | index | daily | yes | implemented |
| `fred:SP500` | S&P 500 Index | index | daily | yes | implemented |
| `fred:DCOILWTICO` | WTI Crude Oil Price | usd_per_barrel | daily | yes | implemented |
| `fred:DTWEXBGS` | Nominal Broad US Dollar Index | index | daily | yes | implemented |
| `nyfed:SOFR` | Secured Overnight Financing Rate | percent | daily | no | implemented |
| `nyfed:RRP` | Overnight Reverse Repo Operations | millions_usd | daily | no | implemented |
| `nyfed:SRF` | Standing Repo Facility Operations | millions_usd | daily | no | implemented |
| `yahoo:SPY` | SPDR S&P 500 ETF Trust | price | daily | no | implemented |
| `yahoo:QQQ` | Invesco QQQ Trust | price | daily | no | implemented |
| `yahoo:IWM` | iShares Russell 2000 ETF | price | daily | no | implemented |
| `yahoo:TLT` | iShares 20+ Year Treasury Bond ETF | price | daily | no | implemented |
| `yahoo:HYG` | iShares iBoxx High Yield Corporate Bond ETF | price | daily | no | implemented |
| `yahoo:LQD` | iShares iBoxx Investment Grade Corporate Bond ETF | price | daily | no | implemented |
| `yahoo:GLD` | SPDR Gold Shares | price | daily | no | implemented |
| `yahoo:USO` | United States Oil Fund | price | daily | no | implemented |
| `yahoo:VIXY` | ProShares VIX Short-Term Futures ETF | price | daily | no | implemented |
| `yahoo:VIXM` | ProShares VIX Mid-Term Futures ETF | price | daily | no | implemented |
| `yahoo:DX-Y.NYB` | US Dollar Index | price | daily | no | implemented |
| `yahoo:BTC-USD` | Bitcoin USD | price | daily | no | implemented |
| `yahoo:ETH-USD` | Ether USD | price | daily | no | implemented |
| `cftc:financial_futures:sp500_net_noncommercial` | S&P 500 Net Noncommercial Positioning | contracts | weekly | no | implemented |
| `treasury_fiscal:operating_cash_balance` | Treasury Operating Cash Balance | millions_usd | daily | no | implemented |
| `official_calendar:fomc_decision_next` | Next FOMC Decision | days_until | event | no | implemented |
| `official_calendar:bea_gdp_next` | Next GDP Release | days_until | event | no | implemented |
| `official_calendar:bea_pce_next` | Next Personal Income and Outlays Release | days_until | event | no | implemented |
| `treasury_auction:2y_high_yield` | 2-Year Treasury Auction High Yield | percent | event | no | implemented |
| `treasury_auction:2y_bid_to_cover` | 2-Year Treasury Auction Bid-to-Cover | ratio | event | no | implemented |
| `treasury_auction:2y_indirect_bidder_pct` | 2-Year Treasury Auction Indirect Bidder Share | percent | event | no | implemented |
| `treasury_auction:10y_high_yield` | 10-Year Treasury Auction High Yield | percent | event | no | implemented |
| `treasury_auction:10y_bid_to_cover` | 10-Year Treasury Auction Bid-to-Cover | ratio | event | no | implemented |
| `treasury_auction:10y_indirect_bidder_pct` | 10-Year Treasury Auction Indirect Bidder Share | percent | event | no | implemented |
| `treasury_auction:30y_high_yield` | 30-Year Treasury Auction High Yield | percent | event | no | implemented |
| `treasury_auction:30y_bid_to_cover` | 30-Year Treasury Auction Bid-to-Cover | ratio | event | no | implemented |
| `treasury_auction:30y_indirect_bidder_pct` | 30-Year Treasury Auction Indirect Bidder Share | percent | event | no | implemented |

Yahoo Finance price series use yfinance daily history with adjusted daily close
as the canonical value. Intraday Yahoo series are not part of this catalog.

## Bundles

`rates-core` requests:

- `fred:DGS2`
- `fred:DGS10`
- `fred:DGS30`
- `fred:T10Y2Y`
- `fred:T10YIE`
- `fred:DFEDTARU`
- `fred:DFEDTARL`
- `fred:IORB`
- `nyfed:SOFR`

`liquidity-core` requests:

- `fred:WALCL`
- `fred:WRBWFRBL`
- `fred:RRPONTSYD`
- `nyfed:SOFR`
- `treasury_fiscal:operating_cash_balance`

`macro-core` requests all `liquidity-core` series plus:

- `fred:DGS2`
- `fred:DGS5`
- `fred:DGS10`
- `fred:DGS30`
- `fred:T10Y2Y`
- `fred:T10Y3M`
- `fred:DFII10`
- `fred:T10YIE`
- `fred:T5YIFR`
- `fred:DFEDTARU`
- `fred:DFEDTARL`
- `fred:EFFR`
- `fred:IORB`
- `fred:JTSJOL`
- `fred:CES0500000003`
- `fred:BAMLC0A0CM`
- `fred:BAMLH0A0HYM2`
- `fred:DRTSCILM`
- `fred:DRTSCIS`
- `fred:DRSDCILM`
- `fred:DRSDCIS`
- `fred:DRBLACBS`
- `fred:DRCLACBS`
- `fred:CORBLACBS`
- `fred:CORCACBS`
- `fred:VIXCLS`
- `fred:SP500`
- `fred:DCOILWTICO`
- `fred:DTWEXBGS`
- `yahoo:SPY`
- `yahoo:QQQ`
- `yahoo:IWM`
- `yahoo:TLT`
- `yahoo:HYG`
- `yahoo:LQD`
- `yahoo:GLD`
- `yahoo:USO`
- `yahoo:VIXY`
- `yahoo:VIXM`
- `yahoo:DX-Y.NYB`
- `yahoo:BTC-USD`
- `yahoo:ETH-USD`
- `cftc:financial_futures:sp500_net_noncommercial`

Bundles return `coverage`, `missing_series`, `series_errors`, and
`source_health` so agents can distinguish complete, partial, and unavailable
snapshots by provider. FRED source health may report redacted access modes such
as `api_key` or `public_csv`; API keys and environment values are never echoed.

`macro-calendar-core` requests next-event catalyst series only:

- `official_calendar:fomc_decision_next`
- `official_calendar:bea_gdp_next`
- `official_calendar:bea_pce_next`

Calendar observations use the event date as `observed_at`, `days_until` as
`value`, and event details in `provenance`. This bundle is separate from
`macro-core`; it is not numeric history for regime scoring.
BLS CPI, Employment Situation, and PPI calendar series are not in the catalog or
default bundle because the BLS schedule site returns HTTP 403 or hangs from this
runtime. Treat them as a source gap until a stable public API/feed is selected.

`treasury-auction-core` requests latest completed auction result event series:

- `treasury_auction:2y_high_yield`
- `treasury_auction:2y_bid_to_cover`
- `treasury_auction:2y_indirect_bidder_pct`
- `treasury_auction:10y_high_yield`
- `treasury_auction:10y_bid_to_cover`
- `treasury_auction:10y_indirect_bidder_pct`
- `treasury_auction:30y_high_yield`
- `treasury_auction:30y_bid_to_cover`
- `treasury_auction:30y_indirect_bidder_pct`

Auction observations use `auction_date` as `observed_at`, FiscalData
`record_date` as `source_ts`, and result metadata such as CUSIP, issue date,
total accepted, total tendered, and offering amount in `provenance`.
This bundle is separate from `macro-core`; it is not daily numeric history for
regime scoring. Auction tail remains a source gap until a reliable when-issued
yield source is implemented.
