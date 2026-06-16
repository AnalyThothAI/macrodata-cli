from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, ClassVar
from urllib.parse import urljoin

from macrodata.core.errors import MacrodataError
from macrodata.core.models import MacroObservation, ProviderSmokeResult
from macrodata.gateway.http_client import MacrodataHttpClient

FED_BASE_URL = "https://www.federalreserve.gov"
FED_FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FED_MONETARY_POLICY_RSS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
FED_SPEECHES_RSS_URL = "https://www.federalreserve.gov/feeds/speeches.xml"
FED_TEXT_TIMEOUT_SEC = 30.0

_FOMC_YEAR_RE = re.compile(r"^(20\d{2})\s+FOMC\s+Meetings$", re.IGNORECASE)
_MEETING_DATE_RE = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?P<start>\d{1,2})(?:-(?P<end>\d{1,2}))?(?P<sep>\*)?",
    re.IGNORECASE,
)
_RELEASED_RE = re.compile(
    r"Released\s+(?P<released>[A-Za-z]+\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
_STATEMENT_URL_RE = re.compile(r"/newsevents/pressreleases/monetary(?P<stamp>\d{8})a\.htm$")
_MINUTES_URL_RE = re.compile(r"/monetarypolicy/fomcminutes(?P<stamp>\d{8})\.htm$")
_DECEMBER = 12

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class _FedTextDataset:
    dataset: str
    source: str
    source_url: str
    document_type: str
    title: str


@dataclass(frozen=True)
class _FedTextDocument:
    observed_at: str
    source_ts: str
    sort_at: datetime
    title: str
    source_url: str
    source_page_url: str
    document_type: str
    description: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class _Link:
    href: str
    text: str


@dataclass(frozen=True)
class _MeetingBlock:
    year: int | None
    texts: list[str]
    links: list[_Link]


@dataclass
class _MeetingBuilder:
    year: int | None
    texts: list[str]
    links: list[_Link]


_DATASETS = {
    "fomc_statement_latest": _FedTextDataset(
        dataset="fomc_statement_latest",
        source="fomc_calendar",
        source_url=FED_FOMC_CALENDAR_URL,
        document_type="fomc_statement",
        title="FOMC statement",
    ),
    "fomc_minutes_latest": _FedTextDataset(
        dataset="fomc_minutes_latest",
        source="fomc_calendar",
        source_url=FED_FOMC_CALENDAR_URL,
        document_type="fomc_minutes",
        title="FOMC minutes",
    ),
    "monetary_policy_press_release_latest": _FedTextDataset(
        dataset="monetary_policy_press_release_latest",
        source="rss",
        source_url=FED_MONETARY_POLICY_RSS_URL,
        document_type="monetary_policy_press_release",
        title="Fed monetary policy press release",
    ),
    "speech_latest": _FedTextDataset(
        dataset="speech_latest",
        source="rss",
        source_url=FED_SPEECHES_RSS_URL,
        document_type="speech",
        title="Fed speech",
    ),
}


class OfficialFedTextProvider:
    provider_name = "official_fed_text"

    def __init__(
        self,
        *,
        http_client: MacrodataHttpClient,
        today: date | None = None,
        text_timeout_sec: float = FED_TEXT_TIMEOUT_SEC,
    ) -> None:
        self._http_client = http_client
        self._today = today
        self._text_timeout_sec = float(text_timeout_sec)
        self._text_cache: dict[str, str] = {}

    def get_latest(self, dataset: str) -> MacroObservation:
        config = self._dataset(dataset)
        today = self._current_date()
        documents = [document for document in self._documents(config) if document.sort_at.date() <= today]
        if not documents:
            raise MacrodataError(
                code="no_data",
                message=f"Official Fed text returned no document for {dataset}",
                retryable=True,
                provider=self.provider_name,
                exit_code=4,
            )
        latest = max(documents, key=lambda item: item.sort_at)
        return self._observation(dataset=config.dataset, document=latest)

    def get_range(self, dataset: str, *, start: str, end: str) -> list[MacroObservation]:
        config = self._dataset(dataset)
        start_date = self._parse_iso_date(start, label="start")
        end_date = self._parse_iso_date(end, label="end")
        documents = [
            document
            for document in self._documents(config)
            if start_date <= document.sort_at.date() <= end_date
        ]
        return [
            self._observation(dataset=config.dataset, document=document)
            for document in sorted(documents, key=lambda item: item.sort_at)
        ]

    def smoke(self) -> ProviderSmokeResult:
        checked_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        try:
            latest = self.get_latest("fomc_statement_latest")
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
            sample_dataset="fomc_statement_latest",
            sample_source_ts=latest.source_ts,
        )

    def _dataset(self, dataset: str) -> _FedTextDataset:
        config = _DATASETS.get(dataset)
        if config is not None:
            return config
        raise MacrodataError(
            code="unknown_series",
            message=f"Official Fed text dataset is not supported: {dataset}",
            provider=self.provider_name,
            exit_code=2,
        )

    def _documents(self, config: _FedTextDataset) -> list[_FedTextDocument]:
        if config.source == "fomc_calendar":
            return self._fomc_documents(config)
        if config.source == "rss":
            return self._rss_documents(config)
        raise MacrodataError(
            code="unknown_series",
            message=f"Official Fed text source is not supported: {config.source}",
            provider=self.provider_name,
            exit_code=2,
        )

    def _fomc_documents(self, config: _FedTextDataset) -> list[_FedTextDocument]:
        blocks = _FomcMeetingParser().parse(self._get_text(config.source_url))
        documents: list[_FedTextDocument] = []
        for block in blocks:
            parsed = _parse_meeting_block(block)
            if parsed is None:
                continue
            meeting_date, sep, statement_url, minutes_url, released_at = parsed
            if config.document_type == "fomc_statement" and statement_url:
                documents.append(
                    _FedTextDocument(
                        observed_at=meeting_date.isoformat(),
                        source_ts=meeting_date.isoformat(),
                        sort_at=_sort_datetime(meeting_date),
                        title=config.title,
                        source_url=statement_url,
                        source_page_url=config.source_url,
                        document_type=config.document_type,
                        description=None,
                        metadata={"meeting_date": meeting_date.isoformat(), "sep": sep},
                    )
                )
            if config.document_type == "fomc_minutes" and minutes_url and released_at is not None:
                documents.append(
                    _FedTextDocument(
                        observed_at=released_at.isoformat(),
                        source_ts=released_at.isoformat(),
                        sort_at=_sort_datetime(released_at),
                        title=config.title,
                        source_url=minutes_url,
                        source_page_url=config.source_url,
                        document_type=config.document_type,
                        description=None,
                        metadata={
                            "meeting_date": meeting_date.isoformat(),
                            "released_at": released_at.isoformat(),
                            "sep": sep,
                        },
                    )
                )
        return documents

    def _rss_documents(self, config: _FedTextDataset) -> list[_FedTextDocument]:
        raw_documents: list[tuple[datetime, str, str, str | None, str | None]] = []
        for item in _RssItemParser().parse(self._get_text(config.source_url)):
            pub_date = _parse_rss_date(item.get("pubdate", ""), provider=self.provider_name)
            title = _clean_text(item.get("title", ""))
            link = _clean_text(item.get("link", ""))
            if not title or not link:
                continue
            raw_documents.append(
                (
                    pub_date,
                    title,
                    link,
                    _clean_text(item.get("description", "")) or None,
                    _clean_text(item.get("category", "")) or None,
                )
            )

        documents: list[_FedTextDocument] = []
        used_observed_at: set[datetime] = set()
        for pub_date, title, link, description, category in sorted(
            raw_documents,
            key=lambda item: (item[0], item[2], item[1]),
        ):
            observed_at = pub_date
            while observed_at in used_observed_at:
                observed_at += timedelta(seconds=1)
            used_observed_at.add(observed_at)
            documents.append(
                _FedTextDocument(
                    observed_at=_format_utc(observed_at),
                    source_ts=_format_utc(pub_date),
                    sort_at=observed_at,
                    title=title,
                    source_url=link,
                    source_page_url=config.source_url,
                    document_type=config.document_type,
                    description=description,
                    metadata={
                        "published_at": _format_utc(pub_date),
                        "category": category,
                    },
                )
            )
        return documents

    def _observation(self, *, dataset: str, document: _FedTextDocument) -> MacroObservation:
        provenance: dict[str, Any] = {
            "provider": self.provider_name,
            "source_url": document.source_url,
            "source_page_url": document.source_page_url,
            "document_type": document.document_type,
            "document_title": document.title,
            **document.metadata,
        }
        if document.description:
            provenance["description"] = document.description
        return MacroObservation(
            series_key=f"{self.provider_name}:{dataset}",
            provider=self.provider_name,
            dataset=dataset,
            observed_at=document.observed_at,
            value=document.title,
            unit="document",
            frequency="event",
            source_ts=document.source_ts,
            realtime_start=None,
            realtime_end=None,
            latency_class="event",
            data_quality="ok",
            provenance=[provenance],
        )

    def _get_text(self, url: str) -> str:
        cached = self._text_cache.get(url)
        if cached is not None:
            return cached
        text = self._http_client.get_text(
            url,
            provider=self.provider_name,
            timeout_sec=max(self._http_client.timeout_sec, self._text_timeout_sec),
        )
        self._text_cache[url] = text
        return text

    def _current_date(self) -> date:
        return self._today or datetime.now(UTC).date()

    def _parse_iso_date(self, value: str, *, label: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise MacrodataError(
                code="provider_invalid_request",
                message=f"Official Fed text {label} date is invalid: {value}",
                retryable=False,
                provider=self.provider_name,
                exit_code=2,
            ) from exc


class _FomcMeetingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_year: int | None = None
        self._meeting_depth = 0
        self._builder: _MeetingBuilder | None = None
        self._active_href: str | None = None
        self._active_text: list[str] = []
        self._blocks: list[_MeetingBlock] = []

    def parse(self, html: str) -> list[_MeetingBlock]:
        self.feed(html)
        if self._builder is not None:
            self._blocks.append(
                _MeetingBlock(
                    year=self._builder.year,
                    texts=list(self._builder.texts),
                    links=list(self._builder.links),
                )
            )
            self._builder = None
        return self._blocks

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "div" and _has_class(attrs_dict.get("class"), "fomc-meeting"):
            self._builder = _MeetingBuilder(year=self._current_year, texts=[], links=[])
            self._meeting_depth = 1
            return
        if self._builder is not None and tag == "div":
            self._meeting_depth += 1

        if self._builder is not None and tag == "a":
            self._active_href = urljoin(FED_BASE_URL, attrs_dict.get("href") or "")
            self._active_text = []

    def handle_endtag(self, tag: str) -> None:
        if self._builder is not None and tag == "a" and self._active_href is not None:
            self._builder.links.append(
                _Link(href=self._active_href, text=_clean_text(" ".join(self._active_text)))
            )
            self._active_href = None
            self._active_text = []

        if self._builder is not None and tag == "div":
            self._meeting_depth -= 1
            if self._meeting_depth <= 0:
                self._blocks.append(
                    _MeetingBlock(
                        year=self._builder.year,
                        texts=list(self._builder.texts),
                        links=list(self._builder.links),
                    )
                )
                self._builder = None
                self._meeting_depth = 0

    def handle_data(self, data: str) -> None:
        cleaned = _clean_text(data)
        if not cleaned:
            return
        year_match = _FOMC_YEAR_RE.match(cleaned)
        if year_match is not None:
            self._current_year = int(year_match.group(1))

        if self._builder is not None:
            self._builder.texts.append(cleaned)
        if self._active_href is not None:
            self._active_text.append(cleaned)


class _RssItemParser(HTMLParser):
    _fields: ClassVar[set[str]] = {"title", "link", "description", "category", "pubdate"}

    def __init__(self) -> None:
        super().__init__()
        self._items: list[dict[str, list[str]]] = []
        self._item: dict[str, list[str]] | None = None
        self._active_field: str | None = None

    def parse(self, text: str) -> list[dict[str, str]]:
        self.feed(text.lstrip("\ufeff"))
        return [
            {field: _clean_text(" ".join(parts)) for field, parts in item.items()}
            for item in self._items
        ]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized == "item":
            self._item = {}
            self._active_field = None
            return
        if self._item is not None and normalized in self._fields:
            self._active_field = normalized
            self._item.setdefault(normalized, [])

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized == "item" and self._item is not None:
            self._items.append(self._item)
            self._item = None
            self._active_field = None
            return
        if normalized == self._active_field:
            self._active_field = None

    def handle_data(self, data: str) -> None:
        self._append_text(data)

    def unknown_decl(self, data: str) -> None:
        if data.startswith("CDATA["):
            self._append_text(data.removeprefix("CDATA["))

    def _append_text(self, data: str) -> None:
        if self._item is None or self._active_field is None:
            return
        cleaned = _clean_text(data)
        if cleaned:
            self._item.setdefault(self._active_field, []).append(cleaned)


def _parse_meeting_block(
    block: _MeetingBlock,
) -> tuple[date, bool, str | None, str | None, date | None] | None:
    joined_text = " ".join(block.texts)
    statement_url = _first_matching_url(block.links, _STATEMENT_URL_RE)
    minutes_url = _first_matching_url(block.links, _MINUTES_URL_RE)
    meeting_date = _meeting_date(block=block, joined_text=joined_text, fallback_url=statement_url or minutes_url)
    if meeting_date is None:
        return None
    release_date = _released_date(joined_text)
    sep = _meeting_sep(joined_text)
    return meeting_date, sep, statement_url, minutes_url, release_date


def _first_matching_url(links: list[_Link], pattern: re.Pattern[str]) -> str | None:
    for link in links:
        if pattern.search(link.href):
            return link.href
    return None


def _meeting_date(*, block: _MeetingBlock, joined_text: str, fallback_url: str | None) -> date | None:
    match = _MEETING_DATE_RE.search(joined_text)
    if match is not None:
        year = block.year or _year_from_url(fallback_url)
        if year is None:
            return None
        month = _MONTHS[match.group("month").lower()]
        start_day = int(match.group("start"))
        end_day = int(match.group("end") or start_day)
        event_month = month
        event_year = year
        if end_day < start_day:
            event_month = 1 if month == _DECEMBER else month + 1
            event_year = year + 1 if month == _DECEMBER else year
        return date(event_year, event_month, end_day)
    return _date_from_url(fallback_url)


def _meeting_sep(joined_text: str) -> bool:
    match = _MEETING_DATE_RE.search(joined_text)
    return bool(match and match.group("sep"))


def _released_date(joined_text: str) -> date | None:
    match = _RELEASED_RE.search(joined_text)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group("released"), "%B %d, %Y").date()
    except ValueError:
        return None


def _date_from_url(url: str | None) -> date | None:
    stamp = _stamp_from_url(url)
    if stamp is None:
        return None
    try:
        return datetime.strptime(stamp, "%Y%m%d").date()
    except ValueError:
        return None


def _year_from_url(url: str | None) -> int | None:
    stamp = _stamp_from_url(url)
    if stamp is None:
        return None
    return int(stamp[:4])


def _stamp_from_url(url: str | None) -> str | None:
    if url is None:
        return None
    for pattern in (_STATEMENT_URL_RE, _MINUTES_URL_RE):
        match = pattern.search(url)
        if match is not None:
            return match.group("stamp")
    return None


def _parse_rss_date(raw_value: str, *, provider: str) -> datetime:
    try:
        parsed = parsedate_to_datetime(raw_value)
    except (TypeError, ValueError) as exc:
        raise MacrodataError(
            code="provider_parse_error",
            message=f"Official Fed RSS pubDate is invalid: {raw_value}",
            retryable=False,
            provider=provider,
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _sort_datetime(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _has_class(raw_class: str | None, class_name: str) -> bool:
    if raw_class is None:
        return False
    return class_name in raw_class.split()


def _clean_text(value: str) -> str:
    return " ".join(unescape(value).split())
