from __future__ import annotations

import json
from importlib.metadata import version

import pytest
from typer.testing import CliRunner

from macrodata.surfaces.cli import app


def test_doctor_returns_json_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("FINANCE_FRED_API_KEY", raising=False)

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["data"]["package"] == "macrodata-cli"
    assert payload["data"]["version"] == version("macrodata-cli")
    assert payload["data"]["fred_api_key_configured"] is False
    assert payload["data"]["fred_api_key_source"] is None


def test_doctor_reports_fred_api_key_source_without_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "secret-test-key")
    monkeypatch.setenv("FINANCE_FRED_API_KEY", "secret-test-key-alias")

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "secret-test-key" not in result.stdout
    assert "secret-test-key-alias" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["data"]["fred_api_key_configured"] is True
    assert payload["data"]["fred_api_key_source"] == "FRED_API_KEY"


def test_doctor_reports_finance_fred_alias_source_without_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.setenv("FINANCE_FRED_API_KEY", "secret-test-key")

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "secret-test-key" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["data"]["fred_api_key_configured"] is True
    assert payload["data"]["fred_api_key_source"] == "FINANCE_FRED_API_KEY"
