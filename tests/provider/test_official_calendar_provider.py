from __future__ import annotations

from datetime import date

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.official_calendar import OfficialCalendarProvider

FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
BEA_RELEASE_DATES_URL = "https://apps.bea.gov/API/signup/release_dates.json"
BLS_CPI_URL = "https://www.bls.gov/schedule/news_release/cpi.htm"
BLS_EMPLOYMENT_URL = "https://www.bls.gov/schedule/news_release/empsit.htm"
BLS_PPI_URL = "https://www.bls.gov/schedule/news_release/ppi.htm"


FOMC_HTML = """
<html><body>
<h4>2026 FOMC Meetings</h4>
<p>June</p>
<p>16-17*</p>
<p>July</p>
<p>28-29</p>
<p>* Meeting associated with a Summary of Economic Projections.</p>
</body></html>
"""

BEA_JSON = {
    "Gross Domestic Product": {
        "release_dates": [
            "2026-05-28T12:30:00+00:00",
            "2026-06-25T12:30:00+00:00",
            "2026-07-30T12:30:00+00:00",
        ]
    },
    "Personal Income and Outlays": {
        "release_dates": [
            "2026-05-28T12:30:00+00:00",
            "2026-06-25T12:30:00+00:00",
            "2026-07-30T12:30:00+00:00",
        ]
    },
}

JUNE_BEA_DAYS_UNTIL = 9
JUNE_BLS_CPI_DAYS_UNTIL = 28

BLS_RELEASE_HTML = """
<html><body>
<table>
<tr><th>Reference Month</th><th>Release Date</th><th>Release Time</th></tr>
<tr><td>May 2026</td><td>Jun. 10, 2026</td><td>08:30 AM</td></tr>
<tr><td>June 2026</td><td>Jul. 14, 2026</td><td>08:30 AM</td></tr>
</table>
</body></html>
"""


@respx.mock
def test_official_calendar_provider_returns_next_fomc_decision_event() -> None:
    respx.get(FOMC_URL).mock(return_value=Response(200, text=FOMC_HTML))
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    observation = provider.get_latest("fomc_decision_next")

    assert observation.series_key == "official_calendar:fomc_decision_next"
    assert observation.observed_at == "2026-06-17"
    assert observation.value == 1
    assert observation.unit == "days_until"
    assert observation.frequency == "event"
    assert observation.latency_class == "calendar"
    assert observation.provenance[0]["source_url"] == FOMC_URL
    assert observation.provenance[0]["event_title"] == "FOMC decision"
    assert observation.provenance[0]["event_time_et"] == "2:00 PM"
    assert observation.provenance[0]["sep"] is True


@respx.mock
def test_official_calendar_provider_returns_next_bea_gdp_and_pce_events_from_json() -> None:
    respx.get(BEA_RELEASE_DATES_URL).mock(return_value=Response(200, json=BEA_JSON))
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    gdp = provider.get_latest("bea_gdp_next")
    pce = provider.get_latest("bea_pce_next")

    assert gdp.observed_at == "2026-06-25"
    assert gdp.value == JUNE_BEA_DAYS_UNTIL
    assert gdp.provenance[0]["source_url"] == BEA_RELEASE_DATES_URL
    assert gdp.provenance[0]["event_title"] == "Gross Domestic Product"
    assert gdp.provenance[0]["event_time_et"] == "08:30 AM"
    assert pce.observed_at == "2026-06-25"
    assert pce.value == JUNE_BEA_DAYS_UNTIL
    assert pce.provenance[0]["event_title"] == "Personal Income and Outlays"


@respx.mock
def test_official_calendar_provider_returns_next_bls_release_events_from_official_pages() -> None:
    respx.get(BLS_CPI_URL).mock(return_value=Response(200, text=BLS_RELEASE_HTML))
    respx.get(BLS_EMPLOYMENT_URL).mock(return_value=Response(200, text=BLS_RELEASE_HTML))
    respx.get(BLS_PPI_URL).mock(return_value=Response(200, text=BLS_RELEASE_HTML))
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    cpi = provider.get_latest("bls_cpi_next")
    employment = provider.get_latest("bls_employment_next")
    ppi = provider.get_latest("bls_ppi_next")

    assert cpi.series_key == "official_calendar:bls_cpi_next"
    assert cpi.observed_at == "2026-07-14"
    assert cpi.value == JUNE_BLS_CPI_DAYS_UNTIL
    assert cpi.provenance[0]["source_url"] == BLS_CPI_URL
    assert cpi.provenance[0]["event_title"] == "Consumer Price Index"
    assert cpi.provenance[0]["event_time_et"] == "08:30 AM"
    assert cpi.provenance[0]["reference_period"] == "June 2026"
    assert employment.provenance[0]["source_url"] == BLS_EMPLOYMENT_URL
    assert employment.provenance[0]["event_title"] == "Employment Situation"
    assert ppi.provenance[0]["source_url"] == BLS_PPI_URL
    assert ppi.provenance[0]["event_title"] == "Producer Price Index"


@respx.mock
def test_official_calendar_provider_range_filters_events_by_event_date() -> None:
    respx.get(FOMC_URL).mock(return_value=Response(200, text=FOMC_HTML))
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    observations = provider.get_range("fomc_decision_next", start="2026-06-01", end="2026-07-31")

    assert [observation.observed_at for observation in observations] == ["2026-06-17", "2026-07-29"]


def test_official_calendar_provider_rejects_unknown_calendar_series() -> None:
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    with pytest.raises(MacrodataError) as exc_info:
        provider.get_latest("not_real_next")

    assert exc_info.value.code == "unknown_series"
