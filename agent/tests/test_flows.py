import logging
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from draftwell.booking import Customer
from draftwell.config import load_business_config, load_price_list
from draftwell.flows import Deps, book, check_area, find_slots, quote, take_message, wait_for_background
from draftwell.notify import Notifier, NotifySettings
from draftwell.pricing import QuoteParams
from fakes import FakeCalendar, RecordingNotifier, RecordingPublish, RecordingSenders

CONFIG = Path(__file__).resolve().parent.parent / "config"
CFG = load_business_config(CONFIG / "business.yaml")
PRICES = load_price_list(CONFIG / "pricing.yaml")
ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 12, 1, 14, tzinfo=UTC)  # Tue Dec 1, 9 AM in Atlanta
CUSTOMER = Customer("John Smith", "+14045550123", "123 Peachtree St NE, Atlanta, GA", "30307", "john@example.com")
SLOT = "2026-12-03T08:00:00-05:00"


async def quoted_book(deps, slot, customer, params):
    """The order of a real call: the caller hears a quote, then books."""
    quote(deps, params)
    return await book(deps, slot, customer)


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


async def test_book_uses_the_quote_total(deps):
    t = await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 16, None, dryer_vent=True))
    assert "$788" in t  # 449 + 6×35 + 129


async def test_book_publishes_panel_events(deps):
    await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None, dryer_vent=True))
    await wait_for_background(deps, 5)
    assert [e["type"] for e in deps.publish.events] == ["sms_to_customer", "owner_notification"]
    assert deps.publish.events[0]["delivered"] is False  # SMS disabled in demo
    assert deps.publish.events[1]["delivered"] is True
    assert len(deps.notifier.owner_texts) == 1


