from __future__ import annotations

import json

import respx
from httpx import Response
from typer.testing import CliRunner

from macrodata.surfaces.cli import app

EXPECTED_VALUE = 4.57
EXPECTED_PARSE_ERROR_EXIT_CODE = 3


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
    assert payload["data"]["observations"][0]["unit"] == "percent"
    assert payload["data"]["observations"][0]["frequency"] == "daily"


@respx.mock
def test_fetch_series_command_returns_structured_parse_error() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={"observations": [{"date": "2026-05-20", "value": "bad"}]},
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

    assert result.exit_code == EXPECTED_PARSE_ERROR_EXIT_CODE
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "provider_parse_error"
    assert payload["error"]["provider"] == "fred"
    assert "DGS10" in payload["error"]["message"]
    assert "2026-05-20" in payload["error"]["message"]
    assert "test-key" not in result.stdout


@respx.mock
def test_fetch_series_command_enriches_rrp_unit_from_catalog() -> None:
    respx.get("https://api.stlouisfed.org/fred/series/observations").mock(
        return_value=Response(
            200,
            json={
                "observations": [
                    {
                        "date": "2026-05-20",
                        "value": "24.867",
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
            "fred:RRPONTSYD",
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
    assert payload["data"]["observations"][0]["unit"] == "billions_usd"
    assert payload["data"]["observations"][0]["frequency"] == "daily"
