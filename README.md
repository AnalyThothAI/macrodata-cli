# macrodata-cli

Agent-friendly public macro data CLI, Python SDK, and MCP server.

`macrodata-cli` gives coding and research agents a small, typed, read-only
surface for public macro data. The CLI is JSON-first, the MCP server exposes the
same application services, and provider responses are normalized into stable
result envelopes with provenance, freshness, and data-quality metadata.

## Quickstart

```bash
uv sync
uv run macrodata doctor
uv run macrodata catalog list
export FRED_API_KEY="..."
uv run macrodata fetch series fred:DGS10 --start 2026-05-20 --end 2026-05-20
uv run macrodata bundle rates-core --asof 2026-05-21
uv run macrodata bundle liquidity-core --asof 2026-05-21
uv run macrodata bundle macro-core --asof 2026-05-21
uv run macrodata mcp serve
```

Every normal CLI command emits one JSON object to stdout by default. Use
`--format pretty` only for human inspection:

```bash
uv run macrodata catalog show fred:DGS10 --format pretty
```

`macrodata mcp serve` is the server command: it starts the stdio MCP server
instead of printing a one-shot result envelope.

## Credentials

FRED requests require a FRED API key. Provide it through the environment:

```bash
export FRED_API_KEY="..."
uv run macrodata source smoke --provider fred
```

Most CLI commands that touch FRED also accept `--fred-api-key`, but the
environment variable is preferred for agent use. Secrets are never printed; the
`doctor` command only reports whether a FRED key is configured.

NY Fed Markets SOFR, Treasury Fiscal Daily Treasury Statement operating cash
balance, Yahoo Finance daily prices, and CFTC Commitment of Traders data are
public sources and do not require an API key.

## Providers

Current public providers:

- `fred`: FRED time series, including rates, Fed balance sheet, credit-spread,
  and volatility proxy series. Requires `FRED_API_KEY`.
- `nyfed`: NY Fed Markets SOFR endpoint. No API key.
- `treasury_fiscal`: Treasury Fiscal Data Daily Treasury Statement operating
  cash balance. No API key.
- `yahoo`: Yahoo Finance daily adjusted price series through yfinance. No API
  key. yfinance is unofficial, not affiliated with Yahoo, and Yahoo API usage
  is intended for personal use.
- `cftc`: CFTC public Commitment of Traders positioning proxies. No API key.

The catalog also contains liquidity-oriented NY Fed `RRP` and `SRF` metadata for
source discovery. The implemented NY Fed fetch path is `nyfed:SOFR`.

## CLI Commands

```bash
uv run macrodata doctor
uv run macrodata catalog list
uv run macrodata catalog show fred:DGS10
uv run macrodata source smoke --provider fred
uv run macrodata source smoke --provider nyfed
uv run macrodata source smoke --provider treasury_fiscal
uv run macrodata source smoke --provider yahoo
uv run macrodata source smoke --provider cftc
uv run macrodata fetch series fred:DGS10 --start 2026-05-20 --end 2026-05-20
uv run macrodata fetch series yahoo:SPY --start 2026-05-20 --end 2026-05-21
uv run macrodata bundle rates-core --asof 2026-05-21
uv run macrodata bundle liquidity-core --asof 2026-05-21
uv run macrodata bundle macro-core --asof 2026-05-21
uv run macrodata bundle fetch rates-core --asof 2026-05-21
uv run macrodata bundle history macro-core --start 2026-05-01 --end 2026-05-21
uv run macrodata mcp serve
```

The bundle commands return partial diagnostics instead of hiding missing source
data. For example, running `rates-core` without `FRED_API_KEY` can still return
NY Fed SOFR while reporting missing FRED series in `series_errors`.

MVP bundles fetch latest available observations; `asof` is a caller
label/snapshot date, not a historical cutoff. Use each observation's
`observed_at` / `source_ts` for freshness.

`source smoke` has two layers of status: top-level `ok:true` means the command
executed and returned a JSON envelope, while provider health is reported in
`data.result.ok`. Agents should inspect `data.result.ok`, `error_code`, and
`message`.

## MCP

Start the MCP server with:

```bash
uv run macrodata mcp serve
```

Current MCP tools:

- `doctor`
- `catalog_list`
- `catalog_show`
- `fetch_series`
- `fetch_latest`
- `bundle_rates_core`
- `bundle_liquidity_core`
- `bundle_macro_core`
- `bundle_macro_core_history`

MCP tools return the same structured result envelope used by the CLI. FRED
credentials are read from `FRED_API_KEY`; MCP tools do not accept API keys as
arguments.

## Reference

- [Result envelope](docs/reference/result-envelope.md)
- [Catalog](docs/reference/catalog.md)
- [MCP tools](docs/reference/mcp-tools.md)

## Development

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src tests
```
