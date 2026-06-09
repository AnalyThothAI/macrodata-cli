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
- `yahoo`: Yahoo Finance daily adjusted price series through yfinance. No API
  key. yfinance is unofficial, not affiliated with Yahoo, and Yahoo API usage
  is intended for personal use.
- `cftc`: CFTC public Commitment of Traders positioning proxies. No API key.

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
| `fred:WALCL` | Fed Total Assets | millions_usd | weekly | yes | implemented |
| `fred:WRBWFRBL` | Reserve Balances | millions_usd | weekly | yes | implemented |
| `fred:RRPONTSYD` | Overnight Reverse Repo | billions_usd | daily | yes | implemented |
| `fred:BAMLC0A0CM` | ICE BofA US Corporate OAS | percent | daily | yes | implemented |
| `fred:BAMLH0A0HYM2` | ICE BofA US High Yield OAS | percent | daily | yes | implemented |
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
| `yahoo:DX-Y.NYB` | US Dollar Index | price | daily | no | implemented |
| `yahoo:BTC-USD` | Bitcoin USD | price | daily | no | implemented |
| `yahoo:ETH-USD` | Ether USD | price | daily | no | implemented |
| `cftc:financial_futures:sp500_net_noncommercial` | S&P 500 Net Noncommercial Positioning | contracts | weekly | no | implemented |
| `treasury_fiscal:operating_cash_balance` | Treasury Operating Cash Balance | millions_usd | daily | no | implemented |

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
- `fred:BAMLC0A0CM`
- `fred:BAMLH0A0HYM2`
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
- `yahoo:DX-Y.NYB`
- `yahoo:BTC-USD`
- `yahoo:ETH-USD`
- `cftc:financial_futures:sp500_net_noncommercial`

Bundles return `coverage`, `missing_series`, and `series_errors` so agents can
distinguish complete, partial, and unavailable snapshots.
