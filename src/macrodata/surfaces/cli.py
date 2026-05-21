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


def main() -> None:
    app()
