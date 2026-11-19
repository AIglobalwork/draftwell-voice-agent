"""Customer and owner notifications. A failed channel is logged and never raises."""

import asyncio
import logging
import os
import smtplib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Literal

import httpx

from draftwell.booking import Booking
from draftwell.config import BusinessConfig

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotifySettings:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    owner_email: str
    slack_webhook_url: str
    sms_enabled: bool
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str

    @classmethod
    def from_env(cls) -> "NotifySettings":
        env = os.environ.get
        return cls(
            smtp_host=env("SMTP_HOST", ""),
            smtp_port=int(env("SMTP_PORT", "587")),
            smtp_user=env("SMTP_USER", ""),
            smtp_password=env("SMTP_PASSWORD", ""),
            owner_email=env("OWNER_EMAIL", ""),
            slack_webhook_url=env("SLACK_WEBHOOK_URL", ""),
            sms_enabled=env("SMS_ENABLED", "false").strip().lower() in ("true", "1", "yes"),
            twilio_account_sid=env("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=env("TWILIO_AUTH_TOKEN", ""),
            twilio_from_number=env("TWILIO_FROM_NUMBER", ""),
        )


@dataclass(frozen=True)
class Delivery:
    channel: Literal["email", "slack", "sms"]
    status: Literal["sent", "skipped", "failed"]
    recipient: str


@dataclass(frozen=True)
class Senders:
    email: Callable[[str, str, str], Awaitable[None]]  # to, subject, body
    slack: Callable[[str], Awaitable[None]]  # text
    sms: Callable[[str, str], Awaitable[None]]  # to, body


def customer_sms_text(booking: Booking, config: BusinessConfig) -> str:
    quote = booking.quote
    kind = "approximate estimate" if quote.vents_estimated else "estimate"
    return (
        f"{config.company_name}: you are booked for {booking.slot.label()}. "
        f"Our {kind} is ${quote.total}. The technician confirms the final price on site. "
        f"Questions? Call {config.phone}."
    )


def owner_booking_text(booking: Booking) -> str:
    c = booking.customer
    lines = [
        f"New booking: {c.name}",
        f"When: {booking.slot.label()}",
        f"Estimate: ${booking.quote.total}" + (" (approximate, vents estimated)" if booking.quote.vents_estimated else ""),
        f"Phone: {c.phone}",
        f"Address: {c.address} {c.zip_code}",
    ]
    if c.email:
        lines.append(f"Email: {c.email}")
    return "\n".join(lines)


def owner_message_text(name: str, phone: str, message: str) -> str:
    return f"Message for the owner from {name} ({phone}): {message}"


# Real senders. They are used only when Notifier gets no test senders.


def _send_email_blocking(settings: NotifySettings, to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _send_sms_blocking(settings: NotifySettings, to: str, body: str) -> None:
    from twilio.rest import Client  # only needed when SMS is on

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    client.messages.create(to=to, from_=settings.twilio_from_number, body=body)


def real_senders(settings: NotifySettings) -> Senders:
    async def email(to: str, subject: str, body: str) -> None:
        await asyncio.to_thread(_send_email_blocking, settings, to, subject, body)

    async def slack(text: str) -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(settings.slack_webhook_url, json={"text": text})
            response.raise_for_status()

    async def sms(to: str, body: str) -> None:
        await asyncio.to_thread(_send_sms_blocking, settings, to, body)

    return Senders(email=email, slack=slack, sms=sms)


class Notifier:
    def __init__(self, settings: NotifySettings, config: BusinessConfig, senders: Senders | None = None):
        self.settings = settings
        self.config = config  # company name and phone for the customer text
        self.senders = senders or real_senders(settings)

    async def _try(self, channel: Literal["email", "slack", "sms"], recipient: str, send: Awaitable[None]) -> Delivery:
        try:
            await send
        except Exception as exc:  # a failed notification must never break a booking
            # Log only the channel and error type: messages can contain URLs or credentials.
            log.warning("Notification via %s failed: %s", channel, type(exc).__name__)
            return Delivery(channel, "failed", recipient)
        return Delivery(channel, "sent", recipient)

    async def confirm_to_customer(self, booking: Booking) -> list[Delivery]:
        customer = booking.customer
        text = customer_sms_text(booking, self.config)
        deliveries = []
        if customer.email:
            subject = f"Your {self.config.company_name} booking"
            deliveries.append(await self._try("email", customer.email, self.senders.email(customer.email, subject, text)))
        if self.settings.sms_enabled:
            deliveries.append(await self._try("sms", customer.phone, self.senders.sms(customer.phone, text)))
        else:
            deliveries.append(Delivery("sms", "skipped", customer.phone))
        return deliveries

    async def notify_owner(self, text: str) -> list[Delivery]:
        subject = "Draftwell: " + text.splitlines()[0][:80]
        owner = self.settings.owner_email
        return [
            await self._try("email", owner, self.senders.email(owner, subject, text)),
            await self._try("slack", "owner", self.senders.slack(text)),
        ]
