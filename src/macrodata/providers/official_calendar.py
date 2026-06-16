from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

FED_FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BEA_RELEASE_DATES_URL = "https://apps.bea.gov/API/signup/release_dates.json"

_NEW_YORK = ZoneInfo("America/New_York")
_FOMC_YEAR_RE = re.compile(r"^(20\d{2})\s+FOMC\s+Meetings$", re.IGNORECASE)
_FOMC_DAY_RE = re.compile(r"^(?P<start>\d{1,2})(?:-(?P<end>\d{1,2}))?(?P<sep>\*)?(?:\s+\(.+\))?$")
_DECEMBER = 12

_MONTHS = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


@dataclass(frozen=True)
class _CalendarDataset:
    dataset: str
    source: str
    title: str
    match_prefix: str
    source_url: str
    event_time_et: str | None
    importance: str


@dataclass(frozen=True)
class _CalendarEvent:
    event_date: date
    title: str
    time_et: str | None
    source_url: str
    event_type: str
    importance: str
    metadata: dict[str, Any]


_DATASETS = {
    "fomc_decision_next": _CalendarDataset(
        dataset="fomc_decision_next",
        source="fed_fomc",
        title="FOMC decision",
        match_prefix="FOMC decision",
        source_url=FED_FOMC_CALENDAR_URL,
        event_time_et="2:00 PM",
        importance="high",
    ),
    "bea_gdp_next": _CalendarDataset(
        dataset="bea_gdp_next",
        source="bea",
        title="Gross Domestic Product",
        match_prefix="Gross Domestic Product",
        source_url=BEA_RELEASE_DATES_URL,
        event_time_et=None,
        importance="high",
    ),
    "bea_pce_next": _CalendarDataset(
        dataset="bea_pce_next",
        source="bea",
        title="Personal Income and Outlays",
        match_prefix="Personal Income and Outlays",
        source_url=BEA_RELEASE_DATES_URL,
        event_time_et=None,
        importance="high",
    ),
}


