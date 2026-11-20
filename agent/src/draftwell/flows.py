"""The logic under each voice-agent tool. Every flow returns plain text for the model:
facts, plus what to say next. The model never does arithmetic; prices come from pricing.py."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime

from draftwell.booking import Booking, Customer, InvalidSlotError, SlotTakenError, book_slot
from draftwell.calendar_client import CalendarClient
from draftwell.config import BusinessConfig, PriceList
from draftwell.notify import Delivery, Notifier, customer_sms_text, owner_booking_text, owner_message_text
from draftwell.pricing import Quote, QuoteParams, calculate_quote
from draftwell.scheduling import Slot, candidate_slots, first_available, free_slots
from draftwell.service_area import is_in_service_area

log = logging.getLogger(__name__)

ESTIMATE_NOTE = "Every price is an estimate: say that the technician confirms the final price on site."


@dataclass
class Deps:
    prices: PriceList
    config: BusinessConfig
    calendar: CalendarClient
    notifier: Notifier
    publish: Callable[[dict], Awaitable[None]]  # sends an event to the browser panel
    now: Callable[[], datetime]


def _quote_text(quote: Quote) -> str:
    lines = [f"- {line.label}: ${line.amount}" for line in quote.lines]
    kind = "approximate estimate" if quote.vents_estimated else "estimate"
    text = "\n".join(lines) + f"\nTotal {kind}: ${quote.total}\n" + ESTIMATE_NOTE
    if quote.vents_estimated:
        text += " The vent count was estimated from the square footage, so the total is approximate."
    return text


def _slot_text(slot: Slot) -> str:
    return f"{slot.label()} (start {slot.start.isoformat()})"


async def _free_slots(deps: Deps) -> list[Slot]:
    """Every bookable slot that is not busy in the calendar."""
    candidates = candidate_slots(deps.config, deps.now())
    if not candidates:
        return []
    busy = await asyncio.to_thread(deps.calendar.busy, candidates[0].start, candidates[-1].end)
    return free_slots(candidates, busy)


def _alternatives_text(slots: list[Slot]) -> str:
    if not slots:
        return "There are no free slots right now. Offer to take a message for the owner."
    return "Free slots:\n" + "\n".join(f"- {_slot_text(s)}" for s in slots)


async def _publish(deps: Deps, event_type: str, text: str, deliveries: list[Delivery], channel: str | None) -> None:
    delivered = any(d.status == "sent" and (channel is None or d.channel == channel) for d in deliveries)
    try:
        await deps.publish({"type": event_type, "text": text, "delivered": delivered})
    except Exception as exc:  # a panel failure must never break a booking
        log.warning("Publishing %s failed: %s", event_type, type(exc).__name__)


def check_area(deps: Deps, zip_code: str) -> str:
    if is_in_service_area(zip_code, deps.config):
        return "That ZIP code is in our service area. Continue with the quote."
    return "That ZIP code is outside our service area. Say we cannot serve it and offer to take a message."


def quote(deps: Deps, params: QuoteParams) -> str:
    try:
        result = calculate_quote(params, deps.prices)
    except ValueError as exc:
        return f"Cannot calculate a quote: {exc}. Ask the caller for the missing or corrected detail."
    return _quote_text(result) + "\nRead the total to the caller."


async def find_slots(deps: Deps, preferred_date: str | None) -> str:
    preferred = None
    if preferred_date is not None:
        try:
            preferred = date.fromisoformat(preferred_date)
        except ValueError:
            return "That is not a date I can read. Ask the caller for a specific day, then call this again with an ISO date (YYYY-MM-DD)."

    free = await _free_slots(deps)
    candidates = candidate_slots(deps.config, deps.now())
    if preferred is not None and candidates and preferred > candidates[-1].start.date():
        days = deps.config.max_days_ahead
        return (
            f"We book up to {days} days ahead, and that date is further out. "
            f"The latest available slots are below. Offer them.\n{_alternatives_text(free[-3:])}"
        )
    return f"Offer these to the caller.\n{_alternatives_text(first_available(free, preferred))}"


async def book(deps: Deps, slot_start: str, customer: Customer, params: QuoteParams) -> str:
    if not is_in_service_area(customer.zip_code, deps.config):
        return "That ZIP code is outside our service area, so nothing was booked. Offer to take a message."
    try:
        result = calculate_quote(params, deps.prices)  # recomputed here: the model never passes a total
    except ValueError as exc:
        return f"Nothing was booked: cannot calculate the quote ({exc}). Ask the caller for the missing detail."

    try:
        start = datetime.fromisoformat(slot_start)
    except ValueError:
        return "That is not a bookable slot. Offer another.\n" + _alternatives_text(
            first_available(await _free_slots(deps), None)
        )

    try:
        booking = await asyncio.to_thread(book_slot, deps.calendar, deps.config, start, customer, result, deps.now())
    except SlotTakenError:
        return "That slot is no longer available. Apologize briefly and offer another.\n" + _alternatives_text(
            first_available(await _free_slots(deps), None)
        )
    except InvalidSlotError:
        return "That is not a bookable slot. Offer another.\n" + _alternatives_text(
            first_available(await _free_slots(deps), None)
        )
    except Exception as exc:  # e.g. the calendar service is down
        log.error("Booking failed: %s", type(exc).__name__)
        return (
            "The appointment was not booked because of a technical problem. "
            "Apologize, and offer to take a message so the owner can call back."
        )

    await _notify(deps, booking)
    return (
        f"Booked: {booking.slot.label()}.\n{_quote_text(result)}\n"
        "Tell the caller the time window and that a confirmation is on its way."
    )


async def _notify(deps: Deps, booking: Booking) -> None:
    customer_deliveries = await deps.notifier.confirm_to_customer(booking)
    await _publish(deps, "sms_to_customer", customer_sms_text(booking, deps.config), customer_deliveries, "sms")
    owner_text = owner_booking_text(booking)
    owner_deliveries = await deps.notifier.notify_owner(owner_text)
    await _publish(deps, "owner_notification", owner_text, owner_deliveries, None)


async def take_message(deps: Deps, name: str, phone: str, message: str) -> str:
    text = owner_message_text(name, phone, message)
    deliveries = await deps.notifier.notify_owner(text)
    await _publish(deps, "owner_notification", text, deliveries, None)
    return "The message was passed on. Tell the caller that the owner will call you back soon."
