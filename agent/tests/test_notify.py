from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from draftwell.booking import Booking, Customer
from draftwell.config import load_business_config, load_price_list
from draftwell.notify import (
    Delivery,
    Notifier,
    NotifySettings,
    Senders,
    customer_sms_text,
    owner_booking_text,
    owner_message_text,
)
from draftwell.pricing import QuoteParams, calculate_quote
from draftwell.scheduling import Slot
from fakes import RecordingSenders

CONFIG = Path(__file__).resolve().parent.parent / "config"
CFG = load_business_config(CONFIG / "business.yaml")
PRICES = load_price_list(CONFIG / "pricing.yaml")
ET = ZoneInfo("America/New_York")
CUSTOMER = Customer("John Smith", "+14045550123", "123 Peachtree St NE, Atlanta, GA", "30307", "john@example.com")
QUOTE_718 = calculate_quote(QuoteParams(1, 14, None, dryer_vent=True), PRICES)
BOOKING_718 = Booking(
    "evt-1", Slot(datetime(2026, 12, 3, 8, tzinfo=ET), datetime(2026, 12, 3, 12, tzinfo=ET)), CUSTOMER, QUOTE_718
)


def settings(**overrides) -> NotifySettings:
    values = dict(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="bot@example.com",
        smtp_password="secret",
        owner_email="owner@example.com",
        slack_webhook_url="https://hooks.example.com/x",
        sms_enabled=True,
        twilio_account_sid="",
        twilio_auth_token="",
        twilio_from_number="",
    )
    values.update(overrides)
    return NotifySettings(**values)


def make_notifier(s: NotifySettings, rec: RecordingSenders) -> Notifier:
    return Notifier(s, CFG, senders=Senders(email=rec.email, slack=rec.slack_send, sms=rec.sms_send))


def test_customer_text():
    t = customer_sms_text(BOOKING_718, CFG)
    for part in ["Draftwell", "Thu, Dec 3, 8 AM–12 PM", "$718", "final price", "(404) 555-0142"]:
        assert part in t


def test_owner_booking_text():
    t = owner_booking_text(BOOKING_718)
    for part in ["New booking", "John Smith", "Thu, Dec 3, 8 AM–12 PM", "$718", CUSTOMER.phone, CUSTOMER.address]:
        assert part in t


def test_owner_message_text():
    t = owner_message_text("Mary Lee", "+14045550199", "Call me back")
    assert "Mary Lee" in t and "+14045550199" in t and "Call me back" in t


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("SMS_ENABLED", "TRUE")
    s = NotifySettings.from_env()
    assert s.smtp_host == "smtp.test" and s.smtp_port == 2525 and s.sms_enabled is True
    monkeypatch.setenv("SMS_ENABLED", "false")
    assert NotifySettings.from_env().sms_enabled is False


async def test_sms_skipped_when_disabled():
    rec = RecordingSenders()
    n = make_notifier(settings(sms_enabled=False), rec)
    d = await n.confirm_to_customer(BOOKING_718)
    assert Delivery("sms", "skipped", CUSTOMER.phone) in d
    assert rec.sms == []


async def test_sms_sent_when_enabled():
    rec = RecordingSenders()
    d = await make_notifier(settings(), rec).confirm_to_customer(BOOKING_718)
    assert Delivery("sms", "sent", CUSTOMER.phone) in d
    assert Delivery("email", "sent", "john@example.com") in d
    assert rec.sms[0][0] == CUSTOMER.phone and "$718" in rec.sms[0][1]


async def test_customer_without_email_gets_no_email():
    customer = Customer("Ann Roe", "+14045550111", "1 Main St, Atlanta, GA", "30307")
    booking = Booking("evt-2", BOOKING_718.slot, customer, QUOTE_718)
    rec = RecordingSenders()
    d = await make_notifier(settings(), rec).confirm_to_customer(booking)
    assert [x.channel for x in d] == ["sms"]
    assert rec.emails == []


async def test_notify_owner_sends_email_and_slack():
    rec = RecordingSenders()
    d = await make_notifier(settings(), rec).notify_owner("New booking from John")
    assert {(x.channel, x.status, x.recipient) for x in d} == {
        ("email", "sent", "owner@example.com"),
        ("slack", "sent", "owner"),
    }
    assert rec.slack == ["New booking from John"]


async def test_failed_channel_does_not_raise():
    rec = RecordingSenders(slack_raises=True)
    d = await make_notifier(settings(), rec).notify_owner("New booking …")
    assert {(x.channel, x.status) for x in d} == {("slack", "failed"), ("email", "sent")}
