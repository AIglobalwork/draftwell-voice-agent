"""Booking a slot in the calendar, without double booking."""

from dataclasses import dataclass
from datetime import datetime

from draftwell.calendar_client import CalendarClient
from draftwell.config import BusinessConfig
from draftwell.pricing import Quote
from draftwell.scheduling import Slot, candidate_slots


class SlotTakenError(Exception):
    pass


class InvalidSlotError(Exception):
    pass


@dataclass(frozen=True)
class Customer:
    name: str
    phone: str
    address: str
    zip_code: str
    email: str | None = None


@dataclass(frozen=True)
class Booking:
    event_id: str
    slot: Slot
    customer: Customer
    quote: Quote


def _event_description(customer: Customer, quote: Quote) -> str:
    lines = [f"Address: {customer.address} {customer.zip_code}", f"Phone: {customer.phone}"]
    if customer.email:
        lines.append(f"Email: {customer.email}")
    lines += [f"{line.label}: ${line.amount}" for line in quote.lines]
    lines.append(f"Total estimate: ${quote.total}")
    lines.append("The technician confirms the final price on site.")
    return "\n".join(lines)


def book_slot(
    calendar: CalendarClient,
    config: BusinessConfig,
    slot_start: datetime,
    customer: Customer,
    quote: Quote,
    now: datetime,
) -> Booking:
    slot = next((s for s in candidate_slots(config, now) if s.start == slot_start), None)
    if slot is None:
        raise InvalidSlotError(f"{slot_start} is not a bookable slot")
    if calendar.busy(slot.start, slot.end):
        raise SlotTakenError("slot is already booked")

    event_id = calendar.create_event(slot, f"Duct cleaning: {customer.name}", _event_description(customer, quote))

    # No lock here: sessions may run in separate processes, so a lock in this process would not
    # help. Instead, re-read the slot after creating our event. The earliest event wins and the
    # others delete themselves.
    events = calendar.events(slot.start, slot.end)
    earliest = min(events, key=lambda e: (e.created, e.id)) if events else None
    if earliest is None or earliest.id != event_id:
        calendar.delete_event(event_id)
        raise SlotTakenError("another booking took this slot first")

    return Booking(event_id, slot, customer, quote)
