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
def test_official_calendar_provider_range_filters_events_by_event_date() -> None:
    respx.get(FOMC_URL).mock(return_value=Response(200, text=FOMC_HTML))
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    observations = provider.get_range("fomc_decision_next", start="2026-06-01", end="2026-07-31")

    assert [observation.observed_at for observation in observations] == ["2026-06-17", "2026-07-29"]


def test_official_calendar_provider_hard_deletes_inaccessible_bls_calendar_series() -> None:
    provider = OfficialCalendarProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    with pytest.raises(MacrodataError) as exc_info:
        provider.get_latest("bls_cpi_next")

    assert exc_info.value.code == "unknown_series"
