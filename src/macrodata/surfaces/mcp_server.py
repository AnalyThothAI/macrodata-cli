from __future__ import annotations

import os
import time
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from macrodata import __version__
from macrodata.app.runtime import build_runtime
from macrodata.core.envelope import error_envelope, success_envelope
from macrodata.core.errors import MacrodataError

LOCAL_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
EXTERNAL_READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def create_mcp() -> FastMCP:
    mcp = FastMCP("macrodata")

    @mcp.tool(annotations=LOCAL_READ_ONLY)
    def doctor() -> dict[str, Any]:
        """Return package health and redacted credential availability."""
        started = time.monotonic()
        return success_envelope(
            command="doctor",
            data={
                "package": "macrodata-cli",
                "version": __version__,
                "fred_api_key_configured": bool(os.getenv("FRED_API_KEY")),
            },
            source_chain=["local"],
            latency_ms=_elapsed_ms(started),
        )

    @mcp.tool(annotations=LOCAL_READ_ONLY)
    def catalog_list() -> dict[str, Any]:
        """List curated macro series that macrodata can fetch."""
        started = time.monotonic()
        runtime = build_runtime()
        return success_envelope(
            command="catalog.list",
            data={"entries": [entry.model_dump(mode="json") for entry in runtime.catalog.list_entries()]},
            source_chain=["catalog"],
            latency_ms=_elapsed_ms(started),
        )

    @mcp.tool(annotations=LOCAL_READ_ONLY)
    def catalog_show(series_key: str) -> dict[str, Any]:
        """Show catalog metadata for one series key such as fred:DGS10."""
        started = time.monotonic()
        runtime = build_runtime()
        try:
            entry = runtime.catalog.get(series_key)
        except MacrodataError as exc:
            return error_envelope(
                command="catalog.show",
                error=exc,
                source_chain=["catalog"],
                latency_ms=_elapsed_ms(started),
            )
        return success_envelope(
            command="catalog.show",
            data={"entry": entry.model_dump(mode="json")},
            source_chain=["catalog"],
            latency_ms=_elapsed_ms(started),
        )

    @mcp.tool(annotations=EXTERNAL_READ_ONLY)
    def fetch_series(series_key: str, start: str, end: str) -> dict[str, Any]:
        """Fetch a date-bounded macro series as structured observations."""
        started = time.monotonic()
        runtime = build_runtime(fred_api_key=os.getenv("FRED_API_KEY"))
        try:
            observations = runtime.service.fetch_series(series_key, start=start, end=end)
        except MacrodataError as exc:
            return error_envelope(
                command="fetch.series",
                error=exc,
                source_chain=[exc.provider or _provider_from_series_key(series_key)],
                latency_ms=_elapsed_ms(started),
            )
        return success_envelope(
            command="fetch.series",
            data={
                "series_key": series_key,
                "observations": [observation.model_dump(mode="json") for observation in observations],
            },
            source_chain=[_provider_from_series_key(series_key)],
            latency_ms=_elapsed_ms(started),
        )

    @mcp.tool(annotations=EXTERNAL_READ_ONLY)
    def fetch_latest(series_key: str) -> dict[str, Any]:
        """Fetch the latest available observation for one macro series."""
        started = time.monotonic()
        runtime = build_runtime(fred_api_key=os.getenv("FRED_API_KEY"))
        try:
            observation = runtime.service.fetch_latest(series_key)
        except MacrodataError as exc:
            return error_envelope(
                command="fetch.latest",
                error=exc,
                source_chain=[exc.provider or _provider_from_series_key(series_key)],
                latency_ms=_elapsed_ms(started),
            )
        return success_envelope(
            command="fetch.latest",
            data={"series_key": series_key, "observation": observation.model_dump(mode="json")},
            source_chain=[observation.provider],
            latency_ms=_elapsed_ms(started),
            data_quality=observation.data_quality,
        )

    @mcp.tool(annotations=EXTERNAL_READ_ONLY)
    def bundle_rates_core(asof: str) -> dict[str, Any]:
        """Fetch the rates-core bundle for an as-of date."""
        return _bundle_tool(bundle_name="rates-core", command="bundle.rates-core", asof=asof)

    @mcp.tool(annotations=EXTERNAL_READ_ONLY)
    def bundle_liquidity_core(asof: str) -> dict[str, Any]:
        """Fetch the liquidity-core bundle for an as-of date."""
        return _bundle_tool(bundle_name="liquidity-core", command="bundle.liquidity-core", asof=asof)

    @mcp.tool(annotations=EXTERNAL_READ_ONLY)
    def bundle_macro_core(asof: str) -> dict[str, Any]:
        """Fetch the macro-core bundle for an as-of date."""
        return _bundle_tool(bundle_name="macro-core", command="bundle.macro-core", asof=asof)

    @mcp.tool(annotations=EXTERNAL_READ_ONLY)
    def bundle_macro_core_history(start: str, end: str) -> dict[str, Any]:
        """Fetch date-bounded macro-core bundle history."""
        return _bundle_history_tool(
            bundle_name="macro-core",
            command="bundle.macro-core-history",
            start=start,
            end=end,
        )

    return mcp


def serve() -> None:
    create_mcp().run()


def _bundle_tool(*, bundle_name: str, command: str, asof: str) -> dict[str, Any]:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=os.getenv("FRED_API_KEY"))
    try:
        snapshot = runtime.service.bundle(bundle_name, asof=asof)
    except MacrodataError as exc:
        return error_envelope(
            command=command,
            error=exc,
            source_chain=[exc.provider or "bundle"],
            latency_ms=_elapsed_ms(started),
        )
    return success_envelope(
        command=command,
        data={"snapshot": snapshot.model_dump(mode="json")},
        source_chain=snapshot.source_chain,
        latency_ms=_elapsed_ms(started),
        data_quality=snapshot.data_quality,
        reason_codes=snapshot.reason_codes,
    )


def _bundle_history_tool(*, bundle_name: str, command: str, start: str, end: str) -> dict[str, Any]:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=os.getenv("FRED_API_KEY"))
    try:
        snapshot = runtime.service.bundle_history(bundle_name, start=start, end=end)
    except MacrodataError as exc:
        return error_envelope(
            command=command,
            error=exc,
            source_chain=[exc.provider or "bundle"],
            latency_ms=_elapsed_ms(started),
        )
    return success_envelope(
        command=command,
        data={"snapshot": snapshot.model_dump(mode="json")},
        source_chain=snapshot.source_chain,
        latency_ms=_elapsed_ms(started),
        data_quality=snapshot.data_quality,
        reason_codes=snapshot.reason_codes,
    )


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _provider_from_series_key(series_key: str) -> str:
    if ":" not in series_key:
        return "unknown"
    provider, _dataset = series_key.split(":", 1)
    return provider.strip().lower() or "unknown"
