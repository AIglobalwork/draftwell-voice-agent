"""The logic under each voice-agent tool. Every flow returns plain text for the model:
facts, plus what to say next. The model never does arithmetic; prices come from pricing.py."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
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
    background: set[asyncio.Task] = field(default_factory=set)  # running notification tasks
    # The last price the caller heard in this call. Booking uses it, so the booked total is always the
    # quoted one. Deps is built per call (main.entrypoint), so it never carries over to another caller.
    last_quote: Quote | None = None


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
        deps.last_quote = None  # the details changed: an older price must not be booked
        return f"Cannot calculate a quote: {exc}. Ask the caller for the missing or corrected detail."
    deps.last_quote = result
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
    if preferred is not None and candidates and preferred < candidates[0].start.date():
        return (
            "That date is in the past or too soon to book. "
            f"The earliest bookable slot is {_slot_text(candidates[0])}. Tell the caller, then offer these.\n"
            f"{_alternatives_text(first_available(free, None))}"
        )
    return f"Offer these to the caller.\n{_alternatives_text(first_available(free, preferred))}"


async def book(deps: Deps, slot_start: str, customer: Customer) -> str:
    if not is_in_service_area(customer.zip_code, deps.config):
        return "That ZIP code is outside our service area, so nothing was booked. Offer to take a message."
    result = deps.last_quote  # the price the caller heard; the model never passes prices or a total
    if result is None:
        return (
            "Nothing was booked: there is no price estimate yet. Call the quote tool, read the total "
            "to the caller, and book after they agree."
        )

    try:
        start = datetime.fromisoformat(slot_start)
    except ValueError:
        return "That is not a bookable slot. Offer another.\n" + _alternatives_text(
            first_available(await _free_slots(deps), None)
        )

    started = time.perf_counter()
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

    log.info("Calendar step took %.2f s", time.perf_counter() - started)
    # Notifications run in the background: the caller hears the result without waiting for SMTP and Slack.
    task = asyncio.create_task(_notify_safely(deps, booking))
    deps.background.add(task)  # keep a reference so the task is not garbage-collected
    task.add_done_callback(deps.background.discard)
    return (
        f"Booked: {booking.slot.label()}.\n{_quote_text(result)}\n"
        "Tell the caller the time window and that a confirmation is on its way."
    )


async def _notify_safely(deps: Deps, booking: Booking) -> None:
    try:
        await _notify(deps, booking)
    except Exception as exc:  # the notifier and _publish never raise, but a background task must not fail silently
        log.error("Background notification failed: %s", type(exc).__name__)


async def wait_for_background(deps: Deps, timeout: float) -> None:
    """Wait until the pending notifications finish, but not longer than timeout seconds."""
    if not deps.background:
        return
    _, pending = await asyncio.wait(set(deps.background), timeout=timeout)
    if pending:
        log.warning("%d background notification task(s) did not finish in %s s", len(pending), timeout)


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
    if not any(d.status == "sent" for d in deliveries):
        return (
            "The message could not be delivered. Apologize, and give the caller our phone number "
            f"to call directly: {deps.config.phone}."
        )
    return "The message was passed on. Tell the caller that the owner will call you back soon."
