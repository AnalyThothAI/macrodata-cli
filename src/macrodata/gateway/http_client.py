from __future__ import annotations

from typing import Any

import httpx

from macrodata.core.errors import MacrodataError

DEFAULT_HEADERS = {"User-Agent": "macrodata-cli/0.1"}


class MacrodataHttpClient:
    def __init__(self, *, timeout_sec: float = 10.0) -> None:
        self.timeout_sec = timeout_sec

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        provider: str,
        timeout_sec: float | None = None,
    ) -> dict[str, Any]:
        request_timeout = self._request_timeout(timeout_sec)
        try:
            with httpx.Client(timeout=request_timeout, headers=DEFAULT_HEADERS, trust_env=False) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise MacrodataError(
                code="provider_timeout",
                message=f"{provider} request timed out after {request_timeout:.1f} seconds",
                retryable=True,
                provider=provider,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MacrodataError(
                code="provider_http_error",
                message=f"{provider} returned HTTP {exc.response.status_code}",
                retryable=exc.response.status_code in {429, 500, 502, 503, 504},
                provider=provider,
            ) from exc
        except httpx.InvalidURL as exc:
            raise MacrodataError(
                code="provider_invalid_request",
                message=f"{provider} request URL is invalid",
                retryable=False,
                provider=provider,
            ) from exc
        except httpx.RequestError as exc:
            raise MacrodataError(
                code="provider_request_error",
                message=f"{provider} request failed: {type(exc).__name__}",
                retryable=not isinstance(exc, (httpx.UnsupportedProtocol, httpx.LocalProtocolError)),
                provider=provider,
            ) from exc
        except ValueError as exc:
            raise MacrodataError(
                code="provider_parse_error",
                message=f"{provider} returned invalid JSON",
                retryable=False,
                provider=provider,
            ) from exc
        return payload if isinstance(payload, dict) else {"data": payload}

    def get_text(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        provider: str,
        timeout_sec: float | None = None,
    ) -> str:
        request_timeout = self._request_timeout(timeout_sec)
        try:
            with httpx.Client(
                timeout=request_timeout,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
                trust_env=False,
            ) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MacrodataError(
                code="provider_timeout",
                message=f"{provider} request timed out after {request_timeout:.1f} seconds",
                retryable=True,
                provider=provider,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise MacrodataError(
                code="provider_http_error",
                message=f"{provider} returned HTTP {exc.response.status_code}",
                retryable=exc.response.status_code in {429, 500, 502, 503, 504},
                provider=provider,
            ) from exc
        except httpx.InvalidURL as exc:
            raise MacrodataError(
                code="provider_invalid_request",
                message=f"{provider} request URL is invalid",
                retryable=False,
                provider=provider,
            ) from exc
        except httpx.RequestError as exc:
            raise MacrodataError(
                code="provider_request_error",
                message=f"{provider} request failed: {type(exc).__name__}",
                retryable=not isinstance(exc, (httpx.UnsupportedProtocol, httpx.LocalProtocolError)),
                provider=provider,
            ) from exc
        return response.text

    def _request_timeout(self, timeout_sec: float | None) -> float:
        return self.timeout_sec if timeout_sec is None else float(timeout_sec)
