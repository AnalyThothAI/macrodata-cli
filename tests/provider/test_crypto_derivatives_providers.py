from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.app.runtime import build_runtime

OKX_TS_MS = "1779235200000"
DERIBIT_TS_MS = 1779235200000
OKX_BTC_OI_USD = 1_939_251_795.54
OKX_BTC_FUNDING_RATE = 0.00012
OKX_BTC_BASIS_PCT = 0.5
DERIBIT_BTC_OI_USD = 502_231_260
DERIBIT_BTC_VOL_INDEX = 66.2


@respx.mock
def test_okx_public_provider_parses_swap_open_interest_funding_and_basis() -> None:
    respx.get("https://www.okx.com/api/v5/public/open-interest").mock(
        return_value=Response(
            200,
            json={
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instType": "SWAP",
                        "instId": "BTC-USDT-SWAP",
                        "oi": "2216113.01",
                        "oiCcy": "22161.13",
                        "oiUsd": "1939251795.54",
                        "ts": OKX_TS_MS,
                    }
                ],
            },
        )
    )
    respx.get("https://www.okx.com/api/v5/public/funding-rate").mock(
        return_value=Response(
            200,
            json={
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "instId": "BTC-USDT-SWAP",
                        "fundingRate": "0.00012",
                        "fundingTime": OKX_TS_MS,
                        "ts": OKX_TS_MS,
                    }
                ],
            },
        )
    )
    respx.get("https://www.okx.com/api/v5/public/mark-price").mock(
        return_value=Response(
            200,
            json={
                "code": "0",
                "msg": "",
                "data": [{"instId": "BTC-USDT-SWAP", "markPx": "100500", "ts": OKX_TS_MS}],
            },
        )
    )
    respx.get("https://www.okx.com/api/v5/market/index-tickers").mock(
        return_value=Response(
            200,
            json={
                "code": "0",
                "msg": "",
                "data": [{"instId": "BTC-USDT", "idxPx": "100000", "ts": OKX_TS_MS}],
            },
        )
    )
    runtime = build_runtime()

    oi = runtime.gateway.fetch_latest("okx:BTC-USDT-SWAP:open_interest_usd")
    funding = runtime.gateway.fetch_latest("okx:BTC-USDT-SWAP:funding_rate")
    basis = runtime.gateway.fetch_latest("okx:BTC-USDT-SWAP:basis_pct")

    assert oi.observed_at == "2026-05-20"
    assert oi.value == OKX_BTC_OI_USD
    assert oi.unit == "usd"
    assert oi.frequency == "intraday"
    assert oi.latency_class == "realtime"
    assert oi.data_quality == "ok"
    assert oi.provenance[0]["provider"] == "okx"
    assert funding.value == OKX_BTC_FUNDING_RATE
    assert funding.unit == "rate"
    assert basis.value == OKX_BTC_BASIS_PCT
    assert basis.unit == "percent"


@respx.mock
def test_deribit_provider_parses_perpetual_open_interest_funding_basis_and_vol_index() -> None:
    respx.get("https://www.deribit.com/api/v2/public/ticker").mock(
        return_value=Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 8106,
                "result": {
                    "instrument_name": "BTC-PERPETUAL",
                    "timestamp": DERIBIT_TS_MS,
                    "open_interest": 502231260,
                    "funding_8h": 0.00002203,
                    "mark_price": 101.0,
                    "index_price": 100.0,
                    "stats": {"volume_usd": 282615600},
                },
            },
        )
    )
    respx.get("https://www.deribit.com/api/v2/public/get_volatility_index_data").mock(
        return_value=Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 833,
                "result": {
                    "data": [
                        [1779231600000, 65.0, 66.0, 64.0, 65.5],
                        [DERIBIT_TS_MS, 66.0, 67.0, 65.0, 66.2],
                    ]
                },
            },
        )
    )
    runtime = build_runtime()

    oi = runtime.gateway.fetch_latest("deribit:BTC-PERPETUAL:open_interest_usd")
    funding = runtime.gateway.fetch_latest("deribit:BTC-PERPETUAL:funding_8h")
    basis = runtime.gateway.fetch_latest("deribit:BTC-PERPETUAL:basis_pct")
    vol = runtime.gateway.fetch_latest("deribit:BTC:volatility_index")

    assert oi.observed_at == "2026-05-20"
    assert oi.value == DERIBIT_BTC_OI_USD
    assert oi.unit == "usd"
    assert oi.provenance[0]["provider"] == "deribit"
    assert funding.value == pytest.approx(0.00002203)
    assert funding.unit == "rate"
    assert basis.value == 1.0
    assert basis.unit == "percent"
    assert vol.value == DERIBIT_BTC_VOL_INDEX
    assert vol.unit == "index"


@respx.mock
def test_crypto_derivatives_providers_filter_latest_observation_outside_requested_range() -> None:
    respx.get("https://www.okx.com/api/v5/public/open-interest").mock(
        return_value=Response(
            200,
            json={
                "code": "0",
                "msg": "",
                "data": [{"instId": "ETH-USDT-SWAP", "oiUsd": "1000", "ts": OKX_TS_MS}],
            },
        )
    )
    runtime = build_runtime()

    observations = runtime.gateway.fetch_series(
        "okx:ETH-USDT-SWAP:open_interest_usd",
        start="2026-05-21",
        end="2026-05-21",
    )

    assert observations == []
