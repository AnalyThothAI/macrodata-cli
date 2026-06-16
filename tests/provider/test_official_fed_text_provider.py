from __future__ import annotations

from datetime import date
from typing import cast

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.official_fed_text import OfficialFedTextProvider

FOMC_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
MONETARY_POLICY_RSS_URL = "https://www.federalreserve.gov/feeds/press_monetary.xml"
SPEECHES_RSS_URL = "https://www.federalreserve.gov/feeds/speeches.xml"
EXPECTED_SAME_DAY_SPEECH_COUNT = 3

FOMC_HTML = """
<html><body>
<h4>2026 FOMC Meetings</h4>
<div class="fomc-meeting">
  <div>January 27-28</div>
  <a href="/newsevents/pressreleases/monetary20260128a.htm">Statement</a>
  <div class="fomc-meeting__minutes">
    <strong>Minutes:</strong>
    <a href="/monetarypolicy/files/fomcminutes20260128.pdf">PDF</a> |
    <a href="/monetarypolicy/fomcminutes20260128.htm">HTML</a>
    <br> (Released February 18, 2026)
  </div>
</div>
<div class="fomc-meeting">
  <div>March 17-18*</div>
  <a href="/newsevents/pressreleases/monetary20260318a.htm">Statement</a>
  <div class="fomc-meeting__minutes">
    <strong>Minutes:</strong>
    <a href="/monetarypolicy/files/fomcminutes20260318.pdf">PDF</a> |
    <a href="/monetarypolicy/fomcminutes20260318.htm">HTML</a>
    <br> (Released April 08, 2026)
  </div>
</div>
</body></html>
"""

MONETARY_POLICY_RSS = """<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0"><channel>
  <item>
    <title>Minutes of the Federal Open Market Committee, March 17-18, 2026</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/pressreleases/monetary20260408a.htm]]></link>
    <description><![CDATA[Minutes of the Federal Open Market Committee, March 17-18, 2026]]></description>
    <category>Monetary Policy</category>
    <pubDate><![CDATA[Wed, 8 Apr 2026 18:00:00 GMT]]></pubDate>
  </item>
  <item>
    <title>Federal Reserve issues FOMC statement</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/pressreleases/monetary20260318a.htm]]></link>
    <description><![CDATA[Federal Reserve issues FOMC statement]]></description>
    <category>Monetary Policy</category>
    <pubDate><![CDATA[Wed, 18 Mar 2026 18:00:00 GMT]]></pubDate>
  </item>
</channel></rss>
"""

SPEECHES_RSS = """<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0"><channel>
  <item>
    <title>Bowman, A Framework for Practical Monetary Policy Decision Making</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/speech/bowman20260529a.htm]]></link>
    <description><![CDATA[Speech At the Reykjavik Economic Conference 2026]]></description>
    <category>Speech</category>
    <pubDate><![CDATA[Fri, 29 May 2026 13:10:00 GMT]]></pubDate>
  </item>
  <item>
    <title>Waller, Policy Risks Have Changed</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/speech/waller20260522a.htm]]></link>
    <description><![CDATA[Speech At The Centre for Central Banking Guest Lecture]]></description>
    <category>Speech</category>
    <pubDate><![CDATA[Fri, 22 May 2026 14:00:00 GMT]]></pubDate>
  </item>
</channel></rss>
"""

SAME_DAY_SPEECHES_RSS = """<?xml version="1.0" encoding="utf-8" ?>
<rss version="2.0"><channel>
  <item>
    <title>Waller, Update On Federal Reserve Bank Operations</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/speech/waller20260508a.htm]]></link>
    <description><![CDATA[Speech At the Hoover Institution Annual Monetary Policy Conference]]></description>
    <category>Speech</category>
    <pubDate><![CDATA[Fri, 8 May 2026 23:30:00 GMT]]></pubDate>
  </item>
  <item>
    <title>Bowman, When Regulation Reshapes Markets: The Migration of Corporate Lending</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/speech/bowman20260508a.htm]]></link>
    <description><![CDATA[Speech At the Hoover Institution Annual Monetary Policy Conference]]></description>
    <category>Speech</category>
    <pubDate><![CDATA[Fri, 8 May 2026 23:30:00 GMT]]></pubDate>
  </item>
  <item>
    <title>Cook, Perspectives on Tokenization and Implications for the Financial System</title>
    <link><![CDATA[https://www.federalreserve.gov/newsevents/speech/cook20260508a.htm]]></link>
    <description><![CDATA[Speech At the Central Bank of West African States Conference]]></description>
    <category>Speech</category>
    <pubDate><![CDATA[Fri, 8 May 2026 09:45:00 GMT]]></pubDate>
  </item>
</channel></rss>
"""


