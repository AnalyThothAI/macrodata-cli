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
from macrodata.surfaces.mcp_server import serve as serve_mcp

app = typer.Typer(
    name="macrodata",
    help="Agent-friendly public macro data CLI.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
)
fetch_app = typer.Typer(help="Fetch macro observations.")
catalog_app = typer.Typer(help="Inspect curated source catalog.")
source_app = typer.Typer(help="Inspect data source health.")
bundle_app = typer.Typer(help="Fetch curated macro bundles.")
mcp_app = typer.Typer(help="Run MCP server.")
app.add_typer(fetch_app, name="fetch")
app.add_typer(catalog_app, name="catalog")
app.add_typer(source_app, name="source")
app.add_typer(bundle_app, name="bundle")
app.add_typer(mcp_app, name="mcp")


@app.callback()
def root() -> None:
    pass


def emit(payload: dict[str, Any], *, pretty: bool = False) -> None:
    if pretty:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    typer.echo(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


@app.command()
def doctor(output_format: str = typer.Option("json", "--format")) -> None:
    emit(
        success_envelope(
            command="doctor",
            data={
                "package": "macrodata-cli",
                "version": __version__,
                "fred_api_key_configured": bool(os.getenv("FRED_API_KEY")),
            },
            source_chain=["local"],
            latency_ms=0,
        ),
        pretty=output_format == "pretty",
    )


@fetch_app.command("series")
def fetch_series(
    series_key: str,
    start: str = typer.Option(..., "--start"),
    end: str = typer.Option(..., "--end"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=fred_api_key or os.getenv("FRED_API_KEY"))
    try:
        observations = runtime.service.fetch_series(series_key, start=start, end=end)
    except MacrodataError as exc:
        emit(
            error_envelope(
                command="fetch.series",
                error=exc,
                source_chain=[exc.provider or "unknown"],
                latency_ms=int((time.monotonic() - started) * 1000),
            ),
            pretty=output_format == "pretty",
        )
        raise typer.Exit(exc.exit_code) from exc
    emit(
        success_envelope(
            command="fetch.series",
            data={
                "series_key": series_key,
                "observations": [item.model_dump(mode="json") for item in observations],
            },
            source_chain=[series_key.split(":", 1)[0]],
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        pretty=output_format == "pretty",
    )


@catalog_app.command("list")
def catalog_list(output_format: str = typer.Option("json", "--format")) -> None:
    started = time.monotonic()
    runtime = build_runtime()
    entries = [entry.model_dump(mode="json") for entry in runtime.catalog.list_entries()]
    emit(
        success_envelope(
            command="catalog.list",
            data={"entries": entries},
            source_chain=["catalog"],
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        pretty=output_format == "pretty",
    )


@catalog_app.command("show")
def catalog_show(series_key: str, output_format: str = typer.Option("json", "--format")) -> None:
    started = time.monotonic()
    runtime = build_runtime()
    try:
        entry = runtime.catalog.get(series_key)
    except MacrodataError as exc:
        emit(
            error_envelope(
                command="catalog.show",
                error=exc,
                source_chain=["catalog"],
                latency_ms=int((time.monotonic() - started) * 1000),
            ),
            pretty=output_format == "pretty",
        )
        raise typer.Exit(exc.exit_code) from exc
    emit(
        success_envelope(
            command="catalog.show",
            data={"entry": entry.model_dump(mode="json")},
            source_chain=["catalog"],
            latency_ms=int((time.monotonic() - started) * 1000),
        ),
        pretty=output_format == "pretty",
    )


@source_app.command("smoke")
def source_smoke(
    provider: str = typer.Option(..., "--provider"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    started = time.monotonic()
    provider_name = provider.strip().lower()
    runtime = build_runtime(fred_api_key=fred_api_key or os.getenv("FRED_API_KEY"))
    selected = runtime.gateway.provider(provider_name)
    if selected is None:
        exc = MacrodataError(
            code="unknown_provider",
            message=f"unknown provider: {provider_name}",
            provider=provider_name,
            exit_code=2,
        )
        emit(
            error_envelope(
                command="source.smoke",
                error=exc,
                source_chain=[provider_name],
                latency_ms=int((time.monotonic() - started) * 1000),
            ),
            pretty=output_format == "pretty",
        )
        raise typer.Exit(exc.exit_code) from exc
    result = selected.smoke()
    emit(
        success_envelope(
            command="source.smoke",
            data={"result": result.model_dump(mode="json")},
            source_chain=[provider_name],
            latency_ms=int((time.monotonic() - started) * 1000),
            data_quality="ok" if result.ok else "unavailable",
        ),
        pretty=output_format == "pretty",
    )


def _run_bundle_command(
    *,
    bundle_name: str,
    command: str,
    asof: str,
    fred_api_key: str | None,
    output_format: str,
) -> None:
    started = time.monotonic()
    runtime = build_runtime(fred_api_key=fred_api_key or os.getenv("FRED_API_KEY"))
    try:
        snapshot = runtime.service.bundle(bundle_name, asof=asof)
    except MacrodataError as exc:
        emit(
            error_envelope(
                command=command,
                error=exc,
                source_chain=[exc.provider or "bundle"],
                latency_ms=int((time.monotonic() - started) * 1000),
            ),
            pretty=output_format == "pretty",
        )
        raise typer.Exit(exc.exit_code) from exc
    emit(
        success_envelope(
            command=command,
            data={"snapshot": snapshot.model_dump(mode="json")},
            source_chain=snapshot.source_chain,
            latency_ms=int((time.monotonic() - started) * 1000),
            data_quality=snapshot.data_quality,
            reason_codes=snapshot.reason_codes,
        ),
        pretty=output_format == "pretty",
    )


@bundle_app.command("rates-core")
def bundle_rates_core(
    asof: str = typer.Option(..., "--asof"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    _run_bundle_command(
        bundle_name="rates-core",
        command="bundle.rates-core",
        asof=asof,
        fred_api_key=fred_api_key,
        output_format=output_format,
    )


@bundle_app.command("liquidity-core")
def bundle_liquidity_core(
    asof: str = typer.Option(..., "--asof"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    _run_bundle_command(
        bundle_name="liquidity-core",
        command="bundle.liquidity-core",
        asof=asof,
        fred_api_key=fred_api_key,
        output_format=output_format,
    )


@bundle_app.command("fetch")
def bundle_fetch(
    bundle_name: str,
    asof: str = typer.Option(..., "--asof"),
    fred_api_key: str | None = typer.Option(None, "--fred-api-key"),
    output_format: str = typer.Option("json", "--format"),
) -> None:
    _run_bundle_command(
        bundle_name=bundle_name,
        command="bundle.fetch",
        asof=asof,
        fred_api_key=fred_api_key,
        output_format=output_format,
    )


@mcp_app.command("serve")
def mcp_serve() -> None:
    serve_mcp()


def main() -> None:
    app()
