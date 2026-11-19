from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from draftwell.booking import Customer, InvalidSlotError, SlotTakenError, book_slot
from draftwell.config import load_business_config, load_price_list
from draftwell.pricing import QuoteParams, calculate_quote
from fakes import FakeCalendar

CONFIG = Path(__file__).resolve().parent.parent / "config"
CFG = load_business_config(CONFIG / "business.yaml")
PRICES = load_price_list(CONFIG / "pricing.yaml")
ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 12, 1, 14, tzinfo=UTC)  # Tue Dec 1, 9 AM in Atlanta
CUSTOMER = Customer("John Smith", "+14045550123", "123 Peachtree St NE, Atlanta, GA", "30307", "john@example.com")
QUOTE_718 = calculate_quote(QuoteParams(1, 14, None, dryer_vent=True), PRICES)


def test_book_slot_creates_event():
    cal = FakeCalendar()
    b = book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert b.slot.end == datetime(2026, 12, 3, 12, tzinfo=ET)
    assert "John Smith" in cal.saved[0]["summary"] and "$718" in cal.saved[0]["description"]


def test_book_slot_raises_when_taken():
    cal = FakeCalendar(busy=[(datetime(2026, 12, 3, 8, tzinfo=ET), datetime(2026, 12, 3, 12, tzinfo=ET))])
    with pytest.raises(SlotTakenError):
        book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert cal.saved == []


def test_book_slot_loses_race_deletes_own_event():  # another process booked a moment earlier
    cal = FakeCalendar(rival="before")
    with pytest.raises(SlotTakenError):
        book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert [e["summary"] for e in cal.saved] == ["Rival booking"]


def test_book_slot_wins_race_keeps_own_event():  # the other process will delete its own event
    cal = FakeCalendar(rival="after")
    b = book_slot(cal, CFG, datetime(2026, 12, 3, 8, tzinfo=ET), CUSTOMER, QUOTE_718, NOW)
    assert b.event_id in [e["id"] for e in cal.saved] and len(cal.saved) == 2


@pytest.mark.parametrize(
    "start",
    [datetime(2026, 12, 3, 9, tzinfo=ET), datetime(2026, 12, 6, 8, tzinfo=ET), datetime(2026, 12, 20, 8, tzinfo=ET)],
)
def test_book_slot_rejects_invalid_start(start):  # wrong hour, Sunday, beyond 14 days
    with pytest.raises(InvalidSlotError):
        book_slot(FakeCalendar(), CFG, start, CUSTOMER, QUOTE_718, NOW)
