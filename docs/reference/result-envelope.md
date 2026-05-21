# Result Envelope

Normal CLI commands and MCP tools return one structured result envelope. CLI
commands write exactly one JSON object to stdout by default. `--format pretty`
prints the same object with indentation for humans.

`macrodata mcp serve` is the server command and speaks MCP over stdio instead of
printing a one-shot JSON envelope.

## Success Shape

```json
{
  "ok": true,
  "command": "fetch.series",
  "request_id": "uuid",
  "asof": "2026-05-21T00:00:00Z",
  "data": {},
  "meta": {
    "source_chain": ["fred"],
    "cache": "none",
    "latency_ms": 123,
    "data_quality": "ok",
    "reason_codes": []
  }
}
```

Fields:

- `ok`: `true` for successful command handling.
- `command`: stable command identifier such as `doctor`, `catalog.list`,
  `fetch.series`, `bundle.rates-core`, or `fetch.latest`.
- `request_id`: generated UUID for this command call.
- `asof`: UTC timestamp when the envelope was created.
- `data`: command-specific payload.
- `meta.source_chain`: providers or local components used.
- `meta.cache`: current cache state. The MVP emits `none`.
- `meta.latency_ms`: elapsed command time in milliseconds.
- `meta.data_quality`: one of `ok`, `stale`, `partial`, or `unavailable`.
- `meta.reason_codes`: machine-readable quality or error reasons.

## Failure Shape

```json
{
  "ok": false,
  "command": "fetch.series",
  "request_id": "uuid",
  "asof": "2026-05-21T00:00:00Z",
  "error": {
    "code": "missing_api_key",
    "message": "FRED_API_KEY is required",
    "retryable": false,
    "provider": "fred"
  },
  "meta": {
    "source_chain": ["fred"],
    "cache": "none",
    "latency_ms": 3,
    "data_quality": "unavailable",
    "reason_codes": ["missing_api_key"]
  }
}
```

Error fields:

- `error.code`: stable machine code, for example `missing_api_key`,
  `unknown_series`, `unknown_provider`, `unknown_bundle`, `no_data`,
  `provider_timeout`, `provider_http_error`, `provider_invalid_request`,
  `provider_request_error`, or `provider_parse_error`.
- `error.message`: sanitized diagnostic text. It must not contain secrets.
- `error.retryable`: whether retrying later may help.
- `error.provider`: provider associated with the failure when known.

## Common Data Payloads

`doctor`:

```json
{
  "package": "macrodata-cli",
  "version": "0.1.0",
  "fred_api_key_configured": true
}
```

`catalog.list`:

```json
{
  "entries": [
    {
      "series_key": "fred:DGS10",
      "provider": "fred",
      "dataset": "DGS10"
    }
  ]
}
```

`fetch.series`:

```json
{
  "series_key": "fred:DGS10",
  "observations": [
    {
      "series_key": "fred:DGS10",
      "provider": "fred",
      "dataset": "DGS10",
      "observed_at": "2026-05-20",
      "value": 4.0,
      "unit": "percent",
      "frequency": "daily",
      "source_ts": "2026-05-20",
      "latency_class": "eod",
      "data_quality": "ok",
      "idempotency_key": "fred:DGS10:2026-05-20"
    }
  ]
}
```

`bundle.*`:

```json
{
  "snapshot": {
    "bundle": "rates-core",
    "asof": "2026-05-21",
    "coverage": {"requested": 9, "available": 9},
    "missing_series": [],
    "series_errors": [],
    "source_chain": ["fred", "nyfed"],
    "data_quality": "ok",
    "reason_codes": []
  }
}
```
