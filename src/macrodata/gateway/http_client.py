from __future__ import annotations

from typing import Any

import httpx

from macrodata.core.errors import MacrodataError


class MacrodataHttpClient:
    def __init__(self, *, timeout_sec: float = 10.0) -> None:
        self.timeout_sec = timeout_sec

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, provider: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout_sec) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise MacrodataError(
                code="provider_timeout",
                message=f"{provider} request timed out after {self.timeout_sec:.1f} seconds",
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
