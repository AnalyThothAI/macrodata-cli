# Macrodata CLI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent `macrodata-cli` package that exposes public macro data through a JSON-first CLI, Python SDK, and MCP stdio server.

**Architecture:** The package uses a clean core/application/infrastructure split. CLI, SDK, and MCP surfaces call the same application services; providers stay behind narrow protocols; all command results are normalized into a stable envelope.

**Tech Stack:** Python 3.12+, Typer, Pydantic v2, httpx, tenacity, platformdirs, pytest, respx, MCP Python SDK.

---

## File Structure

- Create: `pyproject.toml` - package metadata, dependencies, script entrypoint, test/lint config.
- Create: `README.md` - quickstart, CLI examples, config, agent usage.
- Create: `AGENTS.md` - repository instructions for coding agents.
- Create: `src/macrodata/__init__.py` - package version export.
- Create: `src/macrodata/__main__.py` - `python -m macrodata` entrypoint.
- Create: `src/macrodata/core/errors.py` - stable exception hierarchy and error codes.
- Create: `src/macrodata/core/models.py` - Pydantic domain models.
- Create: `src/macrodata/core/series_key.py` - parse and validate `<provider>:<dataset>`.
- Create: `src/macrodata/core/envelope.py` - result envelope helpers.
- Create: `src/macrodata/catalog/entries.py` - curated public macro catalog.
- Create: `src/macrodata/catalog/registry.py` - catalog lookup service.
- Create: `src/macrodata/providers/contracts.py` - provider protocols.
- Create: `src/macrodata/providers/fred.py` - FRED series provider.
- Create: `src/macrodata/providers/nyfed.py` - NY Fed Markets provider for SOFR, RRP, and SRF observations.
- Create: `src/macrodata/providers/treasury_fiscal.py` - Treasury Fiscal Data provider for operating cash balance observations.
- Create: `src/macrodata/gateway/http_client.py` - shared HTTP client wrapper.
- Create: `src/macrodata/gateway/macrodata_gateway.py` - provider routing and envelope normalization.
- Create: `src/macrodata/app/runtime.py` - build catalog, HTTP client, providers, and gateway.
- Create: `src/macrodata/app/services.py` - application use cases.
- Create: `src/macrodata/client.py` - public Python SDK.
- Create: `src/macrodata/surfaces/cli.py` - Typer CLI.
- Create: `src/macrodata/surfaces/mcp_server.py` - MCP stdio server.
- Create: `tests/unit/` - pure model/catalog/bundle tests.
- Create: `tests/provider/` - mocked HTTP provider tests.
- Create: `tests/cli/` - Typer command tests.
- Create: `tests/mcp/` - in-process MCP tool tests.
- Create: `docs/reference/result-envelope.md` - result envelope contract.
- Create: `docs/reference/catalog.md` - curated catalog reference.
- Create: `docs/reference/mcp-tools.md` - MCP tool contract.

## Task 1: Package Foundation

**Files:**
- Create: `pyproject.toml`
- Create: `src/macrodata/__init__.py`
- Create: `src/macrodata/__main__.py`
- Create: `src/macrodata/surfaces/cli.py`
- Create: `tests/cli/test_cli_foundation.py`

- [ ] **Step 1: Write the failing CLI foundation test**

Create `tests/cli/test_cli_foundation.py`:

```python
from __future__ import annotations

import json

from typer.testing import CliRunner

from macrodata.surfaces.cli import app


def test_doctor_returns_json_envelope() -> None:
    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["data"]["package"] == "macrodata-cli"
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/cli/test_cli_foundation.py -q
```

Expected: import failure for `macrodata.surfaces.cli`.

- [ ] **Step 3: Add package metadata**

Create `pyproject.toml`:

```toml
[project]
name = "macrodata-cli"
version = "0.1.0"
description = "Agent-friendly macro data CLI, SDK, and MCP server."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.27.0",
    "mcp>=1.12.4",
    "platformdirs>=4.3.0",
    "pydantic>=2.8.0",
    "tenacity>=9.0.0",
    "typer>=0.21.1",
]

[dependency-groups]
dev = [
    "pytest>=8.3.0",
    "respx>=0.21.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[project.scripts]
macrodata = "macrodata.surfaces.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/macrodata"]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "S", "RUF", "PL"]
ignore = ["PLR0913"]

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = "src"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --strict-config"
markers = [
  "live: opt-in tests that call external provider APIs",
]
```

- [ ] **Step 4: Add minimal package and CLI**

Create `src/macrodata/__init__.py`:

```python
from __future__ import annotations

__version__ = "0.1.0"
```

Create `src/macrodata/__main__.py`:

```python
from __future__ import annotations

from macrodata.surfaces.cli import main


if __name__ == "__main__":
    main()
```

Create `src/macrodata/surfaces/cli.py`:

```python
from __future__ import annotations

import json
from typing import Any

import typer

from macrodata import __version__

app = typer.Typer(
    name="macrodata",
    help="Agent-friendly public macro data CLI.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)


def emit(payload: dict[str, Any]) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


@app.command()
def doctor() -> None:
    emit(
        {
            "ok": True,
            "command": "doctor",
            "data": {
                "package": "macrodata-cli",
                "version": __version__,
            },
        }
    )


def main() -> None:
    app()
```

- [ ] **Step 5: Run the test and verify it passes**

Run:

```bash
uv run pytest tests/cli/test_cli_foundation.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add pyproject.toml src/macrodata tests/cli/test_cli_foundation.py
git commit -m "feat: initialize macrodata cli package"
```

## Task 2: Core Models And Result Envelopes

**Files:**
- Create: `src/macrodata/core/errors.py`
- Create: `src/macrodata/core/models.py`
- Create: `src/macrodata/core/series_key.py`
- Create: `src/macrodata/core/envelope.py`
- Create: `tests/unit/test_core_models.py`

- [ ] **Step 1: Write failing core model tests**

Create `tests/unit/test_core_models.py`:

