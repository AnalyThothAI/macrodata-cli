# MCP Tools

Start the stdio MCP server with:

```bash
uv run macrodata mcp serve
```

The server name is `macrodata`. Tools are read-only. Catalog and doctor tools
are local. Fetch and bundle tools may make network requests to public providers.

FRED credentials are read from `FRED_API_KEY`. MCP tools do not accept API keys
as arguments and must not echo secrets.

All tools return the same result envelope described in
[result-envelope.md](result-envelope.md).

## Tools

### `doctor`

Return package health and redacted credential availability.

Input:

```json
{}
```

Output command: `doctor`

### `catalog_list`

List curated macro series.

Input:

```json
{}
```

Output command: `catalog.list`

### `catalog_show`

Show catalog metadata for one series.

Input:

```json
{"series_key": "fred:DGS10"}
```

Output command: `catalog.show`

### `fetch_series`

Fetch a bounded date range for one series.

Input:

```json
{
  "series_key": "fred:DGS10",
  "start": "2026-05-20",
  "end": "2026-05-20"
}
```

Output command: `fetch.series`

### `fetch_latest`

Fetch the latest available observation for one series.

Input:

```json
{"series_key": "nyfed:SOFR"}
```

Output command: `fetch.latest`

### `bundle_rates_core`

Fetch the curated rates snapshot.

MVP bundles fetch latest available observations; `asof` is a caller
label/snapshot date, not a historical cutoff. Use each observation's
`observed_at` / `source_ts` for freshness.

Input:

```json
{"asof": "2026-05-21"}
```

Output command: `bundle.rates-core`

### `bundle_liquidity_core`

Fetch the curated liquidity snapshot.

MVP bundles fetch latest available observations; `asof` is a caller
label/snapshot date, not a historical cutoff. Use each observation's
`observed_at` / `source_ts` for freshness.

Input:

```json
{"asof": "2026-05-21"}
```

Output command: `bundle.liquidity-core`

## Agent Recommendations

1. Call `doctor` first.
2. Call `catalog_list` or `catalog_show` before selecting a series.
3. Prefer `fetch_latest` for latest-point questions.
4. Prefer `fetch_series` for date-bounded analysis.
5. Prefer `bundle_rates_core` and `bundle_liquidity_core` when an agent needs a
   compact macro context packet rather than isolated series.
