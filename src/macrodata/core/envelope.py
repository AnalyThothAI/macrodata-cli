from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from macrodata.core.errors import MacrodataError


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def success_envelope(
    *,
    command: str,
    data: dict[str, Any],
    source_chain: list[str],
    latency_ms: int,
    cache: str = "none",
    data_quality: str = "ok",
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "request_id": str(uuid4()),
        "asof": _now_iso(),
        "data": data,
        "meta": {
            "source_chain": source_chain,
            "cache": cache,
            "latency_ms": latency_ms,
            "data_quality": data_quality,
            "reason_codes": list(reason_codes or []),
        },
    }


def error_envelope(
    *,
    command: str,
    error: MacrodataError,
    source_chain: list[str],
    latency_ms: int,
) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "request_id": str(uuid4()),
        "asof": _now_iso(),
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "provider": error.provider,
        },
        "meta": {
            "source_chain": source_chain,
            "cache": "none",
            "latency_ms": latency_ms,
            "data_quality": "unavailable",
            "reason_codes": [error.code],
        },
    }