async def test_book_slot_taken_returns_alternatives(deps_busy_dec3_morning):
    t = await quoted_book(deps_busy_dec3_morning, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    assert "no longer available" in t and "Thu, Dec 3, 1 PM–5 PM" in t
    assert deps_busy_dec3_morning.publish.events == []


async def test_book_invalid_slot_returns_alternatives(deps):
    t = await quoted_book(deps, "2026-12-03T09:00:00-05:00", CUSTOMER, QuoteParams(1, 14, None))
    assert "not a bookable slot" in t and "Thu, Dec 3, 8 AM–12 PM" in t
    t = await quoted_book(deps, "next thursday", CUSTOMER, QuoteParams(1, 14, None))
    assert "not a bookable slot" in t


async def test_book_unexpected_error_says_not_booked(deps):
    def broken_create_event(slot, summary, description):
        raise RuntimeError("calendar down")

    deps.calendar.create_event = broken_create_event
    t = await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    assert "not booked" in t.lower() and "message" in t
    assert deps.notifier.owner_texts == [] and deps.publish.events == []


async def test_book_refuses_out_of_area_zip(deps):
    far = Customer("John Smith", "+14045550123", "1 Main St, Beverly Hills", "90210")
    t = await quoted_book(deps, SLOT, far, QuoteParams(1, 14, None))
    assert "outside" in t and deps.calendar.saved == [] and deps.publish.events == []


async def test_book_survives_publish_failure():
    deps = make_deps(FakeCalendar())
    deps.publish = RecordingPublish(raises=True)
    t = await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
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


@pytest.mark.parametrize("day", ["2026-11-30", "2026-12-01"])  # a past day, and today
async def test_find_slots_past_or_same_day_says_so(deps, day):
    t = await find_slots(deps, day)
    assert "past or too soon" in t and "Wed, Dec 2" in t  # earliest bookable day
    assert "start 2026-12-02T08:00:00-05:00" in t  # and the earliest slots follow


async def test_take_message_notifies_owner(deps):
    t = await take_message(deps, "Mary Lee", "+14045550199", "Call me about a commercial job")
    assert deps.notifier.owner_texts and "Mary Lee" in deps.notifier.owner_texts[0]
    assert deps.publish.events[-1]["type"] == "owner_notification" and "call you back" in t


async def test_take_message_when_owner_channels_fail_gives_phone(deps):
    deps.notifier = RecordingNotifier(owner_fails=True)
    t = await take_message(deps, "Mary Lee", "+14045550199", "Call me")
    assert "passed on" not in t and "call you back" not in t
    assert CFG.phone in t
    assert deps.publish.events[-1]["type"] == "owner_notification" and deps.publish.events[-1]["delivered"] is False


async def test_book_logs_timings_without_personal_data(caplog):
    settings = NotifySettings("smtp.example.com", 587, "bot@example.com", "pw", "owner@example.com",
                              "https://hooks.example.com/secret", False, "", "", "")
    notifier = Notifier(settings, CFG, senders=RecordingSenders())
    deps = Deps(PRICES, CFG, FakeCalendar(), notifier, RecordingPublish(), lambda: NOW)
    with caplog.at_level(logging.INFO):
        await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
        await wait_for_background(deps, 5)
    text = caplog.text
    assert "Calendar step took" in text
    assert "Notification email sent in" in text and "Notification slack sent in" in text
    for private in ["john@example.com", "owner@example.com", "+14045550123", "hooks.example.com"]:
        assert private not in text


def make_slow_deps(delay: float):
    settings = NotifySettings("smtp.example.com", 587, "bot@example.com", "pw", "owner@example.com",
                              "https://hooks.example.com/secret", False, "", "", "")
    senders = RecordingSenders(delay=delay)
    deps = Deps(PRICES, CFG, FakeCalendar(), Notifier(settings, CFG, senders=senders), RecordingPublish(), lambda: NOW)
    return deps, senders


async def test_book_returns_before_notifications_finish():
    deps, senders = make_slow_deps(0.2)
    t = await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    assert "Booked" in t and len(deps.calendar.saved) == 1
    assert senders.sent_emails == [] and senders.sent_slack == [] and deps.publish.events == []  # still pending
    await wait_for_background(deps, 5)
    assert len(senders.sent_emails) == 2 and len(senders.sent_slack) == 1  # customer + owner email, owner Slack
    assert [e["type"] for e in deps.publish.events] == ["sms_to_customer", "owner_notification"]
    assert deps.background == set()


async def test_wait_for_background_gives_up_after_timeout(caplog):
    deps, senders = make_slow_deps(1)
    await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
    with caplog.at_level(logging.WARNING):
        await wait_for_background(deps, 0.05)
    assert "did not finish" in caplog.text
    await wait_for_background(deps, 5)  # let the task end so the test leaves nothing running


async def test_background_crash_is_logged_not_raised(caplog):
    deps = make_deps(FakeCalendar())

    async def broken(booking):
        raise ValueError("secret detail")

    deps.notifier.confirm_to_customer = broken
    with caplog.at_level(logging.ERROR):
        await quoted_book(deps, SLOT, CUSTOMER, QuoteParams(1, 14, None))
        await wait_for_background(deps, 5)
    assert "ValueError" in caplog.text and "secret detail" not in caplog.text



async def test_booking_keeps_the_price_the_caller_heard(deps):
    # Live call RM_PRGKqqtEzDfy: get_quote(1 system, 14 vents, dryer vent) gave $718, the caller agreed,
    # then the model called book_appointment without the dryer vent and $589 was booked.
    # Now the booking takes the price from the last quote of the call, not from a second set of arguments.
    assert "$718" in quote(deps, QuoteParams(1, 14, None, dryer_vent=True))
    t = await book(deps, SLOT, CUSTOMER)
    assert "$718" in t
    assert "$718" in deps.calendar.saved[0]["description"]


async def test_booking_without_a_quote_books_nothing(deps):
    t = await book(deps, SLOT, CUSTOMER)
    assert "nothing was booked" in t.lower() and "quote" in t.lower()
    assert deps.calendar.saved == []


async def test_booking_uses_the_latest_quote(deps):
    quote(deps, QuoteParams(1, 14, None, dryer_vent=True))
    quote(deps, QuoteParams(1, 14, None))  # the caller dropped the dryer vent and heard the new total
    assert "$589" in await book(deps, SLOT, CUSTOMER)


async def test_failed_quote_does_not_leave_an_old_price(deps):
    quote(deps, QuoteParams(1, 14, None, dryer_vent=True))
    assert "cannot" in quote(deps, QuoteParams(0, 14, None)).lower()  # the caller changed details, quote failed
    assert "nothing was booked" in (await book(deps, SLOT, CUSTOMER)).lower()


async def test_quote_is_kept_per_call():
    # Each call builds its own Deps in main.entrypoint, so a quote never carries over to another caller.
    first, second = make_deps(FakeCalendar()), make_deps(FakeCalendar())
    quote(first, QuoteParams(1, 14, None, dryer_vent=True))
    assert "nothing was booked" in (await book(second, SLOT, CUSTOMER)).lower()