class OfficialCalendarProvider:
    provider_name = "official_calendar"

    def __init__(self, *, http_client: MacrodataHttpClient, today: date | None = None) -> None:
        self._http_client = http_client
        self._today = today
        self._text_cache: dict[str, str] = {}
        self._json_cache: dict[str, dict[str, Any]] = {}

    def get_latest(self, dataset: str) -> MacroObservation:
        config = self._dataset(dataset)
        today = self._current_date()
        future_events = [event for event in self._events(config) if event.event_date >= today]
        if not future_events:
            raise MacrodataError(
                code="no_data",
                message=f"Official calendar returned no future event for {dataset}",
                retryable=True,
                provider=self.provider_name,
                exit_code=4,
            )
        return self._observation(dataset=config.dataset, event=min(future_events, key=lambda item: item.event_date))

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        config = self._dataset(dataset)
        start_date = self._parse_iso_date(start, label="start")
        end_date = self._parse_iso_date(end, label="end")
        events = [
            event
            for event in self._events(config)
            if start_date <= event.event_date <= end_date
        ]
        return [
            self._observation(dataset=config.dataset, event=event)
            for event in sorted(events, key=lambda item: item.event_date)
        ]

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("fomc_decision_next")
        except MacrodataError as exc:
            return ProviderSmokeResult(
                provider=self.provider_name,
                ok=False,
                latency_ms=0,
                checked_at=checked_at,
                error_code=exc.code,
                message=exc.message,
            )
        return ProviderSmokeResult(
            provider=self.provider_name,
            ok=True,
            latency_ms=0,
            checked_at=checked_at,
            sample_dataset="fomc_decision_next",
            sample_source_ts=latest.source_ts,
        )

    def _dataset(self, dataset: str) -> _CalendarDataset:
        config = _DATASETS.get(dataset)
        if config is not None:
            return config
        raise MacrodataError(
            code="unknown_series",
            message=f"Official calendar dataset is not supported: {dataset}",
            provider=self.provider_name,
            exit_code=2,
        )

    def _events(self, config: _CalendarDataset) -> list[_CalendarEvent]:
        if config.source == "fed_fomc":
            return self._fomc_events(config)
        if config.source == "bea":
            return self._bea_events(config)
        raise MacrodataError(
            code="unknown_series",
            message=f"Official calendar source is not supported: {config.source}",
            provider=self.provider_name,
            exit_code=2,
        )

    def _fomc_events(self, config: _CalendarDataset) -> list[_CalendarEvent]:
        lines = _html_lines(self._get_text(config.source_url))
        events: list[_CalendarEvent] = []
        current_year: int | None = None
        current_month: int | None = None
        for line in lines:
            year_match = _FOMC_YEAR_RE.match(line)
            if year_match:
                current_year = int(year_match.group(1))
                current_month = None
                continue
            month = _month_number(line)
            if month is not None:
                current_month = month
                continue
            if current_year is None or current_month is None or "notation vote" in line.lower():
                continue
            day_match = _FOMC_DAY_RE.match(line)
            if day_match is None:
                continue
            start_day = int(day_match.group("start"))
            end_day = int(day_match.group("end") or start_day)
            event_month = current_month
            if end_day < start_day:
                event_month = 1 if current_month == _DECEMBER else current_month + 1
            events.append(
                _CalendarEvent(
                    event_date=date(current_year, event_month, end_day),
                    title=config.title,
                    time_et=config.event_time_et,
                    source_url=config.source_url,
                    event_type=config.dataset,
                    importance=config.importance,
                    metadata={"sep": bool(day_match.group("sep"))},
                )
            )
        return events

    def _bea_events(self, config: _CalendarDataset) -> list[_CalendarEvent]:
        payload = self._get_json(config.source_url)
        release = payload.get(config.match_prefix)
        if not isinstance(release, dict):
            raise MacrodataError(
                code="provider_parse_error",
                message=f"BEA release calendar is missing {config.match_prefix}",
                retryable=False,
                provider=self.provider_name,
            )
        raw_dates = release.get("release_dates")
        if not isinstance(raw_dates, list):
            raise MacrodataError(
                code="provider_parse_error",
                message=f"BEA release_dates for {config.match_prefix} must be a list",
                retryable=False,
                provider=self.provider_name,
            )
        events: list[_CalendarEvent] = []
        for raw_date in raw_dates:
            event_datetime = _parse_bea_datetime(raw_date)
            events.append(
                _CalendarEvent(
                    event_date=event_datetime.date(),
                    title=config.title,
                    time_et=event_datetime.strftime("%I:%M %p"),
                    source_url=config.source_url,
                    event_type=config.dataset,
                    importance=config.importance,
                    metadata={},
                )
            )
        return events

    def _observation(self, *, dataset: str, event: _CalendarEvent) -> MacroObservation:
        today = self._current_date()
        days_until = (event.event_date - today).days
        provenance = {
            "provider": self.provider_name,
            "source_url": event.source_url,
            "event_title": event.title,
            "event_time_et": event.time_et,
            "event_type": event.event_type,
            "importance": event.importance,
            **event.metadata,
        }
        return MacroObservation(
            series_key=f"{self.provider_name}:{dataset}",
            provider=self.provider_name,
            dataset=dataset,
            observed_at=event.event_date.isoformat(),
            value=days_until,
            unit="days_until",
            frequency="event",
            source_ts=today.isoformat(),
            realtime_start=None,
            realtime_end=None,
            latency_class="calendar",
            data_quality="ok",
            provenance=[provenance],
        )

    def _get_text(self, url: str) -> str:
        cached = self._text_cache.get(url)
        if cached is not None:
            return cached
        text = self._http_client.get_text(url, provider=self.provider_name)
        self._text_cache[url] = text
        return text

    def _get_json(self, url: str) -> dict[str, Any]:
        cached = self._json_cache.get(url)
        if cached is not None:
            return cached
        payload = self._http_client.get_json(url, provider=self.provider_name)
        self._json_cache[url] = payload
        return payload

    def _current_date(self) -> date:
        return self._today or datetime.now(UTC).date()

    def _parse_iso_date(self, value: str, *, label: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise MacrodataError(
                code="provider_invalid_request",
                message=f"Official calendar {label} date is invalid: {value}",
                retryable=False,
                provider=self.provider_name,
                exit_code=2,
            ) from exc


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = " ".join(data.split())
        if cleaned:
            self._parts.append(cleaned)

    def lines(self) -> list[str]:
        return self._parts


def _html_lines(html: str) -> list[str]:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.lines()


def _month_number(value: str) -> int | None:
    normalized = value.strip().lower()
    if "/" in normalized:
        parts = [part.strip() for part in normalized.split("/") if part.strip()]
        if parts:
            normalized = parts[-1]
    return _MONTHS.get(normalized)


def _parse_bea_datetime(raw_value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"BEA release date is invalid: {raw_value}",
            retryable=False,
            provider="official_calendar",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(_NEW_YORK)
