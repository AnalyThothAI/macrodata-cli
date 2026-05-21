# Macrodata CLI Design

Date: 2026-05-21

Repository: `AnalyThothAI/macrodata-cli`

Remote: `https://github.com/AnalyThothAI/macrodata-cli`

## Purpose

`macrodata-cli` is an independent Python package that gives AI coding agents,
research agents, and human operators a deterministic interface to public macro
and cross-asset data sources. It is a data access plane, not a research report
writer and not a trading signal engine.

The first consumer is `gmgn-twitter-intel`, but the package must remain usable
from other repositories through:

- a terminal command: `macrodata`
- a Python SDK: `macrodata.client.MacrodataClient`
- an MCP stdio server: `macrodata mcp serve`

## Design Principles

1. Agent-first output.
   Every operational command returns one JSON object to stdout by default.
   Human-readable output is allowed only through an explicit `--format pretty`
   option. Errors are JSON too.

2. Evidence before analysis.
   The package fetches observations, source status, provenance, freshness, and
   bundle snapshots. It does not produce market recommendations.

3. Source transparency.
   Every returned value carries source id, dataset id, source timestamp, observed
   timestamp, units, frequency, latency class, data quality, and provenance.

4. Thin surfaces, shared use cases.
   CLI, SDK, and MCP must call the same application services. The CLI cannot
   contain provider logic.

5. Read-only by default.
   MVP commands fetch data and optionally write local run artifacts only when an
   output path is explicitly provided. There is no database writer in the MVP.

6. Small provider contracts.
   Providers implement narrow protocols for series, latest observations, and
   smoke checks. Gateway behavior owns timeout, retry, rate limit, and envelope
   normalization.

## Non-Goals For MVP

- No paid Bloomberg, Refinitiv, Markit, Haver, or CME data access.
- No persistent database schema.
- No dashboard frontend.
- No LLM-generated macro analysis.
- No portfolio advice, order execution, or alerting.
- No hidden use of unofficial browser sessions for data sources.

## First Data Scope

The MVP focuses on public macro sources needed for rates and liquidity work:

| Provider | Use | Example datasets |
| --- | --- | --- |
| FRED | rates, credit, volatility proxies | `DGS2`, `DGS10`, `T10YIE`, `BAMLC0A0CM`, `BAMLH0A0HYM2`, `VIXCLS`, `WALCL`, `WRBWFRBL` |
| NY Fed Markets | secured funding and liquidity plumbing | SOFR latest/range, RRP, SRF, secured rates |
| Treasury Fiscal Data | TGA and daily treasury statement items | operating cash balance, deposits, withdrawals |

Second wave providers are CFTC COT, OFR stress indexes, Stooq market bars,
CoinGecko crypto prices, and SEC EDGAR metadata.

## Command Surface

All commands emit a single result envelope.

```bash
macrodata doctor
macrodata catalog list
macrodata catalog show fred:DGS10
macrodata source smoke --provider fred
macrodata fetch latest fred:DGS10
macrodata fetch series fred:DGS10 --start 2024-01-01 --end 2026-05-21
macrodata bundle rates-core --asof 2026-05-21
macrodata bundle liquidity-core --asof 2026-05-21
macrodata explain fred:DGS10
macrodata mcp serve
```

Global options:

```bash
--format json|pretty
--config /path/to/config.toml
--timeout-sec 10
--cache-dir /path/to/cache
--no-cache
```

JSON remains the default format.

## Result Envelope

Successful command:

```json
{
  "ok": true,
  "command": "fetch.series",
  "request_id": "01J...",
  "asof": "2026-05-21T00:00:00Z",
  "data": {
    "series_key": "fred:DGS10",
    "observations": []
  },
  "meta": {
    "source_chain": ["fred"],
    "cache": "miss",
    "latency_ms": 184,
    "data_quality": "ok",
    "reason_codes": []
  }
}
```

Failed command:

```json
{
  "ok": false,
  "command": "fetch.series",
  "request_id": "01J...",
  "error": {
    "code": "provider_timeout",
    "message": "FRED request timed out after 10.0 seconds",
    "retryable": true,
    "provider": "fred"
  },
  "meta": {
    "source_chain": ["fred"],
    "cache": "none",
    "latency_ms": 10001,
    "data_quality": "unavailable",
    "reason_codes": ["timeout"]
  }
}
```

Exit codes:

- `0`: success
- `2`: invalid input or config
- `3`: provider failure
- `4`: no data for a valid request
- `5`: internal invariant failure

## Domain Model

`SeriesKey`

