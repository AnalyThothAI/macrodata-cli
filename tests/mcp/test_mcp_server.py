from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from mcp.server.fastmcp import FastMCP
from typer.testing import CliRunner

from macrodata.core.models import BundleSnapshot, MacroObservation
from macrodata.surfaces import cli, mcp_server
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
        "bundle_macro_core",
        "bundle_macro_core_history",
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


def test_bundle_macro_core_tool_returns_structured_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "build_runtime", _fake_build_runtime)
    server = create_mcp()

    payload = asyncio.run(_call_tool(server, "bundle_macro_core", {"asof": "2026-05-21"}))

    assert payload["ok"] is True
    assert payload["command"] == "bundle.macro-core"
    assert payload["data"]["snapshot"]["bundle"] == "macro-core"


def test_bundle_macro_core_history_tool_returns_structured_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mcp_server, "build_runtime", _fake_build_runtime)
    server = create_mcp()

    payload = asyncio.run(
        _call_tool(server, "bundle_macro_core_history", {"start": "2026-05-01", "end": "2026-05-21"})
    )

    assert payload["ok"] is True
    assert payload["command"] == "bundle.macro-core-history"
    assert payload["data"]["snapshot"]["bundle"] == "macro-core"
    assert payload["data"]["snapshot"]["coverage"] == {"requested": 1, "available": 1}


def test_mcp_serve_cli_invokes_server(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fake_serve() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli, "serve_mcp", fake_serve)

    result = CliRunner().invoke(cli.app, ["mcp", "serve"])

    assert result.exit_code == 0
    assert called is True


class FakeMacrodataService:
    def bundle(self, bundle: str, *, asof: str) -> BundleSnapshot:
        return _snapshot(bundle=bundle, asof=asof)

    def bundle_history(self, bundle: str, *, start: str, end: str) -> BundleSnapshot:
        return _snapshot(bundle=bundle, asof=end)


@dataclass(frozen=True)
class FakeRuntime:
    service: FakeMacrodataService


def _fake_build_runtime(*, fred_api_key: str | None = None) -> FakeRuntime:
    return FakeRuntime(service=FakeMacrodataService())


def _snapshot(*, bundle: str, asof: str) -> BundleSnapshot:
    return BundleSnapshot(
        bundle=bundle,
        asof=asof,
        observations=[_observation()],
        coverage={"requested": 1, "available": 1},
        missing_series=[],
        series_errors=[],
        source_chain=["fred"],
        data_quality="ok",
        reason_codes=[],
    )


def _observation() -> MacroObservation:
    return MacroObservation(
        series_key="fred:DGS10",
        provider="fred",
        dataset="DGS10",
        observed_at="2026-05-20",
        value=4.57,
        unit=None,
        frequency=None,
        source_ts="2026-05-20",
        realtime_start="2026-05-21",
        realtime_end="2026-05-21",
        latency_class="eod",
        data_quality="ok",
        provenance=[],
    )
