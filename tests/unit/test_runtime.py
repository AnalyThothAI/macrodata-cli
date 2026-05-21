from __future__ import annotations

from macrodata.app.runtime import build_runtime
from macrodata.providers.cftc import CftcProvider
from macrodata.providers.yahoo import YahooPriceProvider


def test_runtime_builds_catalog_and_gateway() -> None:
    runtime = build_runtime()

    assert runtime.catalog.get("fred:DGS10").dataset == "DGS10"
    assert runtime.gateway is not None


def test_runtime_wires_macro_core_proxy_providers() -> None:
    runtime = build_runtime()

    assert isinstance(runtime.gateway.provider("yahoo"), YahooPriceProvider)
    assert isinstance(runtime.gateway.provider("cftc"), CftcProvider)
