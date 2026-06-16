from __future__ import annotations

import pytest
import respx
from httpx import Response

from macrodata.core.errors import MacrodataError
from macrodata.gateway.http_client import MacrodataHttpClient
from macrodata.providers.treasury_auction import TreasuryAuctionProvider

AUCTION_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
EXPECTED_BID_TO_COVER = 2.4
EXPECTED_HIGH_YIELD = 5.015
EXPECTED_INDIRECT_BIDDER_PCT = 40.0
UNKNOWN_SERIES_EXIT_CODE = 2


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


def test_treasury_auction_rejects_unknown_dataset_structured() -> None:
    provider = TreasuryAuctionProvider(http_client=MacrodataHttpClient())

    with pytest.raises(MacrodataError) as raised:
        provider.get_latest("10y_tail")

    assert raised.value.code == "unknown_series"
    assert raised.value.provider == "treasury_auction"
    assert raised.value.exit_code == UNKNOWN_SERIES_EXIT_CODE
