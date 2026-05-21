from __future__ import annotations

from datetime import date, datetime
from typing import Any, ClassVar

import pytest

from macrodata.core.errors import MacrodataError
from macrodata.providers.yahoo import YahooPriceProvider

EXPECTED_CLOSE = 604.25
NO_DATA_EXIT_CODE = 4
LATEST_TIMEOUT_SEC = 4.0


class FakeTicker:
    calls: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, **kwargs: Any) -> FakeHistory:
        self.calls.append({"symbol": self.symbol, **kwargs})
        return FakeHistory([(date(2026, 5, 20), {"Close": EXPECTED_CLOSE})])


class EmptyTicker:
    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    def history(self, **kwargs: Any) -> FakeHistory:
        return FakeHistory([])


class FakeHistory:
    def __init__(self, rows: list[tuple[date, dict[str, float]]]) -> None:
        self._rows = rows
        self.empty = not rows

    def iterrows(self) -> list[tuple[date, dict[str, float]]]:
        return self._rows


def test_yahoo_range_uses_daily_adjusted_history_and_emits_price_observation(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeTicker.calls = []
    monkeypatch.setattr("macrodata.providers.yahoo.yf.Ticker", FakeTicker)
    provider = YahooPriceProvider(timeout_sec=7.5)

    observations = provider.get_range("SPY", start="2026-05-20", end="2026-05-21")

    assert FakeTicker.calls == [
        {
            "symbol": "SPY",
            "start": "2026-05-20",
            "end": "2026-05-21",
            "interval": "1d",
            "auto_adjust": True,
            "repair": False,
            "timeout": 7.5,
            "raise_errors": True,
        }
    ]
    observation = observations[0]
    assert observation.series_key == "yahoo:SPY"
    assert observation.provider == "yahoo"
    assert observation.dataset == "SPY"
    assert observation.observed_at == "2026-05-20"
    assert observation.value == EXPECTED_CLOSE
    assert observation.unit == "price"
    assert observation.frequency == "daily"
    assert observation.source_ts == "2026-05-20"
    assert observation.latency_class == "daily"
    assert observation.data_quality == "ok"
    assert observation.provenance == [
        {
            "provider": "yahoo",
            "upstream": "Yahoo Finance",
            "source_url": "https://finance.yahoo.com/quote/SPY",
            "license_note": (
                "Yahoo Finance data is accessed through yfinance, an unofficial library not affiliated "
                "with Yahoo; Yahoo API usage is intended for personal use."
            ),
        }
    ]


def test_yahoo_latest_uses_daily_history_window_and_returns_latest_close(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeTicker.calls = []
    monkeypatch.setattr("macrodata.providers.yahoo.yf.Ticker", FakeTicker)
    provider = YahooPriceProvider(timeout_sec=LATEST_TIMEOUT_SEC)

    observation = provider.get_latest("QQQ")

    call = FakeTicker.calls[0]
    assert call["symbol"] == "QQQ"
    assert call["interval"] == "1d"
    assert call["auto_adjust"] is True
    assert call["repair"] is False
    assert call["timeout"] == LATEST_TIMEOUT_SEC
    assert call["raise_errors"] is True
    assert isinstance(datetime.fromisoformat(call["start"]), datetime)
    assert isinstance(datetime.fromisoformat(call["end"]), datetime)
    assert observation.series_key == "yahoo:QQQ"
    assert observation.observed_at == "2026-05-20"
    assert observation.value == EXPECTED_CLOSE


def test_yahoo_range_raises_no_data_for_empty_history(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("macrodata.providers.yahoo.yf.Ticker", EmptyTicker)
    provider = YahooPriceProvider()

    with pytest.raises(MacrodataError) as raised:
        provider.get_range("SPY", start="2026-05-20", end="2026-05-21")

    assert raised.value.code == "no_data"
    assert raised.value.provider == "yahoo"
    assert raised.value.exit_code == NO_DATA_EXIT_CODE