- string format: `<provider>:<dataset>`
- examples: `fred:DGS10`, `nyfed:SOFR`, `treasury_fiscal:operating_cash_balance`

`MacroObservation`

- `series_key`
- `provider`
- `dataset`
- `observed_at`
- `value`
- `unit`
- `frequency`
- `source_ts`
- `realtime_start`
- `realtime_end`
- `latency_class`
- `data_quality`
- `provenance`
- `idempotency_key`

`SourceCatalogEntry`

- `series_key`
- `name`
- `provider`
- `dataset`
- `description`
- `unit`
- `frequency`
- `latency_class`
- `requires_api_key`
- `source_url`
- `license_note`

`ProviderSmokeResult`

- `provider`
- `ok`
- `latency_ms`
- `checked_at`
- `sample_dataset`
- `sample_source_ts`
- `error_code`
- `message`

`BundleSnapshot`

- `bundle`
- `asof`
- `observations`
- `coverage`
- `missing_series`
- `source_chain`
- `data_quality`
- `reason_codes`

## Bundles

`rates-core`

- `fred:DGS2`
- `fred:DGS10`
- `fred:DGS30`
- `fred:T10Y2Y`
- `fred:T10YIE`
- `fred:DFEDTARU`
- `fred:DFEDTARL`
- `fred:IORB`
- `nyfed:SOFR`

`liquidity-core`

- `fred:WALCL`
- `fred:WRBWFRBL`
- `fred:RRPONTSYD`
- `nyfed:SOFR`
- `nyfed:RRP`
- `nyfed:SRF`
- `treasury_fiscal:operating_cash_balance`

Bundles return raw observations plus coverage metadata. Scoring stays outside
the MVP.

## Provider Gateway

The gateway owns:

- source key parsing
- catalog lookup
- timeout handling
- retry on retryable provider errors
- in-process rate limiting
- optional on-disk HTTP cache
- result envelope normalization
- provenance normalization

Provider implementations own only source-specific URL construction and response
parsing.

## Configuration

Default config search order:

1. `--config`
2. `MACRODATA_CONFIG`
3. `~/.macrodata/config.toml`
4. built-in defaults

Environment variable overrides:

- `FRED_API_KEY`
- `MACRODATA_CACHE_DIR`
- `MACRODATA_TIMEOUT_SEC`

Secrets are never printed. `doctor` reports booleans and paths only.

## Agent Integration

The repository ships an `AGENTS.md` file that tells coding agents:

- commands are read-only unless `--output-dir` is passed
- JSON is the canonical interface
- stdout contains one JSON object
- stderr is reserved for process diagnostics
- provider credentials must not be printed
- MCP server is started with `macrodata mcp serve`

The MCP server exposes these tools:

- `doctor`
- `catalog_list`
- `catalog_show`
- `source_smoke`
- `fetch_latest`
- `fetch_series`
- `bundle_rates_core`
- `bundle_liquidity_core`
- `explain_series`

Tool outputs use Pydantic models so the MCP Python SDK can expose structured
content and schemas.

## Error Handling

Provider errors are mapped to stable error codes:

- `invalid_series_key`
- `unknown_series`
- `missing_api_key`
- `provider_timeout`
- `provider_rate_limited`
- `provider_http_error`
- `provider_parse_error`
- `no_data`
- `internal_error`

Each error includes `retryable`, `provider`, and `message`.

## Testing Strategy

Unit tests:

- result envelope serialization
- series key parsing
- catalog lookup
- provider response parsing
- bundle coverage logic

CLI tests:

- command returns one JSON object
- invalid input returns exit code `2`
- provider failure returns structured JSON error
- `--format pretty` does not change command behavior

Provider tests:

- use mocked HTTP responses
- no live API calls in default test suite
- live tests are opt-in with `--run-live`

MCP tests:

- instantiate server in-process
- call each tool through the MCP client
- assert structured content shape

## Documentation

Initial docs:

- `README.md`: quickstart, CLI examples, config, agent usage
- `AGENTS.md`: agent instructions
- `docs/reference/result-envelope.md`
- `docs/reference/catalog.md`
- `docs/reference/mcp-tools.md`

## Implementation Phases

Phase 1 creates package foundation, core models, catalog, FRED provider, CLI, and
tests.

Phase 2 adds NY Fed and Treasury Fiscal providers plus `rates-core` and
`liquidity-core` bundles.

Phase 3 adds MCP stdio server and agent docs.

Phase 4 adds optional providers and downstream integration examples.

The MVP is complete when an agent can run:

```bash
macrodata bundle rates-core --asof 2026-05-21
```

and receive one schema-stable JSON object containing source-attributed
observations.
