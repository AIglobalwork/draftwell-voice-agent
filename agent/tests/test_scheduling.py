from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from draftwell.config import load_business_config
from draftwell.scheduling import Slot, candidate_slots, first_available, free_slots

CONFIG = Path(__file__).resolve().parent.parent / "config"
CFG = load_business_config(CONFIG / "business.yaml")
ET = ZoneInfo("America/New_York")


def test_first_slot_is_tomorrow_in_local_time():
    now = datetime(2026, 12, 2, 3, 30, tzinfo=UTC)  # Tue Dec 1, 22:30 ET
    assert candidate_slots(CFG, now)[0].start == datetime(2026, 12, 2, 8, tzinfo=ET)


def test_slots_shape_and_window():
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    assert {(s.start.hour, s.end.hour) for s in slots} == {(8, 12), (13, 17)}
    assert all(s.start.weekday() != 6 for s in slots)
    assert slots[-1].start.date() == date(2026, 12, 15)


def test_free_slots_removes_only_overlapping():
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    busy = [(datetime(2026, 12, 3, 9, tzinfo=ET), datetime(2026, 12, 3, 10, tzinfo=ET))]
    free = free_slots(slots, busy)
    assert datetime(2026, 12, 3, 8, tzinfo=ET) not in [s.start for s in free]
    assert datetime(2026, 12, 3, 13, tzinfo=ET) in [s.start for s in free]


def test_busy_touching_slot_edges_removes_nothing():  # lunch 12:00-13:00 only touches both slots
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    busy = [(datetime(2026, 12, 3, 12, tzinfo=ET), datetime(2026, 12, 3, 13, tzinfo=ET))]
    free_starts = [s.start for s in free_slots(slots, busy)]
    assert datetime(2026, 12, 3, 8, tzinfo=ET) in free_starts
    assert datetime(2026, 12, 3, 13, tzinfo=ET) in free_starts


def test_preferred_sunday_returns_next_open_day():
    slots = candidate_slots(CFG, datetime(2026, 12, 1, 14, tzinfo=UTC))
    assert first_available(slots, date(2026, 12, 6))[0].start == datetime(2026, 12, 7, 8, tzinfo=ET)


def test_slot_label():
    assert Slot(datetime(2026, 12, 3, 8, tzinfo=ET), datetime(2026, 12, 3, 12, tzinfo=ET)).label() == "Thu, Dec 3, 8 AM–12 PM"
