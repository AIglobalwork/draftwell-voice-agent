"""Conversation tests: the real agent instructions and tools on a Gemini text model (free tier).
Fake calendar and notifier only. Run with: uv run pytest -m llm -v"""

import asyncio
import os
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from livekit.agents import AgentSession
from google.genai import types
from livekit.plugins import google

from draftwell.agent import DraftwellAgent
from draftwell.config import load_business_config, load_price_list
from draftwell.flows import Deps
from fakes import FakeCalendar, RecordingNotifier, RecordingPublish

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

pytestmark = [
    pytest.mark.llm,
    pytest.mark.skipif(not os.environ.get("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY is not set"),
]

CONFIG = Path(__file__).resolve().parent.parent / "config"
NOW = datetime(2026, 12, 1, 14, tzinfo=UTC)  # Tue Dec 1, 9 AM in Atlanta
MODEL = os.environ.get("TEST_LLM_MODEL", "gemini-3.5-flash-lite")


# Free tier: 15 model requests per minute. The longest test (two turns with tool calls) makes about 7 requests:
# turn 1 = tool call(s) + answer (3), turn 2 = tool call + answer (2), judge (1), plus a retry now and then.
# Without a pause, quick tests burst past that. The longest test took ~50 s alone (earlier run), so with a
# 15 s pause it uses 7 requests per ~65 s, about 6 per minute; short tests (2-3 requests, ~10 s) about 6-7 per minute.
PAUSE_SECONDS = float(os.environ.get("LLM_TEST_PAUSE_SECONDS", "15"))


@pytest.fixture(autouse=True)
async def pause_after_test():
    yield
    await asyncio.sleep(PAUSE_SECONDS)


def make_agent(calendar=None, notifier=None) -> DraftwellAgent:
    deps = Deps(
        load_price_list(CONFIG / "pricing.yaml"),
        load_business_config(CONFIG / "business.yaml"),
        calendar or FakeCalendar(),
        notifier or RecordingNotifier(),
        RecordingPublish(),
        lambda: NOW,
    )
    return DraftwellAgent(deps)


@pytest.fixture
async def llm():
    async with google.LLM(model=MODEL, http_options=types.HttpOptions(timeout=120_000)) as model:  # timeout in ms
        yield model


DETAILS = (
    "Hi, I'm John Smith, phone 404 555 0123, 123 Peachtree Street, Atlanta, ZIP 30307. One system, 10 vents, no add-ons."
)


def agent_text(result) -> str:
    """Everything the agent said in one turn."""
    return " ".join(e.item.text_content or "" for e in result.events if e.type == "message")


async def start(llm, calendar=None, notifier=None) -> AgentSession:
    session = AgentSession(llm=llm)
    await session.start(make_agent(calendar, notifier))
    return session


async def test_quote_comes_from_tool(llm):
    async with await start(llm) as session:
        r = await session.run(user_input="ZIP 30307. One system, 14 vents and the dryer vent. How much?")
        r.expect.contains_function_call(name="get_quote")
        await r.expect.next_event(type="message").judge(
            llm, intent="States an estimate of $718 and says the technician confirms the final price on site."
        )


async def test_unknown_vents_asks_square_feet(llm):
    async with await start(llm) as session:
        r = await session.run(user_input="ZIP 30307, one system. I don't know how many vents. What would it cost?")
        with pytest.raises(AssertionError):
            r.expect.contains_function_call(name="get_quote")
        await r.expect.next_event(type="message").judge(llm, intent="Asks for the approximate square footage of the home.")


async def test_out_of_area_zip(llm):
    async with await start(llm) as session:
        r = await session.run(user_input="I live in New York, ZIP 10001. Can you clean my ducts?")
        r.expect.contains_function_call(name="check_service_area")
        await r.expect.next_event(type="message").judge(
            llm, intent="Says the address is outside the service area and does not offer to book an appointment."
        )


async def test_wants_a_person(llm):
    async with await start(llm) as session:
        r = await session.run(user_input="I want to talk to a real person, not a robot.")
        await r.expect.next_event(type="message").judge(llm, intent="Offers to take a message for the owner.")


async def test_mold_question(llm):
    async with await start(llm) as session:
        r = await session.run(user_input="I see black spots in my vents. Is that mold? Is it dangerous?")
        await r.expect.next_event(type="message").judge(
            llm, intent="Does not diagnose the problem or give health advice, and says the technician will assess it on site."
        )


async def test_discount_request(llm):
    async with await start(llm) as session:
        await session.run(user_input="ZIP 30307. One system, 10 vents. How much?")
        r = await session.run(user_input="Can you do it for $300?")
        await r.expect.next_event(type="message").judge(
            llm, intent="Does not agree to a price outside the price list; says the price is set or an estimate."
        )


async def test_slot_taken(llm):
    # rival="before": another booking lands in the same slot first, so book_slot raises SlotTakenError
    async with await start(llm, FakeCalendar(rival="before")) as session:
        await session.run(user_input=DETAILS + " What times do you have on Thursday December 3rd?")
        r = await session.run(
            user_input="The Thursday 8 AM slot works. No email. Those details are all correct, please book it now."
        )
        r.expect.contains_function_call(name="book_appointment")
        await r.expect.next_event(type="message").judge(
            llm, intent="Says the requested time is no longer available and offers other times."
        )


async def test_message_not_delivered_gives_phone(llm):
    phone = load_business_config(CONFIG / "business.yaml").phone
    # owner_fails=True: both email and Slack fail, so the message tool reports it was not delivered
    async with await start(llm, notifier=RecordingNotifier(owner_fails=True)) as session:
        await session.run(user_input="I want to talk to a real person.")
        r = await session.run(
            user_input="Yes, please take a message. I'm John Smith, phone 404 555 0123. "
            "Tell the owner I need a call back about a quote. Please send it now."
        )
        r.expect.contains_function_call(name="take_message_for_owner")
        await r.expect.next_event(type="message").judge(
            llm, intent=f"Apologizes that the message could not be passed on and gives the company phone number {phone}."
        )


async def test_this_thursday_uses_todays_date(llm):
    # NOW is Tue Dec 1, 2026, so "this coming Thursday" is 2026-12-03
    async with await start(llm) as session:
        r = await session.run(user_input="Do you have anything this coming Thursday?")
        r.expect.contains_function_call(name="find_available_slots", arguments={"preferred_date": "2026-12-03"})


async def test_offers_email_after_slot_choice(llm):
    async with await start(llm) as session:
        await session.run(user_input=DETAILS + " What times do you have on Thursday December 3rd?")
        r = await session.run(user_input="The Thursday 8 AM slot works for me.")
        await r.expect.next_event(type="message").judge(
            llm, intent="Asks whether the caller wants the confirmation by email."
        )


async def test_never_guesses_a_title(llm):
    # Live call: speech recognition heard "Mine" for "Mike", and the agent said "Ms. Johnson".
    async with await start(llm) as session:
        r1 = await session.run(user_input="Hi, this is Mine Johnson. I'd like to get my air ducts cleaned.")
        r2 = await session.run(user_input="Sure, my phone number is 404 555 0123.")
        said = agent_text(r1) + " " + agent_text(r2)
        assert not re.search(r"\b(Mr|Mrs|Ms|Miss)\b", said), said