@respx.mock
def test_official_fed_text_provider_returns_latest_fomc_statement_and_minutes() -> None:
    respx.get(FOMC_CALENDAR_URL).mock(return_value=Response(200, text=FOMC_HTML))
    provider = OfficialFedTextProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    statement = provider.get_latest("fomc_statement_latest")
    minutes = provider.get_latest("fomc_minutes_latest")

    assert statement.series_key == "official_fed_text:fomc_statement_latest"
    assert statement.observed_at == "2026-03-18"
    assert statement.value == "FOMC statement"
    assert statement.unit == "document"
    assert statement.frequency == "event"
    assert statement.latency_class == "event"
    assert statement.provenance[0]["source_url"] == (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260318a.htm"
    )
    assert statement.provenance[0]["document_type"] == "fomc_statement"
    assert statement.provenance[0]["source_page_url"] == FOMC_CALENDAR_URL
    assert statement.provenance[0]["meeting_date"] == "2026-03-18"
    assert statement.provenance[0]["sep"] is True

    assert minutes.series_key == "official_fed_text:fomc_minutes_latest"
    assert minutes.observed_at == "2026-04-08"
    assert minutes.value == "FOMC minutes"
    assert minutes.provenance[0]["source_url"] == (
        "https://www.federalreserve.gov/monetarypolicy/fomcminutes20260318.htm"
    )
    assert minutes.provenance[0]["meeting_date"] == "2026-03-18"
    assert minutes.provenance[0]["released_at"] == "2026-04-08"


@respx.mock
def test_official_fed_text_provider_returns_rss_press_release_and_speech() -> None:
    respx.get(MONETARY_POLICY_RSS_URL).mock(return_value=Response(200, text=MONETARY_POLICY_RSS))
    respx.get(SPEECHES_RSS_URL).mock(return_value=Response(200, text=SPEECHES_RSS))
    provider = OfficialFedTextProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    press = provider.get_latest("monetary_policy_press_release_latest")
    speech = provider.get_latest("speech_latest")

    assert press.series_key == "official_fed_text:monetary_policy_press_release_latest"
    assert press.observed_at == "2026-04-08T18:00:00Z"
    assert press.value == "Minutes of the Federal Open Market Committee, March 17-18, 2026"
    assert press.provenance[0]["source_url"] == (
        "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260408a.htm"
    )
    assert press.provenance[0]["document_type"] == "monetary_policy_press_release"
    assert press.provenance[0]["description"] == "Minutes of the Federal Open Market Committee, March 17-18, 2026"

    assert speech.series_key == "official_fed_text:speech_latest"
    assert speech.observed_at == "2026-05-29T13:10:00Z"
    assert speech.value == "Bowman, A Framework for Practical Monetary Policy Decision Making"
    assert speech.provenance[0]["document_type"] == "speech"
    assert speech.provenance[0]["source_url"] == "https://www.federalreserve.gov/newsevents/speech/bowman20260529a.htm"


@respx.mock
def test_official_fed_text_provider_range_filters_documents_by_release_date() -> None:
    respx.get(FOMC_CALENDAR_URL).mock(return_value=Response(200, text=FOMC_HTML))
    respx.get(MONETARY_POLICY_RSS_URL).mock(return_value=Response(200, text=MONETARY_POLICY_RSS))
    provider = OfficialFedTextProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    statements = provider.get_range("fomc_statement_latest", start="2026-03-01", end="2026-03-31")
    press_releases = provider.get_range(
        "monetary_policy_press_release_latest",
        start="2026-04-01",
        end="2026-04-30",
    )

    assert [item.observed_at for item in statements] == ["2026-03-18"]
    assert [item.observed_at for item in press_releases] == ["2026-04-08T18:00:00Z"]


@respx.mock
def test_official_fed_text_rss_history_uses_timestamp_keys_for_same_day_documents() -> None:
    respx.get(SPEECHES_RSS_URL).mock(return_value=Response(200, text=SAME_DAY_SPEECHES_RSS))
    provider = OfficialFedTextProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    observations = provider.get_range("speech_latest", start="2026-05-08", end="2026-05-08")

    assert [item.observed_at for item in observations] == [
        "2026-05-08T09:45:00Z",
        "2026-05-08T23:30:00Z",
        "2026-05-08T23:30:01Z",
    ]
    assert [item.provenance[0]["published_at"] for item in observations] == [
        "2026-05-08T09:45:00Z",
        "2026-05-08T23:30:00Z",
        "2026-05-08T23:30:00Z",
    ]
    assert [item.source_ts for item in observations] == [
        "2026-05-08T09:45:00Z",
        "2026-05-08T23:30:00Z",
        "2026-05-08T23:30:00Z",
    ]
    assert len({item.idempotency_key for item in observations}) == EXPECTED_SAME_DAY_SPEECH_COUNT


def test_official_fed_text_provider_hard_rejects_removed_legacy_fed_page_series() -> None:
    provider = OfficialFedTextProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    with pytest.raises(MacrodataError) as exc_info:
        provider.get_latest("fed_page_latest")

    assert exc_info.value.code == "unknown_series"


def test_official_fed_text_provider_uses_extended_timeout_for_fed_text_sources() -> None:
    calls: list[float | None] = []

    class FakeHttpClient:
        timeout_sec = 10.0

        def get_text(
            self,
            _url: str,
            *,
            provider: str,
            timeout_sec: float | None = None,
            params: dict[str, object] | None = None,
        ) -> str:
            del provider, params
            calls.append(timeout_sec)
            return SPEECHES_RSS

    provider = OfficialFedTextProvider(
        http_client=cast(MacrodataHttpClient, FakeHttpClient()),
        today=date(2026, 6, 16),
    )

    provider.get_latest("speech_latest")

    assert calls == [30.0]
