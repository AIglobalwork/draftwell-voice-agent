"""Google Calendar access. Only this module talks to the Google API."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from google.oauth2 import service_account
from googleapiclient.discovery import build

from draftwell.scheduling import Slot


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    created: datetime


class CalendarClient(Protocol):
    def busy(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]: ...

    def create_event(self, slot: Slot, summary: str, description: str) -> str: ...

    def events(self, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    def delete_event(self, event_id: str) -> None: ...


class GoogleCalendarClient:
    def __init__(self, calendar_id: str, service_account_info: dict):
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        self.calendar_id = calendar_id
        self.service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def busy(self, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
        body = {"timeMin": start.isoformat(), "timeMax": end.isoformat(), "items": [{"id": self.calendar_id}]}
        result = self.service.freebusy().query(body=body).execute()
        intervals = result["calendars"][self.calendar_id]["busy"]
        return [(datetime.fromisoformat(i["start"]), datetime.fromisoformat(i["end"])) for i in intervals]

    def create_event(self, slot: Slot, summary: str, description: str) -> str:
        zone = slot.start.tzinfo.key
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": slot.start.isoformat(), "timeZone": zone},
            "end": {"dateTime": slot.end.isoformat(), "timeZone": zone},
        }
        return self.service.events().insert(calendarId=self.calendar_id, body=body).execute()["id"]

    def events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        result = (
            self.service.events()
            .list(calendarId=self.calendar_id, timeMin=start.isoformat(), timeMax=end.isoformat(), singleEvents=True)
            .execute()
        )
        return [CalendarEvent(item["id"], datetime.fromisoformat(item["created"])) for item in result["items"]]

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