```python
from __future__ import annotations

from macrodata.core.envelope import error_envelope, success_envelope
from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation
from macrodata.core.series_key import parse_series_key


def test_parse_series_key() -> None:
    parsed = parse_series_key("fred:DGS10")

    assert parsed.provider == "fred"
    assert parsed.dataset == "DGS10"
    assert parsed.value == "fred:DGS10"


def test_observation_idempotency_key() -> None:
    observation = MacroObservation(
        series_key="fred:DGS10",
        provider="fred",
        dataset="DGS10",
        observed_at="2026-05-20",
        value=4.57,
        unit="percent",
        frequency="daily",
        source_ts="2026-05-20",
        realtime_start=None,
        realtime_end=None,
        latency_class="eod",
        data_quality="ok",
        provenance=[{"provider": "fred", "source_url": "https://api.stlouisfed.org"}],
    )

    assert observation.idempotency_key == "fred:DGS10:2026-05-20"


def test_success_envelope_shape() -> None:
    payload = success_envelope(command="doctor", data={"status": "ok"}, source_chain=["local"], latency_ms=1)

    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["data"] == {"status": "ok"}
    assert payload["meta"]["source_chain"] == ["local"]


def test_error_envelope_shape() -> None:
    exc = MacrodataError(code="provider_timeout", message="timed out", retryable=True, provider="fred")
    payload = error_envelope(command="fetch.series", error=exc, source_chain=["fred"], latency_ms=10)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "provider_timeout"
    assert payload["error"]["retryable"] is True
    assert payload["meta"]["data_quality"] == "unavailable"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/unit/test_core_models.py -q
```

Expected: import failure for `macrodata.core`.

- [ ] **Step 3: Implement error types**

Create `src/macrodata/core/errors.py`:

```python
from __future__ import annotations


class MacrodataError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool = False,
        provider: str | None = None,
        exit_code: int = 3,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.provider = provider
        self.exit_code = exit_code


class ValidationError(MacrodataError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code=code, message=message, retryable=False, provider=None, exit_code=2)
```

- [ ] **Step 4: Implement series key parser**

Create `src/macrodata/core/series_key.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from macrodata.core.errors import ValidationError


@dataclass(frozen=True)
class SeriesKey:
    provider: str
    dataset: str

    @property
    def value(self) -> str:
        return f"{self.provider}:{self.dataset}"


def parse_series_key(value: str) -> SeriesKey:
    normalized = value.strip()
    if ":" not in normalized:
        raise ValidationError(code="invalid_series_key", message="series key must use '<provider>:<dataset>'")
    provider, dataset = normalized.split(":", 1)
    provider = provider.strip().lower()
    dataset = dataset.strip()
    if not provider or not dataset:
        raise ValidationError(code="invalid_series_key", message="provider and dataset are required")
    return SeriesKey(provider=provider, dataset=dataset)
```

- [ ] **Step 5: Implement domain models**

Create `src/macrodata/core/models.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DataQuality = Literal["ok", "stale", "partial", "unavailable"]


class MacroObservation(BaseModel):
    series_key: str
    provider: str
    dataset: str
    observed_at: str
    value: float | int | str | None
    unit: str | None
    frequency: str | None
    source_ts: str | None
    realtime_start: str | None
    realtime_end: str | None
    latency_class: str
    data_quality: DataQuality
    provenance: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def idempotency_key(self) -> str:
        return f"{self.series_key}:{self.observed_at}"


class SourceCatalogEntry(BaseModel):
    series_key: str
    name: str
    provider: str
    dataset: str
    description: str
    unit: str | None
    frequency: str | None
    latency_class: str
    requires_api_key: bool
    source_url: str
    license_note: str


class ProviderSmokeResult(BaseModel):
    provider: str
    ok: bool
    latency_ms: int
    checked_at: str
    sample_dataset: str | None = None
    sample_source_ts: str | None = None
    error_code: str | None = None
    message: str | None = None


class BundleSnapshot(BaseModel):
    bundle: str
    asof: str
    observations: list[MacroObservation]
    coverage: dict[str, int]
    missing_series: list[str]
    source_chain: list[str]
    data_quality: DataQuality
    reason_codes: list[str]
```

- [ ] **Step 6: Implement envelopes**

Create `src/macrodata/core/envelope.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from macrodata.core.errors import MacrodataError


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def success_envelope(
    *,
    command: str,
    data: dict[str, Any],
    source_chain: list[str],
    latency_ms: int,
    cache: str = "none",
    data_quality: str = "ok",
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "request_id": str(uuid4()),
        "asof": _now_iso(),
        "data": data,
        "meta": {
            "source_chain": source_chain,
            "cache": cache,
            "latency_ms": latency_ms,
            "data_quality": data_quality,
            "reason_codes": list(reason_codes or []),
        },
    }


def error_envelope(
    *,
    command: str,
    error: MacrodataError,
    source_chain: list[str],
    latency_ms: int,
) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "request_id": str(uuid4()),
        "asof": _now_iso(),
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "provider": error.provider,
        },
        "meta": {
            "source_chain": source_chain,
            "cache": "none",
            "latency_ms": latency_ms,
            "data_quality": "unavailable",
            "reason_codes": [error.code],
        },
    }
```

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/unit/test_core_models.py -q
```

Expected: `4 passed`.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/macrodata/core tests/unit/test_core_models.py
git commit -m "feat: add core macrodata models"
```

## Task 3: Curated Catalog

**Files:**
- Create: `src/macrodata/catalog/entries.py`
- Create: `src/macrodata/catalog/registry.py`
- Create: `tests/unit/test_catalog.py`

- [ ] **Step 1: Write failing catalog tests**

Create `tests/unit/test_catalog.py`:

```python
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


def test_catalog_show_known_series() -> None:
    catalog = default_catalog()

    entry = catalog.get("fred:DGS10")

    assert entry.provider == "fred"
    assert entry.dataset == "DGS10"
    assert entry.frequency == "daily"


def test_catalog_unknown_series_raises_validation_error() -> None:
    catalog = CatalogRegistry(entries=[])

    with pytest.raises(ValidationError) as exc:
        catalog.get("fred:UNKNOWN")

    assert exc.value.code == "unknown_series"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_catalog.py -q
```

Expected: import failure for `macrodata.catalog`.

- [ ] **Step 3: Implement catalog entries**

Create `src/macrodata/catalog/entries.py`:

