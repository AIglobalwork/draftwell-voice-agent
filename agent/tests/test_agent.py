from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from draftwell.agent import today_line


def test_today_line_uses_local_date():
    now = datetime(2026, 11, 22, 15, tzinfo=UTC)
    assert today_line(now, ZoneInfo("America/New_York")) == "Today is Sunday, November 22, 2026 (Atlanta time)."


def test_today_line_late_evening_utc_is_still_previous_local_day():
    now = datetime(2026, 12, 2, 3, 30, tzinfo=UTC)  # Tue Dec 1, 22:30 in Atlanta
    assert "Tuesday, December 1, 2026" in today_line(now, ZoneInfo("America/New_York"))


def test_booking_tool_takes_no_price_details():
    # The price comes from the last get_quote of the call. If the tool took systems, vents or add-ons,
    # the model could pass a different set than the one the caller agreed to (live call: $718 -> $589).
    import inspect

    from draftwell.agent import DraftwellAgent

    params = set(inspect.signature(DraftwellAgent.book_appointment).parameters)
    assert params == {"self", "slot_start", "name", "phone", "address", "zip_code", "email"}
