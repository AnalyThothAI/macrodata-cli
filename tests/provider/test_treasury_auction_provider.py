from __future__ import annotations

from datetime import date

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.treasury_auction import TreasuryAuctionProvider

AUCTION_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
TENTATIVE_AUCTION_SCHEDULE_URL = "https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.xml"
EXPECTED_BID_TO_COVER = 2.4
EXPECTED_HIGH_YIELD = 5.015
EXPECTED_INDIRECT_BIDDER_PCT = 40.0
EXPECTED_2Y_NEXT_DAYS_UNTIL = 7
EXPECTED_10Y_NEXT_DAYS_UNTIL = 21
UNKNOWN_SERIES_EXIT_CODE = 2

TENTATIVE_AUCTION_SCHEDULE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<AuctionCalendar>
  <AuctionCalendarName>May2026 Refunding Auction Calendar Official Ver2</AuctionCalendarName>
  <StartDate>2026-05-06</StartDate>
  <EndDate>2026-10-31</EndDate>
  <AuctionCalendarDate>
    <SecurityTermWeekYear>10-Year</SecurityTermWeekYear>
    <SecurityType>NOTE</SecurityType>
    <ReOpeningIndicator>N</ReOpeningIndicator>
    <TIPS>N</TIPS>
    <FloatingRate>N</FloatingRate>
    <AnnouncementDate>2026-06-04</AnnouncementDate>
    <AuctionDate>2026-06-09</AuctionDate>
    <SettlementDate>2026-06-16</SettlementDate>
  </AuctionCalendarDate>
  <AuctionCalendarDate>
    <SecurityTermWeekYear>2-Year</SecurityTermWeekYear>
    <SecurityType>NOTE</SecurityType>
    <ReOpeningIndicator>N</ReOpeningIndicator>
    <TIPS>N</TIPS>
    <FloatingRate>N</FloatingRate>
    <AnnouncementDate>2026-06-18</AnnouncementDate>
    <AuctionDate>2026-06-23</AuctionDate>
    <SettlementDate>2026-06-30</SettlementDate>
  </AuctionCalendarDate>
  <AuctionCalendarDate>
    <SecurityTermWeekYear>10-Year</SecurityTermWeekYear>
    <SecurityType>NOTE</SecurityType>
    <ReOpeningIndicator>Y</ReOpeningIndicator>
    <TIPS>N</TIPS>
    <FloatingRate>N</FloatingRate>
    <AnnouncementDate>2026-07-02</AnnouncementDate>
    <AuctionDate>2026-07-07</AuctionDate>
    <SettlementDate>2026-07-15</SettlementDate>
  </AuctionCalendarDate>
  <AuctionCalendarDate>
    <SecurityTermWeekYear>30-Year</SecurityTermWeekYear>
    <SecurityType>BOND</SecurityType>
    <ReOpeningIndicator>Y</ReOpeningIndicator>
    <TIPS>N</TIPS>
    <FloatingRate>N</FloatingRate>
    <AnnouncementDate>2026-07-02</AnnouncementDate>
    <AuctionDate>2026-07-08</AuctionDate>
    <SettlementDate>2026-07-15</SettlementDate>
  </AuctionCalendarDate>
  <AuctionCalendarDate>
    <SecurityTermWeekYear>10-Year</SecurityTermWeekYear>
    <SecurityType>NOTE</SecurityType>
    <ReOpeningIndicator>Y</ReOpeningIndicator>
    <TIPS>Y</TIPS>
    <FloatingRate>N</FloatingRate>
    <AnnouncementDate>2026-07-17</AnnouncementDate>
    <AuctionDate>2026-07-22</AuctionDate>
    <SettlementDate>2026-07-31</SettlementDate>
  </AuctionCalendarDate>
