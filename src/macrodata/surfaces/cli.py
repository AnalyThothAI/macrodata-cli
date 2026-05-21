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


@app.callback()
def root() -> None:
    pass


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
