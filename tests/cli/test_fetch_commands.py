from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app

EXPECTED_VALUE = 4.57


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
    assert payload["data"]["observations"][0]["value"] == EXPECTED_VALUE
