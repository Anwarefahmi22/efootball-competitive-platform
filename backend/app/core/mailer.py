"""Outgoing mail, behind the smallest possible provider seam.

``MAIL_PROVIDER=console`` appends messages to the in-process ``OUTBOX``
(and logs only a masked recipient) — that is how tests and local dev
"receive" mail. ``MAIL_PROVIDER=smtp`` speaks plain SMTP via the
standard library, which covers every candidate relay (Brevo, Gmail
app-password, a future custom-domain provider) with no new dependency;
switching providers is then an environment change, not a code change.
"""
import asyncio
import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)

# Console-provider deliveries: dicts with to/subject/text/html.
OUTBOX: list[dict] = []


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}" if name else email


def _send_smtp_sync(to: str, subject: str, text_body: str, html_body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


def _send_resend_sync(to: str, subject: str, text_body: str, html_body: str) -> None:
    payload = json.dumps(
        {
            "from": settings.MAIL_FROM,
            "to": [to],
            "subject": subject,
            "text": text_body,
            "html": html_body,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        # Surface the provider's own error body in the logs — a bare
        # "403 Forbidden" cost a full diagnostic round on 2026-11-03.
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"resend api error {exc.code}: {detail}") from exc


async def send_email(to: str, subject: str, text_body: str, html_body: str) -> None:
    if settings.MAIL_PROVIDER == "resend":
        await asyncio.to_thread(_send_resend_sync, to, subject, text_body, html_body)
        logger.info("mail sent via resend to %s", _mask(to))
    elif settings.MAIL_PROVIDER == "smtp":
        await asyncio.to_thread(_send_smtp_sync, to, subject, text_body, html_body)
        logger.info("mail sent via smtp to %s", _mask(to))
    else:
        OUTBOX.append(
            {"to": to, "subject": subject, "text": text_body, "html": html_body}
        )
        logger.info("mail captured by console provider for %s", _mask(to))


async def send_verification_email(to: str, code: str) -> None:
    subject = "eFootball Arena — رمز تأكيد البريد / Verification code"
    text_body = (
        f"رمز تأكيد بريدك في eFootball Arena هو: {code}\n"
        f"ينتهي الرمز بعد 10 دقائق. إن لم تطلب هذا الرمز، تجاهل هذه الرسالة.\n\n"
        f"Your eFootball Arena verification code is: {code}\n"
        f"It expires in 10 minutes. If you did not request it, ignore this email.\n"
    )
    html_body = (
        '<div style="font-family:Arial,sans-serif;background:#0a1409;color:#eaffea;'
        'padding:24px;border-radius:12px;max-width:480px;margin:auto">'
        '<h2 style="color:#b6ff3c;margin:0 0 12px">eFootball Arena</h2>'
        '<p style="margin:0 0 8px">رمز تأكيد بريدك / Your verification code:</p>'
        f'<p style="font-size:32px;font-weight:bold;letter-spacing:6px;color:#b6ff3c;'
        f'margin:8px 0">{code}</p>'
        '<p style="color:#9fb89a;margin:0">ينتهي بعد 10 دقائق · Expires in 10 minutes</p>'
        "</div>"
    )
    await send_email(to, subject, text_body, html_body)
