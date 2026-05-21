from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP
from typer.testing import CliRunner

from macrodata.surfaces import cli
from macrodata.surfaces.mcp_server import create_mcp


async def _tool_names(server: FastMCP) -> set[str]:
    return {tool.name for tool in await server.list_tools()}


async def _call_tool(server: FastMCP, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    _content, structured_content = await server.call_tool(name, arguments)
    assert isinstance(structured_content, dict)
    return structured_content


def test_create_mcp_server() -> None:
    server = create_mcp()

    assert server.name == "macrodata"


def test_create_mcp_registers_agent_tools() -> None:
    server = create_mcp()

    tool_names = asyncio.run(_tool_names(server))

    assert {
        "doctor",
        "catalog_list",
        "catalog_show",
        "fetch_series",
        "fetch_latest",
        "bundle_rates_core",
        "bundle_liquidity_core",
    }.issubset(tool_names)


def test_catalog_show_tool_returns_structured_envelope() -> None:
    server = create_mcp()

    payload = asyncio.run(_call_tool(server, "catalog_show", {"series_key": "fred:DGS10"}))

    assert payload["ok"] is True
    assert payload["command"] == "catalog.show"
    assert payload["data"]["entry"]["series_key"] == "fred:DGS10"


def test_doctor_tool_does_not_expose_api_key_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "secret-test-key")
    server = create_mcp()

    payload = asyncio.run(_call_tool(server, "doctor", {}))

    assert payload["ok"] is True
    assert payload["data"]["fred_api_key_configured"] is True
    assert "secret-test-key" not in str(payload)


def test_mcp_serve_cli_invokes_server(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_serve() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli, "serve_mcp", fake_serve)

    result = CliRunner().invoke(cli.app, ["mcp", "serve"])

    assert result.exit_code == 0
    assert called is True