```python
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
        requires_api_key=True,
        source_url=f"https://fred.stlouisfed.org/series/{dataset}",
        license_note="FRED terms and upstream source terms apply.",
    )


CATALOG_ENTRIES: list[SourceCatalogEntry] = [
    _fred("DGS2", "2-Year Treasury Constant Maturity Rate", "US 2-year Treasury yield.", "percent", "daily"),
    _fred("DGS10", "10-Year Treasury Constant Maturity Rate", "US 10-year Treasury yield.", "percent", "daily"),
    _fred("DGS30", "30-Year Treasury Constant Maturity Rate", "US 30-year Treasury yield.", "percent", "daily"),
    _fred("T10Y2Y", "10-Year Minus 2-Year Treasury Spread", "Treasury curve slope.", "percent", "daily"),
    _fred("T10YIE", "10-Year Breakeven Inflation Rate", "Market implied inflation compensation.", "percent", "daily"),
    _fred("DFEDTARU", "Federal Funds Target Range Upper Limit", "Fed target range upper bound.", "percent", "daily"),
    _fred("DFEDTARL", "Federal Funds Target Range Lower Limit", "Fed target range lower bound.", "percent", "daily"),
    _fred("IORB", "Interest Rate on Reserve Balances", "Fed administered reserve rate.", "percent", "daily"),
    _fred("WALCL", "Fed Total Assets", "Federal Reserve balance sheet total assets.", "millions_usd", "weekly"),
    _fred("WRBWFRBL", "Reserve Balances", "Reserve balances with Federal Reserve Banks.", "millions_usd", "weekly"),
    _fred("RRPONTSYD", "Overnight Reverse Repo", "Overnight reverse repurchase agreements.", "millions_usd", "daily"),
    _fred("BAMLC0A0CM", "ICE BofA US Corporate OAS", "Investment-grade corporate OAS proxy.", "percent", "daily"),
    _fred("BAMLH0A0HYM2", "ICE BofA US High Yield OAS", "High-yield OAS proxy.", "percent", "daily"),
    _fred("VIXCLS", "CBOE VIX Close", "Equity volatility proxy.", "index", "daily"),
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
```

- [ ] **Step 4: Implement catalog registry**

Create `src/macrodata/catalog/registry.py`:

```python
from __future__ import annotations

from macrodata.catalog.entries import CATALOG_ENTRIES
from macrodata.core.errors import ValidationError
from macrodata.core.models import SourceCatalogEntry


class CatalogRegistry:
    def __init__(self, *, entries: list[SourceCatalogEntry]) -> None:
        self._entries = {entry.series_key: entry for entry in entries}

    def list_entries(self) -> list[SourceCatalogEntry]:
        return sorted(self._entries.values(), key=lambda entry: entry.series_key)

    def get(self, series_key: str) -> SourceCatalogEntry:
        entry = self._entries.get(series_key)
        if entry is None:
            raise ValidationError(code="unknown_series", message=f"unknown series: {series_key}")
        return entry


def default_catalog() -> CatalogRegistry:
    return CatalogRegistry(entries=CATALOG_ENTRIES)
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/unit/test_catalog.py -q
```

Expected: `3 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/macrodata/catalog tests/unit/test_catalog.py
git commit -m "feat: add curated macro catalog"
```

## Task 4: Provider Contracts And Runtime

**Files:**
- Create: `src/macrodata/providers/contracts.py`
- Create: `src/macrodata/gateway/http_client.py`
- Create: `src/macrodata/app/runtime.py`
- Create: `tests/unit/test_runtime.py`

- [ ] **Step 1: Write failing runtime tests**

Create `tests/unit/test_runtime.py`:

```python
from __future__ import annotations

from macrodata.app.runtime import build_runtime


def test_runtime_builds_catalog_and_gateway() -> None:
    runtime = build_runtime()

    assert runtime.catalog.get("fred:DGS10").dataset == "DGS10"
    assert runtime.gateway is not None
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/unit/test_runtime.py -q
```

Expected: import failure for `macrodata.app.runtime`.

- [ ] **Step 3: Implement provider contracts**

Create `src/macrodata/providers/contracts.py`:

```python
from __future__ import annotations

from typing import Protocol

from macrodata.core.models import MacroObservation, ProviderSmokeResult


class SeriesProvider(Protocol):
    provider_name: str

    def get_latest(self, dataset: str) -> MacroObservation:
        raise NotImplementedError

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        raise NotImplementedError

    def smoke(self) -> ProviderSmokeResult:
        raise NotImplementedError
```

- [ ] **Step 4: Implement HTTP client wrapper**

Create `src/macrodata/gateway/http_client.py`:

```python
from __future__ import annotations

from typing import Any

import httpx

from macrodata.core.errors import MacrodataError


class MacrodataHttpClient:
    def __init__(self, *, timeout_sec: float = 10.0) -> None:
        self.timeout_sec = timeout_sec

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, provider: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise MacrodataError(
                code="provider_timeout",
                message=f"{provider} request timed out after {self.timeout_sec:.1f} seconds",
                retryable=True,
                provider=provider,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MacrodataError(
                code="provider_http_error",
                message=f"{provider} returned HTTP {exc.response.status_code}",
                retryable=exc.response.status_code in {429, 500, 502, 503, 504},
                provider=provider,
            ) from exc
        except ValueError as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"{provider} returned invalid JSON",
                retryable=False,
                provider=provider,
            ) from exc
        return payload if isinstance(payload, dict) else {"data": payload}
```

- [ ] **Step 5: Implement runtime shell**

Create `src/macrodata/app/runtime.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from macrodata.catalog.registry import CatalogRegistry, default_catalog
from macrodata.gateway.http_client import MacrodataHttpClient


@dataclass(frozen=True)
class MacrodataRuntime:
    catalog: CatalogRegistry
    http_client: MacrodataHttpClient
    gateway: object


def build_runtime(*, timeout_sec: float = 10.0) -> MacrodataRuntime:
    catalog = default_catalog()
    http_client = MacrodataHttpClient(timeout_sec=timeout_sec)
    return MacrodataRuntime(catalog=catalog, http_client=http_client, gateway=object())
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/unit/test_runtime.py -q
```

Expected: `1 passed`.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/macrodata/providers src/macrodata/gateway src/macrodata/app tests/unit/test_runtime.py
git commit -m "feat: add provider contracts and runtime shell"
```

## Task 5: FRED Provider And Fetch Commands

**Files:**
- Create: `src/macrodata/providers/fred.py`
- Create: `src/macrodata/gateway/macrodata_gateway.py`
- Create: `src/macrodata/app/services.py`
- Modify: `src/macrodata/app/runtime.py`
- Modify: `src/macrodata/surfaces/cli.py`
- Create: `tests/provider/test_fred_provider.py`
- Create: `tests/cli/test_fetch_commands.py`

- [ ] **Step 1: Write failing FRED provider test**

Create `tests/provider/test_fred_provider.py`:

```python
from __future__ import annotations

import respx
from httpx import Response

from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.fred import FredSeriesProvider


@respx.mock
def test_fred_range_parses_observations() -> None:
    route = respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={
                "observations": [
                    {
                        "date": "2026-05-20",
                        "value": "4.57",
                        "realtime_start": "2026-05-21",
                        "realtime_end": "2026-05-21",
                    }
                ]
            },
        )
    )
    provider = FredSeriesProvider(http_client=MacrodataHttpClient(), api_key="test-key")

    observations = provider.get_range("DGS10", start="2026-05-20", end="2026-05-20")

    assert route.called
    assert observations[0].series_key == "fred:DGS10"
    assert observations[0].value == 4.57
    assert observations[0].source_ts == "2026-05-20"
