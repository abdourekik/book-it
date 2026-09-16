"""Transactional email.

Two senders behind one interface:

  * ResendSender  - used when RESEND_API_KEY is configured
  * ConsoleSender - used otherwise; prints instead of sending

That fallback is deliberate. Without it, running the app locally either needs an API key
(so a contributor cannot start it) or crashes on the first booking. With it, development
and the test suite see exactly the same code path, and the email content is visible in
the terminal instead of arriving in a stranger's inbox.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    html: str


class ConsoleSender:
    """Logs the email instead of sending it. The default in development and tests."""

    name = "console"

    def send(self, email: Email) -> None:
        logger.info(
            "EMAIL (not sent - no RESEND_API_KEY) to=%s subject=%s", email.to, email.subject
        )


class ResendSender:
    """Sends through Resend's HTTP API."""

    name = "resend"

    def __init__(self, api_key: str, sender: str) -> None:
        self._api_key = api_key
        self._sender = sender

    def send(self, email: Email) -> None:
        # Imported here rather than at module level so the package is only required when
        # it is actually configured.
        import resend

        resend.api_key = self._api_key
        resend.Emails.send(
            {
                "from": self._sender,
                "to": [email.to],
                "subject": email.subject,
                "html": email.html,
            }
        )


def build_sender() -> ConsoleSender | ResendSender:
    key = settings.resend_api_key
    if key is None or not key.get_secret_value():
        return ConsoleSender()
    return ResendSender(key.get_secret_value(), settings.email_from)


# One sender for the process. Tests replace this via the `sender` fixture rather than
# monkeypatching the network.
_sender: ConsoleSender | ResendSender | None = None


def get_sender():
    global _sender
    if _sender is None:
        _sender = build_sender()
    return _sender


def set_sender(sender) -> None:
    """Swap the sender - used by tests, and by nothing else."""
    global _sender
    _sender = sender


def send(email: Email) -> None:
    """Send one email, swallowing failures.

    An email provider being down must never turn a successful booking into an error.
    The appointment is already committed; the customer can still see it through their
    link. So this logs and moves on rather than raising.
    """
    try:
        get_sender().send(email)
    except Exception:  # noqa: BLE001 - deliberately broad; see the docstring
        logger.exception("Failed to send email to %s", email.to)


# ----------------------------------------------------------------- templates


def _local(when: datetime, timezone: str) -> str:
    """Render a UTC instant in the business's timezone, spelled out in full.

    Ambiguity in an appointment email is expensive: the reader has to be able to write
    it straight into their calendar without doing arithmetic.
    """
    zone = ZoneInfo(timezone)
    return when.astimezone(zone).strftime("%A %d %B %Y at %H:%M") + f" ({timezone})"


def _layout(heading: str, body: str) -> str:
    return f"""\
<div style="font-family:system-ui,-apple-system,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#0f172a">
  <h1 style="font-size:20px;margin:0 0 16px">{heading}</h1>
  {body}
  <p style="margin-top:32px;font-size:12px;color:#64748b">Sent by Book-it</p>
</div>"""


def _details(business_name: str, service_name: str, when: str) -> str:
    return f"""\
  <table style="font-size:14px;line-height:1.6;border-collapse:collapse">
    <tr><td style="padding-right:16px;color:#64748b">Where</td><td>{business_name}</td></tr>
    <tr><td style="padding-right:16px;color:#64748b">What</td><td>{service_name}</td></tr>
    <tr><td style="padding-right:16px;color:#64748b">When</td><td>{when}</td></tr>
  </table>"""


def booking_confirmation(
    *,
    to: str,
    customer_name: str,
    business_name: str,
    service_name: str,
    starts_at: datetime,
    timezone: str,
    manage_url: str,
) -> Email:
    when = _local(starts_at, timezone)
    return Email(
        to=to,
        subject=f"Booking confirmed - {business_name}, {when}",
        html=_layout(
            f"You are booked in, {customer_name}",
            _details(business_name, service_name, when)
            + f"""
  <p style="margin-top:24px">
    <a href="{manage_url}" style="display:inline-block;background:#0f172a;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-size:14px">
      View or cancel this booking
    </a>
  </p>
  <p style="font-size:12px;color:#64748b">Keep this link - it is how you manage the booking.</p>""",
        ),
    )


def booking_cancellation(
    *,
    to: str,
    customer_name: str,
    business_name: str,
    service_name: str,
    starts_at: datetime,
    timezone: str,
    booking_url: str,
) -> Email:
    when = _local(starts_at, timezone)
    return Email(
        to=to,
        subject=f"Booking cancelled - {business_name}, {when}",
        html=_layout(
            f"Your booking was cancelled, {customer_name}",
            _details(business_name, service_name, when)
            + f"""
  <p style="margin-top:24px;font-size:14px">
    If this was not you, <a href="{booking_url}">check the booking</a> or contact {business_name}.
  </p>""",
        ),
    )


def booking_reminder(
    *,
    to: str,
    customer_name: str,
    business_name: str,
    service_name: str,
    starts_at: datetime,
    timezone: str,
    manage_url: str,
) -> Email:
    when = _local(starts_at, timezone)
    return Email(
        to=to,
        subject=f"Tomorrow: {service_name} at {business_name}",
        html=_layout(
            f"See you tomorrow, {customer_name}",
            _details(business_name, service_name, when)
            + f"""
  <p style="margin-top:24px;font-size:14px">
    Cannot make it? <a href="{manage_url}">Cancel or reschedule</a> so someone else can take the slot.
  </p>""",
        ),
    )
