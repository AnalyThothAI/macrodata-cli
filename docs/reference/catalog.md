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
- `treasury_fiscal:operating_cash_balance`

Use the catalog before fetching:

```bash
uv run macrodata catalog list
uv run macrodata catalog show fred:DGS10
```

## Current Providers

- `fred`: FRED series observations. Requires `FRED_API_KEY`.
- `nyfed`: NY Fed Markets SOFR. No API key.
- `treasury_fiscal`: Treasury Fiscal Daily Treasury Statement operating cash
  balance. No API key.

## Curated Catalog

| Series key | Name | Unit | Frequency | API key | Fetch status |
| --- | --- | --- | --- | --- | --- |
| `fred:DGS2` | 2-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:DGS10` | 10-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:DGS30` | 30-Year Treasury Constant Maturity Rate | percent | daily | yes | implemented |
| `fred:T10Y2Y` | 10-Year Minus 2-Year Treasury Spread | percent | daily | yes | implemented |
| `fred:T10YIE` | 10-Year Breakeven Inflation Rate | percent | daily | yes | implemented |
| `fred:DFEDTARU` | Federal Funds Target Range Upper Limit | percent | daily | yes | implemented |
| `fred:DFEDTARL` | Federal Funds Target Range Lower Limit | percent | daily | yes | implemented |
| `fred:IORB` | Interest Rate on Reserve Balances | percent | daily | yes | implemented |
| `fred:WALCL` | Fed Total Assets | millions_usd | weekly | yes | implemented |
| `fred:WRBWFRBL` | Reserve Balances | millions_usd | weekly | yes | implemented |
| `fred:RRPONTSYD` | Overnight Reverse Repo | billions_usd | daily | yes | implemented |
| `fred:BAMLC0A0CM` | ICE BofA US Corporate OAS | percent | daily | yes | implemented |
| `fred:BAMLH0A0HYM2` | ICE BofA US High Yield OAS | percent | daily | yes | implemented |
| `fred:VIXCLS` | CBOE VIX Close | index | daily | yes | implemented |
| `nyfed:SOFR` | Secured Overnight Financing Rate | percent | daily | no | implemented |
| `nyfed:RRP` | Overnight Reverse Repo Operations | millions_usd | daily | no | catalog metadata only |
| `nyfed:SRF` | Standing Repo Facility Operations | millions_usd | daily | no | catalog metadata only |
| `treasury_fiscal:operating_cash_balance` | Treasury Operating Cash Balance | millions_usd | daily | no | implemented |

`catalog metadata only` means the entry exists for source discovery and future
liquidity coverage, but the MVP provider does not fetch it yet.

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

Bundles return `coverage`, `missing_series`, and `series_errors` so agents can
distinguish complete, partial, and unavailable snapshots.