```

- [ ] **Step 2: Write failing CLI fetch test**

Create `tests/cli/test_fetch_commands.py`:

```python
from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app


@respx.mock
def test_fetch_series_command_returns_json() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={
                "observations": [
                    {
                        "date": "2026-05-20",
                        "value": "4.57",
                        "realtime_start": "2026-05-21",
                        "realtime_end": "2026-05-21",
                    }
                ]
            },
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "fetch",
            "series",
            "fred:DGS10",
            "--start",
            "2026-05-20",
            "--end",
            "2026-05-20",
            "--fred-api-key",
            "test-key",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["series_key"] == "fred:DGS10"
    assert payload["data"]["observations"][0]["value"] == 4.57
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest tests/provider/test_fred_provider.py tests/cli/test_fetch_commands.py -q
```

Expected: import failure for `macrodata.providers.fred`.

- [ ] **Step 4: Implement FRED provider**

Create `src/macrodata/providers/fred.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class FredSeriesProvider:
    provider_name = "fred"
    base_url = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, *, http_client: MacrodataHttpClient, api_key: str | None) -> None:
        self._http_client = http_client
        self._api_key = (api_key or "").strip()

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(code="no_data", message=f"FRED returned no data for {dataset}", provider="fred", exit_code=4)
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        if not self._api_key:
            raise MacrodataError(code="missing_api_key", message="FRED_API_KEY is required", provider="fred", exit_code=2)
        payload = self._http_client.get_json(
            self.base_url,
            params={
                "series_id": dataset,
                "api_key": self._api_key,
                "file_type": "json",
                "observation_start": start,
                "observation_end": end,
                "sort_order": "asc",
            },
            provider="fred",
        )
        raw_observations = payload.get("observations", [])
        if not isinstance(raw_observations, list):
            raise MacrodataError(code="provider_parse_error", message="FRED observations must be a list", provider="fred")
        return [self._parse_observation(dataset, item) for item in raw_observations if isinstance(item, dict)]

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("DGS10")
        except MacrodataError as exc:
            return ProviderSmokeResult(provider="fred", ok=False, latency_ms=0, checked_at=checked_at, error_code=exc.code, message=exc.message)
        return ProviderSmokeResult(provider="fred", ok=True, latency_ms=0, checked_at=checked_at, sample_dataset="DGS10", sample_source_ts=latest.source_ts)

    def _parse_observation(self, dataset: str, item: dict[str, Any]) -> MacroObservation:
        observed_at = str(item.get("date", "")).strip()
        raw_value = item.get("value")
        value = None if raw_value in {None, "."} else float(raw_value)
        return MacroObservation(
            series_key=f"fred:{dataset}",
            provider="fred",
            dataset=dataset,
            observed_at=observed_at,
            value=value,
            unit=None,
            frequency=None,
            source_ts=observed_at,
            realtime_start=item.get("realtime_start"),
            realtime_end=item.get("realtime_end"),
            latency_class="eod",
            data_quality="ok" if value is not None else "partial",
            provenance=[{"provider": "fred", "source_url": f"https://fred.stlouisfed.org/series/{dataset}"}],
        )
```

- [ ] **Step 5: Implement gateway and services**

Create `src/macrodata/gateway/macrodata_gateway.py`:

```python
from __future__ import annotations

from macrodata.catalog.registry import CatalogRegistry
from macrodata.core.errors import ValidationError
from macrodata.core.models import MacroObservation
from macrodata.core.series_key import parse_series_key
from macrodata.providers.contracts import SeriesProvider


