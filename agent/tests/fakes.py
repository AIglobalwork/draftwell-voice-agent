"""Test doubles. FakeCalendar mimics the CalendarClient methods without any network."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from draftwell.calendar_client import CalendarEvent
from draftwell.scheduling import Slot

BASE_TIME = datetime(2026, 12, 1, 14, tzinfo=timezone.utc)


class EventList(list):
    """A list of event dicts that can also be called like CalendarClient.events(start, end).

    The brief wants `cal.events` to be a plain list in tests AND a method in the client interface.
    """

    def __call__(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [CalendarEvent(e["id"], e["created"]) for e in self if e["start"] < end and start < e["end"]]


class FakeCalendar:
    def __init__(self, busy: list | None = None, rival: Literal["before", "after"] | None = None):
        self._busy = busy or []
        self._rival = rival
        self._counter = 0  # fake clock: each created event is one minute later
        self.events = EventList()

    def _add(self, event_id: str, summary: str, description: str, slot: Slot, created: datetime) -> None:
        self.events.append(
            {
                "id": event_id,
                "summary": summary,
                "description": description,
                "start": slot.start,
                "end": slot.end,
                "created": created,
            }
        )

    def busy(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        return [(s, e) for s, e in self._busy if s < end and start < e]

    def create_event(self, slot: Slot, summary: str, description: str) -> str:
        self._counter += 1
        created = BASE_TIME + timedelta(minutes=self._counter)
        event_id = f"evt-{self._counter}"
        self._add(event_id, summary, description, slot, created)
        if self._rival:
            offset = timedelta(seconds=-1 if self._rival == "before" else 1)
            self._add("rival", "Rival booking", "", slot, created + offset)
        return event_id

    def delete_event(self, event_id: str) -> None:
        self.events[:] = [e for e in self.events if e["id"] != event_id]
