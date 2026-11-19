"""Test doubles. FakeCalendar mimics the CalendarClient methods without any network."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from draftwell.calendar_client import CalendarEvent
from draftwell.scheduling import Slot

BASE_TIME = datetime(2026, 12, 1, 14, tzinfo=timezone.utc)


class FakeCalendar:
    def __init__(self, busy: list | None = None, rival: Literal["before", "after"] | None = None):
        self._busy = busy or []
        self._rival = rival
        self._counter = 0  # fake clock: each created event is one minute later
        self.saved: list[dict] = []  # events stored in this fake calendar

    def _add(self, event_id: str, summary: str, description: str, slot: Slot, created: datetime) -> None:
        self.saved.append(
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

    def events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return [CalendarEvent(e["id"], e["created"]) for e in self.saved if e["start"] < end and start < e["end"]]

    def delete_event(self, event_id: str) -> None:
        self.saved = [e for e in self.saved if e["id"] != event_id]


class RecordingSenders:
    """Same three async methods as notify.Senders; they record calls instead of sending."""

    def __init__(self, slack_raises: bool = False, email_raises: bool = False, sms_raises: bool = False):
        self.sent_emails: list[tuple[str, str, str]] = []
        self.sent_slack: list[str] = []
        self.sent_sms: list[tuple[str, str]] = []
        self._slack_raises = slack_raises
        self._email_raises = email_raises
        self._sms_raises = sms_raises

    async def email(self, to: str, subject: str, body: str) -> None:
        if self._email_raises:
            raise RuntimeError("email down")
        self.sent_emails.append((to, subject, body))

    async def slack(self, text: str) -> None:
        if self._slack_raises:
            raise RuntimeError("slack down")
        self.sent_slack.append(text)

    async def sms(self, to: str, body: str) -> None:
        if self._sms_raises:
            raise RuntimeError("sms down")
        self.sent_sms.append((to, body))
