from __future__ import annotations

from macrodata.app.runtime import build_runtime


def test_runtime_builds_catalog_and_gateway() -> None:
    runtime = build_runtime()

    assert runtime.catalog.get("fred:DGS10").dataset == "DGS10"
    assert runtime.gateway is not None
