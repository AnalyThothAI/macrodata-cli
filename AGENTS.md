# AGENTS.md

`macrodata-cli` is a read-only public macro data tool for coding and research
agents. It exposes a JSON-first CLI and a stdio MCP server. Commands may make
network requests to public data providers, but they do not mutate remote state.

## Agent Usage Rules

- Prefer the default JSON output. Use `--format pretty` only when a human needs
  to inspect output.
- Treat stdout from normal CLI commands as one complete JSON object.
- Treat stderr as process diagnostics, not data.
- Do not print API keys, config secrets, or environment variable values.
- Use `macrodata doctor` before debugging provider failures.
- Use `macrodata catalog list` before guessing a series key.
- Use `macrodata catalog show <provider>:<dataset>` before fetching unfamiliar
  series.
- Use `macrodata source smoke --provider <provider>` to check provider health.
- Use `macrodata fetch series <series_key> --start <YYYY-MM-DD> --end <YYYY-MM-DD>`
  for bounded CLI fetches.
- Use MCP `fetch_latest` when an agent needs latest observations; the CLI
  currently exposes bounded `fetch series`, while latest fetch is available
  through the application service and MCP.
- Use `macrodata bundle rates-core --asof <YYYY-MM-DD>` or
  `macrodata bundle liquidity-core --asof <YYYY-MM-DD>` for curated snapshots.
- MVP bundles fetch latest available observations; `asof` is a caller
  label/snapshot date, not a historical cutoff. Use each observation's
  `observed_at` / `source_ts` for freshness.
- For `source smoke`, top-level `ok:true` means the command executed. Provider
  health is `data.result.ok`; inspect `data.result.ok`, `error_code`, and
  `message`.
- Use `macrodata mcp serve` when an MCP-compatible agent needs tools.

## Credentials

- FRED requires `FRED_API_KEY`.
- Prefer `FRED_API_KEY` in the environment over passing `--fred-api-key`.
- Secrets must never be copied into logs, docs, issues, or agent summaries.
- `doctor` reports only `fred_api_key_configured`; it never prints the key.
- NY Fed Markets SOFR and Treasury Fiscal DTS operating cash balance are public
  sources and require no API key.

## Recommended Command Flow

```bash
uv run macrodata doctor
uv run macrodata catalog list
uv run macrodata catalog show fred:DGS10
uv run macrodata source smoke --provider fred
uv run macrodata fetch series fred:DGS10 --start 2026-05-20 --end 2026-05-20
uv run macrodata bundle rates-core --asof 2026-05-21
uv run macrodata bundle liquidity-core --asof 2026-05-21
uv run macrodata mcp serve
```

## Current Providers

- `fred`: implemented for curated FRED catalog entries; requires
  `FRED_API_KEY`.
- `nyfed`: implemented for `nyfed:SOFR`; no API key.
- `treasury_fiscal`: implemented for
  `treasury_fiscal:operating_cash_balance`; no API key.

The catalog contains `nyfed:RRP` and `nyfed:SRF` metadata for future liquidity
coverage. Do not assume they are fetchable until provider support is added.

## Verification

Run the project gates before reporting completion:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src tests
```
