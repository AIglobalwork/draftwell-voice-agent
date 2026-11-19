from dataclasses import dataclass
from datetime import date, datetime, timedelta

from draftwell.config import BusinessConfig

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _clock(moment: datetime) -> str:
    """12-hour time without a leading zero, minutes only when not zero: '8 AM', '8:30 AM'."""
    hour = moment.hour % 12 or 12
    suffix = "AM" if moment.hour < 12 else "PM"
    if moment.minute:
        return f"{hour}:{moment.minute:02d} {suffix}"
    return f"{hour} {suffix}"


@dataclass(frozen=True)
class Slot:
    start: datetime
    end: datetime

    def label(self) -> str:
        weekday = WEEKDAYS[self.start.weekday()]
        month = MONTHS[self.start.month - 1]
        return f"{weekday}, {month} {self.start.day}, {_clock(self.start)}–{_clock(self.end)}"


def candidate_slots(config: BusinessConfig, now: datetime) -> list[Slot]:
    """All bookable slots in the window, in company local time (not the server's)."""
    today = now.astimezone(config.timezone).date()
    slots = []
    for offset in range(config.min_days_ahead, config.max_days_ahead + 1):
        day = today + timedelta(days=offset)
        if day.weekday() not in config.work_days:
            continue
        for start_time in config.slot_starts:
            start = datetime.combine(day, start_time, tzinfo=config.timezone)
            slots.append(Slot(start, start + timedelta(hours=config.slot_hours)))
    return slots


def free_slots(candidates: list[Slot], busy: list[tuple[datetime, datetime]]) -> list[Slot]:
    """Drop slots that overlap any busy interval (touching at an edge is fine)."""
    return [
        slot
        for slot in candidates
        if not any(busy_start < slot.end and slot.start < busy_end for busy_start, busy_end in busy)
    ]


def first_available(slots: list[Slot], preferred: date | None, limit: int = 3) -> list[Slot]:
    """The first `limit` slots, starting from the preferred day if one is given."""
    if preferred is not None:
        slots = [slot for slot in slots if slot.start.date() >= preferred]
    return slots[:limit]