class MacrodataGateway:
    def __init__(self, *, catalog: CatalogRegistry, providers: dict[str, SeriesProvider]) -> None:
        self._catalog = catalog
        self._providers = providers

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        parsed = parse_series_key(series_key)
        self._catalog.get(parsed.value)
        provider = self._providers.get(parsed.provider)
        if provider is None:
            raise ValidationError(code="unknown_provider", message=f"unknown provider: {parsed.provider}")
        return provider.get_range(parsed.dataset, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        parsed = parse_series_key(series_key)
        self._catalog.get(parsed.value)
        provider = self._providers.get(parsed.provider)
        if provider is None:
            raise ValidationError(code="unknown_provider", message=f"unknown provider: {parsed.provider}")
        return provider.get_latest(parsed.dataset)
```

Create `src/macrodata/app/services.py`:

```python
from __future__ import annotations

from macrodata.core.models import MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway


class MacrodataService:
    def __init__(self, *, gateway: MacrodataGateway) -> None:
        self._gateway = gateway

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        return self._gateway.fetch_series(series_key, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        return self._gateway.fetch_latest(series_key)
```

- [ ] **Step 6: Wire runtime**

Replace `src/macrodata/app/runtime.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass

from macrodata.app.services import MacrodataService
from macrodata.catalog.registry import CatalogRegistry, default_catalog
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.gateway.macrodata_gateway import MacrodataGateway
from macrodata.providers.fred import FredSeriesProvider


@dataclass(frozen=True)
class MacrodataRuntime:
    catalog: CatalogRegistry
    http_client: MacrodataHttpClient
    gateway: MacrodataGateway
    service: MacrodataService


def build_runtime(*, timeout_sec: float = 10.0, fred_api_key: str | None = None) -> MacrodataRuntime:
    catalog = default_catalog()
    http_client = MacrodataHttpClient(timeout_sec=timeout_sec)
    providers = {
        "fred": FredSeriesProvider(http_client=http_client, api_key=fred_api_key),
    }
    gateway = MacrodataGateway(catalog=catalog, providers=providers)
    service = MacrodataService(gateway=gateway)
    return MacrodataRuntime(catalog=catalog, http_client=http_client, gateway=gateway, service=service)
```

- [ ] **Step 7: Add fetch CLI commands**

Replace `src/macrodata/surfaces/cli.py` with:

```python
from __future__ import annotations

import json
import os
import time
from typing import Any

import typer

from macrodata import __version__
from macrodata.app.runtime import build_runtime
from macrodata.core.envelope import error_envelope, success_envelope
from macrodata.core.errors import MacrodataError

app = typer.Typer(
    name="macrodata",
    help="Agent-friendly public macro data CLI.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
fetch_app = typer.Typer(help="Fetch macro observations.")
app.add_typer(fetch_app, name="fetch")


def emit(payload: dict[str, Any], *, pretty: bool = False) -> None:
    if pretty:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    typer.echo(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


@app.command()
def doctor(format: str = typer.Option("json", "--format")) -> None:
    emit(
        success_envelope(
            command="doctor",
            data={"package": "macrodata-cli", "version": __version__, "fred_api_key_configured": bool(os.getenv("FRED_API_KEY"))},
            source_chain=["local"],
            latency_ms=0,
        ),
        pretty=format == "pretty",
    )


@fetch_app.command("series")
def fetch_series(
    series_key: str,
    start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    format: str = typer.Option("json", "--format"),
) -> None:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=fred_api_key or os.getenv("FRED_API_KEY"))
    try:
        observations = runtime.service.fetch_series(series_key, start=start, end=end)
    except MacrodataError as exc:
        emit(error_envelope(command="fetch.series", error=exc, source_chain=[exc.provider or "unknown"], latency_ms=int((time.monotonic() - started) * 1000)), pretty=format == "pretty")
        raise typer.Exit(exc.exit_code) from exc
    emit(
        success_envelope(
            command="fetch.series",
            data={"series_key": series_key, "observations": [item.model_dump() for item in observations]},
            source_chain=[series_key.split(":", 1)[0]],
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        pretty=format == "pretty",
    )


def main() -> None:
    app()
```

- [ ] **Step 8: Run tests**

Run:

```bash
uv run pytest tests/provider/test_fred_provider.py tests/cli/test_fetch_commands.py tests/unit/test_runtime.py -q
```

Expected: all selected tests pass.

- [ ] **Step 9: Commit**

Run:

```bash
git add src/macrodata tests/provider/test_fred_provider.py tests/cli/test_fetch_commands.py
git commit -m "feat: add fred provider and fetch command"
```

## Task 6: Catalog And Source CLI Commands

**Files:**
- Modify: `src/macrodata/surfaces/cli.py`
- Create: `tests/cli/test_catalog_commands.py`
- Create: `tests/cli/test_source_commands.py`

- [ ] **Step 1: Write failing catalog CLI tests**

Create `tests/cli/test_catalog_commands.py`:

```python
from __future__ import annotations

import json

from typer.testing import CliRunner

from macrodata.surfaces.cli import app


def test_catalog_list_command() -> None:
    result = CliRunner().invoke(app, ["catalog", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert any(entry["series_key"] == "fred:DGS10" for entry in payload["data"]["entries"])


def test_catalog_show_command() -> None:
    result = CliRunner().invoke(app, ["catalog", "show", "fred:DGS10"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["data"]["entry"]["provider"] == "fred"
```

- [ ] **Step 2: Write failing source smoke CLI test**

Create `tests/cli/test_source_commands.py`:

```python
from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app


@respx.mock
def test_source_smoke_fred() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={
                "observations": [
                    {
                        "date": "2026-05-20",
                        "value": "4.57",
                        "realtime_start": "2026-05-21",
                        "realtime_end": "2026-05-21",
                    }
                ]
            },
        )
    )

    result = CliRunner().invoke(app, ["source", "smoke", "--provider", "fred", "--fred-api-key", "test-key"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["result"]["provider"] == "fred"
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest tests/cli/test_catalog_commands.py tests/cli/test_source_commands.py -q
```

Expected: Typer reports missing `catalog` and `source` commands.

- [ ] **Step 4: Add catalog and source command groups**

Modify `src/macrodata/surfaces/cli.py` by adding command groups after `fetch_app`:

```python
catalog_app = typer.Typer(help="Inspect curated source catalog.")
source_app = typer.Typer(help="Inspect data source health.")
app.add_typer(catalog_app, name="catalog")
app.add_typer(source_app, name="source")
```

Add these command functions before `main()`:

```python
@catalog_app.command("list")
def catalog_list(format: str = typer.Option("json", "--format")) -> None:
    started = time.monotonic()
    runtime = build_runtime()
    entries = [entry.model_dump() for entry in runtime.catalog.list_entries()]
    emit(
        success_envelope(
            command="catalog.list",
            data={"entries": entries},
            source_chain=["catalog"],
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        pretty=format == "pretty",
    )


@catalog_app.command("show")
def catalog_show(series_key: str, format: str = typer.Option("json", "--format")) -> None:
    started = time.monotonic()
    runtime = build_runtime()
    try:
        entry = runtime.catalog.get(series_key)
    except MacrodataError as exc:
        emit(error_envelope(command="catalog.show", error=exc, source_chain=["catalog"], latency_ms=int((time.monotonic() - started) * 1000)), pretty=format == "pretty")
        raise typer.Exit(exc.exit_code) from exc
    emit(
        success_envelope(
            command="catalog.show",
            data={"entry": entry.model_dump()},
            source_chain=["catalog"],
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        pretty=format == "pretty",
    )


@source_app.command("smoke")
def source_smoke(
    provider: str = typer.Option(..., "--provider"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    format: str = typer.Option("json", "--format"),
) -> None:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=fred_api_key or os.getenv("FRED_API_KEY"))
    selected = runtime.gateway._providers.get(provider)
    if selected is None:
        exc = MacrodataError(code="unknown_provider", message=f"unknown provider: {provider}", provider=provider, exit_code=2)
        emit(error_envelope(command="source.smoke", error=exc, source_chain=[provider], latency_ms=int((time.monotonic() - started) * 1000)), pretty=format == "pretty")
        raise typer.Exit(exc.exit_code) from exc
    result = selected.smoke()
    emit(
        success_envelope(
            command="source.smoke",
            data={"result": result.model_dump()},
            source_chain=[provider],
            latency_ms=int((time.monotonic() - started) * 1000),
            data_quality="ok" if result.ok else "unavailable",
        ),
        pretty=format == "pretty",
    )
```

- [ ] **Step 5: Replace private provider access with a gateway method**

Modify `src/macrodata/gateway/macrodata_gateway.py` by adding:

```python
    def provider(self, provider_name: str) -> SeriesProvider | None:
        return self._providers.get(provider_name)
```

Then replace `runtime.gateway._providers.get(provider)` in CLI with:

```python
    selected = runtime.gateway.provider(provider)
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/cli/test_catalog_commands.py tests/cli/test_source_commands.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/macrodata/surfaces/cli.py src/macrodata/gateway/macrodata_gateway.py tests/cli/test_catalog_commands.py tests/cli/test_source_commands.py
git commit -m "feat: add catalog and source cli commands"
```

## Task 7: NY Fed Provider

**Files:**
- Create: `src/macrodata/providers/nyfed.py`
- Modify: `src/macrodata/app/runtime.py`
- Create: `tests/provider/test_nyfed_provider.py`

- [ ] **Step 1: Write failing NY Fed provider test**

Create `tests/provider/test_nyfed_provider.py`:

```python
from __future__ import annotations

import respx
from httpx import Response

from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.nyfed import NyFedMarketsProvider


@respx.mock
def test_nyfed_sofr_parses_latest_rate() -> None:
    respx.get("https://markets.newyorkfed.org/api/rates/secured/sofr/search.json").mock(
        return_value=Response(
            200,
            json={
                "refRates": [
                    {
                        "effectiveDate": "2026-05-20",
                        "percentRate": "4.31",
                    }
                ]
            },
        )
    )
    provider = NyFedMarketsProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("SOFR", start="2026-05-20", end="2026-05-20")

    assert observations[0].series_key == "nyfed:SOFR"
    assert observations[0].value == 4.31
    assert observations[0].source_ts == "2026-05-20"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/provider/test_nyfed_provider.py -q
```

Expected: import failure for `macrodata.providers.nyfed`.

- [ ] **Step 3: Implement NY Fed provider**

Create `src/macrodata/providers/nyfed.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class NyFedMarketsProvider:
    provider_name = "nyfed"
    sofr_url = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json"

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(code="no_data", message=f"NY Fed returned no data for {dataset}", provider="nyfed", exit_code=4)
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        if dataset != "SOFR":
            raise MacrodataError(code="unknown_series", message=f"NY Fed dataset is not supported: {dataset}", provider="nyfed", exit_code=2)
        payload = self._http_client.get_json(
            self.sofr_url,
            params={"startDate": start, "endDate": end, "type": "rate"},
            provider="nyfed",
        )
        rows = payload.get("refRates", [])
        if not isinstance(rows, list):
            raise MacrodataError(code="provider_parse_error", message="NY Fed refRates must be a list", provider="nyfed")
        return [self._parse_sofr(row) for row in rows if isinstance(row, dict)]

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("SOFR")
        except MacrodataError as exc:
            return ProviderSmokeResult(provider="nyfed", ok=False, latency_ms=0, checked_at=checked_at, error_code=exc.code, message=exc.message)
        return ProviderSmokeResult(provider="nyfed", ok=True, latency_ms=0, checked_at=checked_at, sample_dataset="SOFR", sample_source_ts=latest.source_ts)

    def _parse_sofr(self, row: dict[str, Any]) -> MacroObservation:
        observed_at = str(row.get("effectiveDate", "")).strip()
        return MacroObservation(
            series_key="nyfed:SOFR",
            provider="nyfed",
            dataset="SOFR",
            observed_at=observed_at,
            value=float(row["percentRate"]),
            unit="percent",
            frequency="daily",
            source_ts=observed_at,
            realtime_start=None,
            realtime_end=None,
            latency_class="daily",
            data_quality="ok",
            provenance=[{"provider": "nyfed", "source_url": self.sofr_url}],
        )
```

- [ ] **Step 4: Wire NY Fed provider into runtime**

Modify `src/macrodata/app/runtime.py`:

```python
from macrodata.providers.nyfed import NyFedMarketsProvider
```

Update the providers dictionary:

```python
    providers = {
        "fred": FredSeriesProvider(http_client=http_client, api_key=fred_api_key),
        "nyfed": NyFedMarketsProvider(http_client=http_client),
    }
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/provider/test_nyfed_provider.py tests/unit/test_runtime.py -q
```

Expected: selected tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/macrodata/providers/nyfed.py src/macrodata/app/runtime.py tests/provider/test_nyfed_provider.py
git commit -m "feat: add ny fed markets provider"
```

## Task 8: Treasury Fiscal Provider

**Files:**
- Create: `src/macrodata/providers/treasury_fiscal.py`
- Modify: `src/macrodata/app/runtime.py`
- Create: `tests/provider/test_treasury_fiscal_provider.py`

- [ ] **Step 1: Write failing Treasury Fiscal provider test**

Create `tests/provider/test_treasury_fiscal_provider.py`:

```python
from __future__ import annotations

import respx
from httpx import Response

from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.treasury_fiscal import TreasuryFiscalProvider


@respx.mock
def test_treasury_operating_cash_balance_parses_data() -> None:
    respx.get(
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
    ).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "record_date": "2026-05-20",
                        "account_type": "Treasury General Account (TGA)",
                        "close_today_bal": "812345",
                    }
                ]
            },
        )
    )
    provider = TreasuryFiscalProvider(http_client=MacrodataHttpClient())

    observations = provider.get_range("operating_cash_balance", start="2026-05-20", end="2026-05-20")

    assert observations[0].series_key == "treasury_fiscal:operating_cash_balance"
    assert observations[0].value == 812345.0
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/provider/test_treasury_fiscal_provider.py -q
```

Expected: import failure for `macrodata.providers.treasury_fiscal`.

- [ ] **Step 3: Implement Treasury Fiscal provider**

Create `src/macrodata/providers/treasury_fiscal.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient


class TreasuryFiscalProvider:
    provider_name = "treasury_fiscal"
    operating_cash_balance_url = (
        "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
    )

    def __init__(self, *, http_client: MacrodataHttpClient) -> None:
        self._http_client = http_client

    def get_latest(self, dataset: str) -> MacroObservation:
        observations = self.get_range(dataset, start="1776-07-04", end=datetime.now(UTC).date().isoformat())
        if not observations:
            raise MacrodataError(code="no_data", message=f"Treasury Fiscal returned no data for {dataset}", provider="treasury_fiscal", exit_code=4)
        return observations[-1]

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        if dataset != "operating_cash_balance":
            raise MacrodataError(code="unknown_series", message=f"Treasury Fiscal dataset is not supported: {dataset}", provider="treasury_fiscal", exit_code=2)
        payload = self._http_client.get_json(
            self.operating_cash_balance_url,
            params={
                "filter": f"record_date:gte:{start},record_date:lte:{end}",
                "sort": "record_date",
                "page[size]": "10000",
            },
            provider="treasury_fiscal",
        )
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise MacrodataError(code="provider_parse_error", message="Treasury Fiscal data must be a list", provider="treasury_fiscal")
        return [self._parse_row(row) for row in rows if isinstance(row, dict)]

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("operating_cash_balance")
        except MacrodataError as exc:
            return ProviderSmokeResult(provider="treasury_fiscal", ok=False, latency_ms=0, checked_at=checked_at, error_code=exc.code, message=exc.message)
        return ProviderSmokeResult(provider="treasury_fiscal", ok=True, latency_ms=0, checked_at=checked_at, sample_dataset="operating_cash_balance", sample_source_ts=latest.source_ts)

    def _parse_row(self, row: dict[str, Any]) -> MacroObservation:
        observed_at = str(row.get("record_date", "")).strip()
        return MacroObservation(
            series_key="treasury_fiscal:operating_cash_balance",
            provider="treasury_fiscal",
            dataset="operating_cash_balance",
            observed_at=observed_at,
            value=float(row["close_today_bal"]),
            unit="millions_usd",
            frequency="daily",
            source_ts=observed_at,
            realtime_start=None,
            realtime_end=None,
            latency_class="daily",
            data_quality="ok",
            provenance=[{"provider": "treasury_fiscal", "source_url": self.operating_cash_balance_url}],
        )
```

- [ ] **Step 4: Wire Treasury Fiscal provider into runtime**

Modify `src/macrodata/app/runtime.py`:

```python
from macrodata.providers.treasury_fiscal import TreasuryFiscalProvider
```

Update the providers dictionary:

```python
    providers = {
        "fred": FredSeriesProvider(http_client=http_client, api_key=fred_api_key),
        "nyfed": NyFedMarketsProvider(http_client=http_client),
        "treasury_fiscal": TreasuryFiscalProvider(http_client=http_client),
    }
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/provider/test_treasury_fiscal_provider.py tests/unit/test_runtime.py -q
```

Expected: selected tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/macrodata/providers/treasury_fiscal.py src/macrodata/app/runtime.py tests/provider/test_treasury_fiscal_provider.py
git commit -m "feat: add treasury fiscal provider"
```

## Task 9: Rates And Liquidity Bundles

**Files:**
- Modify: `src/macrodata/app/services.py`
- Modify: `src/macrodata/surfaces/cli.py`
- Create: `tests/unit/test_bundles.py`
- Create: `tests/cli/test_bundle_commands.py`

- [ ] **Step 1: Write failing bundle service test**

Create `tests/unit/test_bundles.py`:

```python
from __future__ import annotations

from macrodata.core.models import BundleSnapshot, MacroObservation


def make_observation(series_key: str) -> MacroObservation:
    provider, dataset = series_key.split(":", 1)
    return MacroObservation(
        series_key=series_key,
        provider=provider,
        dataset=dataset,
        observed_at="2026-05-20",
        value=1.0,
        unit=None,
        frequency=None,
        source_ts="2026-05-20",
        realtime_start=None,
        realtime_end=None,
        latency_class="eod",
        data_quality="ok",
        provenance=[],
    )


def test_bundle_snapshot_model() -> None:
    snapshot = BundleSnapshot(
        bundle="rates-core",
        asof="2026-05-21",
        observations=[make_observation("fred:DGS10")],
        coverage={"requested": 1, "available": 1},
        missing_series=[],
        source_chain=["fred"],
        data_quality="ok",
        reason_codes=[],
    )

    assert snapshot.coverage["available"] == 1
```

- [ ] **Step 2: Write failing bundle CLI test**

Create `tests/cli/test_bundle_commands.py`:

```python
from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app


@respx.mock
def test_rates_core_bundle_command() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={
                "observations": [
                    {
                        "date": "2026-05-20",
                        "value": "4.57",
                        "realtime_start": "2026-05-21",
                        "realtime_end": "2026-05-21",
                    }
                ]
            },
        )
    )

    result = CliRunner().invoke(app, ["bundle", "rates-core", "--asof", "2026-05-21", "--fred-api-key", "test-key"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["snapshot"]["bundle"] == "rates-core"
    assert payload["data"]["snapshot"]["coverage"]["requested"] > 0
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_bundles.py tests/cli/test_bundle_commands.py -q
```

Expected: Typer reports missing `bundle` command.

- [ ] **Step 4: Add bundle service constants and method**

Modify `src/macrodata/app/services.py`:

```python
from __future__ import annotations

from macrodata.core.models import BundleSnapshot, MacroObservation
from macrodata.gateway.macrodata_gateway import MacrodataGateway

RATES_CORE = [
    "fred:DGS2",
    "fred:DGS10",
    "fred:DGS30",
    "fred:T10Y2Y",
    "fred:T10YIE",
    "fred:DFEDTARU",
    "fred:DFEDTARL",
    "fred:IORB",
]

LIQUIDITY_CORE = [
    "fred:WALCL",
    "fred:WRBWFRBL",
    "fred:RRPONTSYD",
    "nyfed:SOFR",
    "treasury_fiscal:operating_cash_balance",
]


class MacrodataService:
    def __init__(self, *, gateway: MacrodataGateway) -> None:
        self._gateway = gateway

    def fetch_series(self, series_key: str, *, start: str, end: str) -> list[MacroObservation]:
        return self._gateway.fetch_series(series_key, start=start, end=end)

    def fetch_latest(self, series_key: str) -> MacroObservation:
        return self._gateway.fetch_latest(series_key)

    def bundle(self, bundle: str, *, asof: str) -> BundleSnapshot:
        requested = _bundle_series(bundle)
        observations: list[MacroObservation] = []
        missing: list[str] = []
        source_chain: list[str] = []
        for series_key in requested:
            try:
                observation = self.fetch_latest(series_key)
            except Exception:
                missing.append(series_key)
                continue
            observations.append(observation)
            if observation.provider not in source_chain:
                source_chain.append(observation.provider)
        data_quality = "ok" if not missing else "partial"
        return BundleSnapshot(
            bundle=bundle,
            asof=asof,
            observations=observations,
            coverage={"requested": len(requested), "available": len(observations)},
            missing_series=missing,
            source_chain=source_chain,
            data_quality=data_quality,
            reason_codes=["missing_series"] if missing else [],
        )


def _bundle_series(bundle: str) -> list[str]:
    if bundle == "rates-core":
        return list(RATES_CORE)
    if bundle == "liquidity-core":
        return list(LIQUIDITY_CORE)
    raise ValueError(f"unsupported bundle: {bundle}")
```

- [ ] **Step 5: Add bundle CLI group**

Modify `src/macrodata/surfaces/cli.py` by adding:

```python
bundle_app = typer.Typer(help="Fetch curated macro bundles.")
app.add_typer(bundle_app, name="bundle")
```

Add command:

```python
@bundle_app.command("rates-core")
def bundle_rates_core(
    asof: str = typer.Option(..., "--asof"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    format: str = typer.Option("json", "--format"),
) -> None:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=fred_api_key or os.getenv("FRED_API_KEY"))
    snapshot = runtime.service.bundle("rates-core", asof=asof)
    emit(
        success_envelope(
            command="bundle.rates-core",
            data={"snapshot": snapshot.model_dump()},
            source_chain=snapshot.source_chain,
            latency_ms=int((time.monotonic() - started) * 1000),
            data_quality=snapshot.data_quality,
            reason_codes=snapshot.reason_codes,
        ),
        pretty=format == "pretty",
    )
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/unit/test_bundles.py tests/cli/test_bundle_commands.py -q
```

Expected: selected tests pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/macrodata/app/services.py src/macrodata/surfaces/cli.py tests/unit/test_bundles.py tests/cli/test_bundle_commands.py
git commit -m "feat: add macro bundle snapshots"
```

## Task 10: MCP Server

**Files:**
- Create: `src/macrodata/surfaces/mcp_server.py`
- Modify: `src/macrodata/surfaces/cli.py`
- Create: `tests/mcp/test_mcp_server.py`

- [ ] **Step 1: Write failing MCP test**

Create `tests/mcp/test_mcp_server.py`:

```python
from __future__ import annotations

from macrodata.surfaces.mcp_server import create_mcp


def test_create_mcp_server() -> None:
    server = create_mcp()

    assert server.name == "macrodata"
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/mcp/test_mcp_server.py -q
```

Expected: import failure for `macrodata.surfaces.mcp_server`.

- [ ] **Step 3: Implement FastMCP server factory**

Create `src/macrodata/surfaces/mcp_server.py`:

```python
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from macrodata.app.runtime import build_runtime


def create_mcp() -> FastMCP:
    mcp = FastMCP("macrodata")

    @mcp.tool()
    def doctor() -> dict[str, object]:
        return {
            "package": "macrodata-cli",
            "fred_api_key_configured": bool(os.getenv("FRED_API_KEY")),
        }

    @mcp.tool()
    def catalog_list() -> dict[str, object]:
        runtime = build_runtime()
        return {"entries": [entry.model_dump() for entry in runtime.catalog.list_entries()]}

    @mcp.tool()
    def catalog_show(series_key: str) -> dict[str, object]:
        runtime = build_runtime()
        return {"entry": runtime.catalog.get(series_key).model_dump()}

    @mcp.tool()
    def fetch_series(series_key: str, start: str, end: str) -> dict[str, object]:
        runtime = build_runtime(fred_api_key=os.getenv("FRED_API_KEY"))
        observations = runtime.service.fetch_series(series_key, start=start, end=end)
        return {"series_key": series_key, "observations": [item.model_dump() for item in observations]}

    return mcp


def serve() -> None:
    create_mcp().run()
```

- [ ] **Step 4: Add CLI mcp serve command**

Modify `src/macrodata/surfaces/cli.py` by adding:

```python
mcp_app = typer.Typer(help="Run MCP server.")
app.add_typer(mcp_app, name="mcp")
```

Add command:

```python
@mcp_app.command("serve")
def mcp_serve() -> None:
    from macrodata.surfaces.mcp_server import serve

    serve()
```

- [ ] **Step 5: Run MCP tests**

Run:

```bash
uv run pytest tests/mcp/test_mcp_server.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/macrodata/surfaces/mcp_server.py src/macrodata/surfaces/cli.py tests/mcp/test_mcp_server.py
git commit -m "feat: expose macrodata mcp server"
```

## Task 11: Documentation And Agent Instructions

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/reference/result-envelope.md`
- Create: `docs/reference/catalog.md`
- Create: `docs/reference/mcp-tools.md`

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# macrodata-cli

Agent-friendly public macro data CLI, Python SDK, and MCP server.

## Quickstart

```bash
uv sync
uv run macrodata doctor
uv run macrodata catalog list
uv run macrodata fetch series fred:DGS10 --start 2026-05-20 --end 2026-05-20 --fred-api-key "$FRED_API_KEY"
```

Every command emits one JSON object to stdout by default.

## MCP

```bash
uv run macrodata mcp serve
```

The MCP server exposes catalog and fetch tools backed by the same application services as the CLI.
```

- [ ] **Step 2: Create AGENTS.md**

Create `AGENTS.md`:

```markdown
# AGENTS.md

`macrodata-cli` is a read-only public macro data tool for coding and research agents.

## Agent usage

- Prefer `--format json` or the default output.
- Treat stdout as one JSON object.
- Treat stderr as process diagnostics.
- Do not print API keys or config secrets.
- Use `macrodata doctor` before debugging provider failures.
- Use `macrodata catalog list` before guessing a series key.
- Use `macrodata mcp serve` when an MCP-compatible agent needs tools.

## Verification

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```
```

- [ ] **Step 3: Create reference docs**

Create `docs/reference/result-envelope.md`:

```markdown
# Result Envelope

All non-MCP CLI commands emit one JSON object.

Success shape:

```json
{"ok":true,"command":"doctor","request_id":"uuid","asof":"2026-05-21T00:00:00Z","data":{},"meta":{}}
```

Failure shape:

```json
{"ok":false,"command":"fetch.series","request_id":"uuid","asof":"2026-05-21T00:00:00Z","error":{},"meta":{}}
```
```

Create `docs/reference/catalog.md`:

```markdown
# Catalog

Series keys use `<provider>:<dataset>`.

Examples:

- `fred:DGS10`
- `nyfed:SOFR`
- `treasury_fiscal:operating_cash_balance`
```

Create `docs/reference/mcp-tools.md`:

```markdown
# MCP Tools

The stdio MCP server starts with:

```bash
macrodata mcp serve
```

Initial tools:

- `doctor`
- `catalog_list`
- `catalog_show`
- `fetch_series`
```

- [ ] **Step 4: Run documentation-adjacent verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Expected: all commands pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add README.md AGENTS.md docs/reference
git commit -m "docs: add agent and reference documentation"
```

## Task 12: Final Verification And Push

**Files:**
- Modify only files needed to fix verification failures found in this task.

- [ ] **Step 1: Run full verification**

Run:

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

Expected: all commands pass.

- [ ] **Step 2: Inspect git history**

Run:

```bash
git log --oneline --decorate --max-count=10
git status --short
```

Expected: task commits exist and worktree is clean.

- [ ] **Step 3: Push**

Run:

```bash
git push -u origin main
```

Expected: branch `main` pushes to `AnalyThothAI/macrodata-cli`.

## Self-Review

- Spec coverage: package foundation, agent-first JSON output, catalog, FRED provider, NY Fed provider, Treasury Fiscal provider, bundles, MCP server, docs, and tests are each covered by a task.
- Scope control: paid data providers, database persistence, dashboards, and LLM analysis are outside this MVP task list.
- Type consistency: `MacroObservation`, `SourceCatalogEntry`, `ProviderSmokeResult`, `BundleSnapshot`, `MacrodataGateway`, and `MacrodataService` names are consistent across tasks.
- Command consistency: CLI command names match the design for `doctor`, `catalog list`, `catalog show`, `source smoke`, `fetch series`, `bundle rates-core`, and `mcp serve`.
- Verification: each implementation task includes a focused pytest command and a commit step.

Plan complete and saved to `docs/superpowers/plans/2026-05-21-macrodata-cli-mvp-plan.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.

2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.
