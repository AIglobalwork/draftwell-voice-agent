from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from draftwell.booking import Customer
from draftwell.config import load_business_config, load_price_list
from draftwell.flows import Deps, book, check_area, find_slots, quote, take_message
from draftwell.pricing import QuoteParams
from fakes import FakeCalendar, RecordingNotifier, RecordingPublish

CONFIG = Path(__file__).resolve().parent.parent / "config"
CFG = load_business_config(CONFIG / "business.yaml")
PRICES = load_price_list(CONFIG / "pricing.yaml")
ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 12, 1, 14, tzinfo=UTC)  # Tue Dec 1, 9 AM in Atlanta
CUSTOMER = Customer("John Smith", "+14045550123", "123 Peachtree St NE, Atlanta, GA", "30307", "john@example.com")
SLOT = "2026-12-03T08:00:00-05:00"


def make_deps(calendar) -> Deps:
    return Deps(PRICES, CFG, calendar, RecordingNotifier(), RecordingPublish(), lambda: NOW)


@pytest.fixture
def deps():
    return make_deps(FakeCalendar())


@pytest.fixture
def deps_busy_dec3_morning():
    busy = [(datetime(2026, 12, 3, 8, tzinfo=ET), datetime(2026, 12, 3, 12, tzinfo=ET))]
    return make_deps(FakeCalendar(busy=busy))


def test_quote_text_has_lines_total_and_estimate_wording(deps):
    t = quote(deps, QuoteParams(1, 14, None, dryer_vent=True))
    assert "$718" in t and "$140" in t and "estimate" in t.lower() and "final price" in t


def test_quote_without_vent_count_is_approximate(deps):
    assert "approximate" in quote(deps, QuoteParams(1, None, 2000)).lower()


def test_quote_bad_params_returns_text(deps):
    assert "cannot" in quote(deps, QuoteParams(0, 14, None)).lower()


def test_check_area(deps):
    assert "in our service area" in check_area(deps, "30307")
    assert "outside" in check_area(deps, "90210")


async def test_book_recomputes_quote(deps):
    t = await book(deps, SLOT, CUSTOMER, QuoteParams(1, 16, None, dryer_vent=True))
    assert "$788" in t  # 449 + 6×35 + 129, not an earlier $718


async def test_book_publishes_panel_events(deps):
    await book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None, dryer_vent=True))
    assert [e["type"] for e in deps.publish.events] == ["sms_to_customer", "owner_notification"]
    assert deps.publish.events[0]["delivered"] is False  # SMS disabled in demo
    assert deps.publish.events[1]["delivered"] is True
    assert len(deps.notifier.owner_texts) == 1


async def test_book_slot_taken_returns_alternatives(deps_busy_dec3_morning):
    t = await book(deps_busy_dec3_morning, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    assert "no longer available" in t and "Thu, Dec 3, 1 PM–5 PM" in t
    assert deps_busy_dec3_morning.publish.events == []


async def test_book_invalid_slot_returns_alternatives(deps):
    t = await book(deps, "2026-12-03T09:00:00-05:00", CUSTOMER, QuoteParams(1, 14, None))
    assert "not a bookable slot" in t and "Thu, Dec 3, 8 AM–12 PM" in t
    t = await book(deps, "next thursday", CUSTOMER, QuoteParams(1, 14, None))
    assert "not a bookable slot" in t


async def test_book_unexpected_error_says_not_booked(deps):
    def broken_create_event(slot, summary, description):
        raise RuntimeError("calendar down")

    deps.calendar.create_event = broken_create_event
    t = await book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    assert "not booked" in t.lower() and "message" in t
    assert deps.notifier.owner_texts == [] and deps.publish.events == []


async def test_book_refuses_out_of_area_zip(deps):
    far = Customer("John Smith", "+14045550123", "1 Main St, Beverly Hills", "90210")
    t = await book(deps, SLOT, far, QuoteParams(1, 14, None))
    assert "outside" in t and deps.calendar.saved == [] and deps.publish.events == []


async def test_book_survives_publish_failure():
    deps = make_deps(FakeCalendar())
    deps.publish = RecordingPublish(raises=True)
    t = await book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    assert "Booked" in t and len(deps.calendar.saved) == 1


async def test_find_slots_without_date_gives_earliest(deps):
    t = await find_slots(deps, None)
    assert "Thu, Dec 3, 8 AM–12 PM (start 2026-12-03T08:00:00-05:00)" in t


async def test_find_slots_skips_busy_slots(deps_busy_dec3_morning):
    t = await find_slots(deps_busy_dec3_morning, "2026-12-03")
    assert "8 AM–12 PM" not in t.split("\n")[1] and "Thu, Dec 3, 1 PM–5 PM" in t


async def test_find_slots_bad_date_asks_for_a_date(deps):
    assert "date" in (await find_slots(deps, "soon")).lower()


async def test_find_slots_beyond_window_says_14_days(deps):
    t = await find_slots(deps, "2027-03-01")
    assert "14 days ahead" in t and "start 2026-12-1" in t


async def test_take_message_notifies_owner(deps):
    t = await take_message(deps, "Mary Lee", "+14045550199", "Call me about a commercial job")
    assert deps.notifier.owner_texts and "Mary Lee" in deps.notifier.owner_texts[0]
    assert deps.publish.events[-1]["type"] == "owner_notification" and "call you back" in t