</AuctionCalendar>
"""


def _row(
    *,
    auction_date: str,
    record_date: str = "2026-05-15",
    security_type: str = "Note",
    security_term: str = "10-Year",
    high_yield: str = "4.4680",
    bid_to_cover_ratio: str = "2.400000",
    indirect_bidder_accepted: str = "26775518000",
    total_accepted: str = "51972791100",
) -> dict[str, str]:
    return {
        "record_date": record_date,
        "cusip": "91282CQQ7",
        "security_type": security_type,
        "security_term": security_term,
        "auction_date": auction_date,
        "issue_date": "2026-05-15",
        "maturity_date": "2036-05-15",
        "high_yield": high_yield,
        "bid_to_cover_ratio": bid_to_cover_ratio,
        "indirect_bidder_accepted": indirect_bidder_accepted,
        "total_accepted": total_accepted,
        "total_tendered": "110863591100",
        "offering_amt": "42000000000",
    }


@respx.mock
def test_treasury_auction_latest_skips_announced_rows_and_parses_bid_to_cover() -> None:
    route = respx.get(AUCTION_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    _row(auction_date="2026-06-10", bid_to_cover_ratio="null"),
                    _row(auction_date="2026-05-12"),
                ]
            },
        )
    )
    provider = TreasuryAuctionProvider(http_client=MacrodataHttpClient())

    observation = provider.get_latest("10y_bid_to_cover")

    request = route.calls.last.request
    assert request.url.params["filter"] == "security_type:eq:Note,security_term:eq:10-Year"
    assert request.url.params["sort"] == "-auction_date"
    assert request.url.params["page[size]"] == "25"
    assert observation.series_key == "treasury_auction:10y_bid_to_cover"
    assert observation.provider == "treasury_auction"
    assert observation.dataset == "10y_bid_to_cover"
    assert observation.observed_at == "2026-05-12"
    assert observation.source_ts == "2026-05-15"
    assert observation.value == EXPECTED_BID_TO_COVER
    assert observation.unit == "ratio"
    assert observation.frequency == "event"
    assert observation.latency_class == "event"
    assert observation.data_quality == "ok"
    assert observation.provenance[0]["source_url"] == AUCTION_URL
    assert observation.provenance[0]["cusip"] == "91282CQQ7"


@respx.mock
def test_treasury_auction_range_parses_high_yield_and_indirect_bidder_share() -> None:
    respx.get(AUCTION_URL).mock(
        return_value=Response(
            200,
            json={
                "data": [
                    _row(
                        auction_date="2026-05-13",
                        security_type="Bond",
                        security_term="30-Year",
                        high_yield="5.0150",
                        indirect_bidder_accepted="12000000000",
                        total_accepted="30000000000",
                    )
                ]
            },
        )
    )
    provider = TreasuryAuctionProvider(http_client=MacrodataHttpClient())

    high_yield = provider.get_range("30y_high_yield", start="2026-05-01", end="2026-05-31")
    indirect_pct = provider.get_range("30y_indirect_bidder_pct", start="2026-05-01", end="2026-05-31")

    assert high_yield[0].series_key == "treasury_auction:30y_high_yield"
    assert high_yield[0].value == EXPECTED_HIGH_YIELD
    assert high_yield[0].unit == "percent"
    assert indirect_pct[0].series_key == "treasury_auction:30y_indirect_bidder_pct"
    assert indirect_pct[0].value == EXPECTED_INDIRECT_BIDDER_PCT
    assert indirect_pct[0].unit == "percent"


@respx.mock
def test_treasury_auction_latest_returns_next_nominal_auction_from_official_tentative_schedule() -> None:
    respx.get(TENTATIVE_AUCTION_SCHEDULE_URL).mock(return_value=Response(200, text=TENTATIVE_AUCTION_SCHEDULE_XML))
    provider = TreasuryAuctionProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    observation = provider.get_latest("2y_next_auction_days")

    assert observation.series_key == "treasury_auction:2y_next_auction_days"
    assert observation.provider == "treasury_auction"
    assert observation.dataset == "2y_next_auction_days"
    assert observation.observed_at == "2026-06-23"
    assert observation.source_ts == "2026-06-16"
    assert observation.value == EXPECTED_2Y_NEXT_DAYS_UNTIL
    assert observation.unit == "days_until"
    assert observation.frequency == "event"
    assert observation.latency_class == "calendar"
    assert observation.data_quality == "ok"
    assert observation.provenance[0]["source_url"] == TENTATIVE_AUCTION_SCHEDULE_URL
    assert observation.provenance[0]["security_type"] == "NOTE"
    assert observation.provenance[0]["security_term"] == "2-Year"
    assert observation.provenance[0]["announcement_date"] == "2026-06-18"
    assert observation.provenance[0]["settlement_date"] == "2026-06-30"
    assert observation.provenance[0]["reopening"] is False
    assert observation.provenance[0]["tips"] is False
    assert observation.provenance[0]["floating_rate"] is False


@respx.mock
def test_treasury_auction_range_returns_nominal_auction_calendar_without_tips_rows() -> None:
    respx.get(TENTATIVE_AUCTION_SCHEDULE_URL).mock(return_value=Response(200, text=TENTATIVE_AUCTION_SCHEDULE_XML))
    provider = TreasuryAuctionProvider(http_client=MacrodataHttpClient(), today=date(2026, 6, 16))

    observations = provider.get_range("10y_next_auction_days", start="2026-06-16", end="2026-07-31")

    assert [observation.observed_at for observation in observations] == ["2026-07-07"]
    assert observations[0].series_key == "treasury_auction:10y_next_auction_days"
    assert observations[0].value == EXPECTED_10Y_NEXT_DAYS_UNTIL
    assert observations[0].provenance[0]["reopening"] is True


def test_treasury_auction_rejects_unknown_dataset_structured() -> None:
    provider = TreasuryAuctionProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_latest("10y_tail")

    assert raised.value.code == "unknown_series"
    assert raised.value.provider == "treasury_auction"
    assert raised.value.exit_code == UNKNOWN_SERIES_EXIT_CODE
