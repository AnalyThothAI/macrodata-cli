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
