from __future__ import annotations

from dataclasses import dataclass

from macrodata.catalog.registry import CatalogRegistry, default_catalog
from macrodata.gateway.http_client import MacrodataHttpClient


@dataclass(frozen=True)
class MacrodataRuntime:
    catalog: CatalogRegistry
    http_client: MacrodataHttpClient
    gateway: object


def build_runtime(*, timeout_sec: float = 10.0) -> MacrodataRuntime:
    catalog = default_catalog()
    http_client = MacrodataHttpClient(timeout_sec=timeout_sec)
    return MacrodataRuntime(catalog=catalog, http_client=http_client, gateway=object())
