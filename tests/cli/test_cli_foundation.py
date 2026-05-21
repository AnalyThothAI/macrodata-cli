from __future__ import annotations

import json
from importlib.metadata import version

from typer.testing import CliRunner

from macrodata.surfaces.cli import app


def test_doctor_returns_json_envelope() -> None:
    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["data"]["package"] == "macrodata-cli"
    assert payload["data"]["version"] == version("macrodata-cli")
