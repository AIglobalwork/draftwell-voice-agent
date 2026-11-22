from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from draftwell.agent import today_line


def test_today_line_uses_local_date():
    now = datetime(2026, 11, 22, 15, tzinfo=UTC)
    assert today_line(now, ZoneInfo("America/New_York")) == "Today is Sunday, November 22, 2026 (Atlanta time)."


def test_today_line_late_evening_utc_is_still_previous_local_day():
    now = datetime(2026, 12, 2, 3, 30, tzinfo=UTC)  # Tue Dec 1, 22:30 in Atlanta
    assert "Tuesday, December 1, 2026" in today_line(now, ZoneInfo("America/New_York"))
