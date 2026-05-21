from __future__ import annotations

import httpx
import pytest
import respx

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient


def test_unsupported_protocol_is_wrapped_as_non_retryable_request_error() -> None:
    client = MacrodataHttpClient(timeout_sec=1.0)

    with pytest.raises(MacrodataError) as raised:
        client.get_json("mailto:test@example.com", provider="fred")

    assert raised.value.code == "provider_request_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "fred"
    assert "UnsupportedProtocol" in raised.value.message


def test_invalid_url_is_wrapped_as_non_retryable_invalid_request() -> None:
    client = MacrodataHttpClient(timeout_sec=1.0)

    with pytest.raises(MacrodataError) as raised:
        client.get_json("http://example.com:abc", provider="fred")

    assert raised.value.code == "provider_invalid_request"
    assert raised.value.retryable is False
    assert raised.value.provider == "fred"


@respx.mock
def test_http_503_is_retryable_http_error() -> None:
    respx.get("https://example.test/unavailable").mock(return_value=httpx.Response(503))
    client = MacrodataHttpClient(timeout_sec=1.0)

    with pytest.raises(MacrodataError) as raised:
        client.get_json("https://example.test/unavailable", provider="fred")

    assert raised.value.code == "provider_http_error"
    assert raised.value.retryable is True
    assert raised.value.provider == "fred"


@respx.mock
def test_invalid_json_is_non_retryable_parse_error() -> None:
    respx.get("https://example.test/not-json").mock(return_value=httpx.Response(200, text="not-json"))
    client = MacrodataHttpClient(timeout_sec=1.0)

    with pytest.raises(MacrodataError) as raised:
        client.get_json("https://example.test/not-json", provider="fred")

    assert raised.value.code == "provider_parse_error"
    assert raised.value.retryable is False
    assert raised.value.provider == "fred"


@respx.mock
def test_non_dict_json_is_wrapped_in_data_key() -> None:
    respx.get("https://example.test/list").mock(return_value=httpx.Response(200, json=[1, 2, 3]))
    client = MacrodataHttpClient(timeout_sec=1.0)

    payload = client.get_json("https://example.test/list", provider="fred")

    assert payload == {"data": [1, 2, 3]}
