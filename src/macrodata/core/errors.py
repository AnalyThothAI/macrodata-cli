from __future__ import annotations


class MacrodataError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool = False,
        provider: str | None = None,
        exit_code: int = 3,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.provider = provider
        self.exit_code = exit_code


class ValidationError(MacrodataError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(code=code, message=message, retryable=False, provider=None, exit_code=2)
