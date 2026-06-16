from __future__ import annotations

from importlib.metadata import version

from macrodata.app.runtime import build_runtime
from macrodata.providers.cftc import CftcProvider
from macrodata.providers.official_calendar import OfficialCalendarProvider
from macrodata.providers.treasury_auction import TreasuryAuctionProvider
from macrodata.providers.yahoo import YahooPriceProvider


def test_runtime_builds_catalog_and_gateway() -> None:
    runtime = build_runtime()

    assert runtime.catalog.get("fred:DGS10").dataset == "DGS10"
    assert runtime.gateway is not None


def test_runtime_wires_macro_core_proxy_providers() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("yahoo"), YahooPriceProvider)
    assert isinstance(runtime.gateway.provider("cftc"), CftcProvider)


def test_runtime_wires_official_calendar_provider() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("official_calendar"), OfficialCalendarProvider)


def test_runtime_wires_treasury_auction_provider() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("treasury_auction"), TreasuryAuctionProvider)


def test_package_version_advances_for_event_history_release() -> None:
    assert version("macrodata-cli") == "0.1.9"
