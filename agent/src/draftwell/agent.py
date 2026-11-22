"""The voice agent: instructions for the model, and thin tools that delegate to flows.py.
No `llm` is set here, so tests can run this agent on a text model and main.py on the voice model."""

from datetime import datetime
from zoneinfo import ZoneInfo

from livekit.agents import Agent, function_tool

from draftwell import flows
from draftwell.booking import Customer
from draftwell.flows import Deps
from draftwell.pricing import QuoteParams

INSTRUCTIONS = """\
You are the virtual assistant of Draftwell, an air duct cleaning company in Atlanta. You talk with callers by voice.
Always say you are a virtual assistant when you introduce yourself. Speak English only.

# Style
- Plain spoken sentences, no lists or markdown. One or two sentences at a time, one question at a time.
- Say numbers, phone numbers and prices the way a person would say them aloud.

# What you do
Help the caller get a price estimate and book a cleaning. Collect these details, one at a time:
name, phone number, street address with ZIP code, number of HVAC systems, number of vents
(if they do not know, ask for the approximate square footage of the home), add-ons
(dryer vent cleaning, blower cleaning, antimicrobial treatment), and the preferred day.
An email address is optional: offer it for the confirmation, and ask the caller to spell it letter by letter.

# Rules
- Check the ZIP code with the service area tool before quoting. If it is outside the area, say so, do not offer a booking, and offer to take a message for the owner.
- If the caller does not know the number of vents, ask for the approximate square footage of the home first. Do not call the quote tool until you have either the vent count or the square footage.
- Never calculate or guess prices or times. Use only what the tools return.
- Every price is an estimate. Always say that the technician confirms the final price on site.
- Offer appointment times only from the availability tool. If the caller asks about availability for a day, call the availability tool right away, before collecting their other details.
- After the caller picks a time slot, and before the read-back, ask once whether they want the confirmation by email. If yes, ask for the address.
- Before booking, read back the name, phone, address, time slot and quoted estimate. If the caller gave an email, read it back too, spelled out letter by letter. Wait for the caller to say yes. Then book.
- Right before calling the booking tool, say one short sentence like "One moment, I'm booking that now." After the tool returns, always tell the caller the result.
- If a booking fails because the time was taken, say the time is gone and offer the other times the tool gave you.
- Never agree to a discount or a price that is not from the price tool. Politely say the price is set and the technician confirms the final price on site.
- Give no mold, health or repair advice and no diagnosis. Say the technician will assess it on site.
- If the caller wants to speak to a person, you cannot transfer the call. Offer to take a message for the owner (name, phone, message), then use the message tool.
- If the message tool says the message could not be delivered or passed on, apologize and read the company phone number from the tool result to the caller so they can call directly.
- You cannot reschedule or cancel appointments. Offer to take a message for the owner instead.
"""


def today_line(now: datetime, timezone: ZoneInfo) -> str:
    """The model cannot know the date, so we tell it: 'Today is Sunday, November 22, 2026 (Atlanta time).'"""
    today = now.astimezone(timezone)
    return f"Today is {today:%A}, {today:%B} {today.day}, {today.year} (Atlanta time)."


class DraftwellAgent(Agent):
    def __init__(self, deps: Deps) -> None:
        today = today_line(deps.now(), deps.config.timezone)
        date_rule = f"# Date\n{today} Use it to turn days like 'this Thursday' into a YYYY-MM-DD date for the availability tool."
        super().__init__(instructions=INSTRUCTIONS + "\n" + date_rule)
        self.deps = deps

    @function_tool
    async def check_service_area(self, zip_code: str) -> str:
        """Check whether a ZIP code is in the service area. Call this before giving any quote.

        Args:
            zip_code: The five-digit ZIP code of the caller's address.
        """
        return flows.check_area(self.deps, zip_code)

    @function_tool
    async def get_quote(
        self,
        systems: int,
        vents: int | None = None,
        square_feet: int | None = None,
        dryer_vent: bool = False,
        blower: bool = False,
        antimicrobial: bool = False,
    ) -> str:
        """Get a price estimate. Call this whenever the caller asks about price, once the ZIP code is in the service area.
        Give the vent count if known; otherwise give the approximate square footage of the home.

        Args:
            systems: Number of HVAC systems.
            vents: Number of vents, if the caller knows it.
            square_feet: Approximate home size in square feet, only if the vent count is unknown.
            dryer_vent: True if the caller wants dryer vent cleaning.
            blower: True if the caller wants blower cleaning.
            antimicrobial: True if the caller wants the antimicrobial treatment.
        """
        return flows.quote(self.deps, QuoteParams(systems, vents, square_feet, dryer_vent, blower, antimicrobial))

    @function_tool
    async def find_available_slots(self, preferred_date: str | None = None) -> str:
        """Find free appointment times. Call this when the caller is ready to pick a time.

        Args:
            preferred_date: The caller's preferred day as YYYY-MM-DD, if they named one.
        """
        return await flows.find_slots(self.deps, preferred_date)

    @function_tool
    async def book_appointment(
        self,
        slot_start: str,
        name: str,
        phone: str,
        address: str,
        zip_code: str,
        systems: int,
        vents: int | None = None,
        square_feet: int | None = None,
        dryer_vent: bool = False,
        blower: bool = False,
        antimicrobial: bool = False,
        email: str | None = None,
    ) -> str:
        """Book the appointment. Call this only after you read all the details back and the caller said yes.

        Args:
            slot_start: The start value of the chosen slot, exactly as returned by the availability tool.
            name: The caller's full name.
            phone: The caller's phone number.
            address: The street address.
            zip_code: The five-digit ZIP code of the address.
            systems: Number of HVAC systems.
            vents: Number of vents, if known.
            square_feet: Approximate home size, only if the vent count is unknown.
            dryer_vent: True if dryer vent cleaning was requested.
            blower: True if blower cleaning was requested.
            antimicrobial: True if the antimicrobial treatment was requested.
            email: The caller's email address, if they gave one.
        """
        customer = Customer(name, phone, address, zip_code, email)
        return await flows.book(
            self.deps, slot_start, customer, QuoteParams(systems, vents, square_feet, dryer_vent, blower, antimicrobial)
        )

    @function_tool
    async def take_message_for_owner(self, name: str, phone: str, message: str) -> str:
        """Pass a message to the owner. Use it when the caller wants a person, or when we cannot serve them.

        Args:
            name: The caller's name.
            phone: The caller's phone number.
            message: What the caller wants the owner to know.
        """
        return await flows.take_message(self.deps, name, phone, message)
