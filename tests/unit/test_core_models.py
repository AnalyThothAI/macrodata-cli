from __future__ import annotations

from macrodata.core.envelope import error_envelope, success_envelope
from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation
from macrodata.core.series_key import parse_series_key


def test_parse_series_key() -> None:
    parsed = parse_series_key("fred:DGS10")

    assert parsed.provider == "fred"
    assert parsed.dataset == "DGS10"
    assert parsed.value == "fred:DGS10"


def test_observation_idempotency_key() -> None:
    observation = MacroObservation(
        series_key="fred:DGS10",
        provider="fred",
        dataset="DGS10",
        observed_at="2026-05-20",
        value=4.57,
        unit="percent",
        frequency="daily",
        source_ts="2026-05-20",
        realtime_start=None,
        realtime_end=None,
        latency_class="eod",
        data_quality="ok",
        provenance=[{"provider": "fred", "source_url": "https://api.stlouisfed.org"}],
    )

    assert observation.idempotency_key == "fred:DGS10:2026-05-20"


def test_success_envelope_shape() -> None:
    payload = success_envelope(command="doctor", data={"status": "ok"}, source_chain=["local"], latency_ms=1)

    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["data"] == {"status": "ok"}
    assert payload["meta"]["source_chain"] == ["local"]


def test_error_envelope_shape() -> None:
    exc = MacrodataError(code="provider_timeout", message="timed out", retryable=True, provider="fred")
    payload = error_envelope(command="fetch.series", error=exc, source_chain=["fred"], latency_ms=10)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "provider_timeout"
    assert payload["error"]["retryable"] is True
    assert payload["meta"]["data_quality"] == "unavailable"
