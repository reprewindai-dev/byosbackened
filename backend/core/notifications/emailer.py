"""Transactional email delivery helpers."""
from __future__ import annotations

import asyncio
import json
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

import httpx

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _resend_enabled() -> bool:
    return bool(settings.resend_api_key and settings.mail_from)


def _smtp_enabled() -> bool:
    return bool(settings.smtp_host and settings.mail_from)


def _build_message(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = to_email
    msg["Subject"] = subject
    if reply_to or settings.mail_reply_to:
        msg["Reply-To"] = reply_to or settings.mail_reply_to
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")
    return msg


def _send_message(msg: EmailMessage) -> None:
    if not _smtp_enabled():
        logger.warning("SMTP not configured; skipping email delivery to %s", msg.get("To"))
        return

    smtp_cls = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
    with smtp_cls(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls and not settings.smtp_use_ssl:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password or "")
        server.send_message(msg)


def _send_via_resend(
    *,
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> None:
    payload = {
        "from": settings.mail_from,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
    }
    if html_body:
        payload["html"] = html_body
    effective_reply_to = reply_to or settings.mail_reply_to
    if effective_reply_to:
        payload["reply_to"] = effective_reply_to

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=15.0) as client:
        response = client.post("https://api.resend.com/emails", headers=headers, content=json.dumps(payload))
        response.raise_for_status()


async def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> bool:
    """Send a transactional email via Resend API or SMTP fallback."""
    if _resend_enabled():
        await asyncio.to_thread(
            _send_via_resend,
            to_email=to_email,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            reply_to=reply_to,
        )
        return True

    msg = _build_message(to_email, subject, text_body, html_body=html_body, reply_to=reply_to)
    await asyncio.to_thread(_send_message, msg)
    return True


async def send_trial_welcome_email(
    *,
    to_email: str,
    workspace_name: str,
    tier: str,
    license_key: str,
    download_url: str,
    expires_at_iso: str,
) -> bool:
    subject = f"Your Veklom {tier.title()} trial is ready"
    text_body = (
        f"Hello {workspace_name},\n\n"
        f"Your {tier} trial key is ready.\n\n"
        f"License key: {license_key}\n"
        f"Download link: {download_url}\n"
        f"Expires at: {expires_at_iso}\n\n"
        "Install the backend, add the license key, and start the service.\n"
    )
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111; line-height: 1.5;">
        <p>Hello {workspace_name},</p>
        <p>Your <strong>{tier}</strong> trial key is ready.</p>
        <p><strong>License key:</strong> <code>{license_key}</code><br />
           <strong>Download link:</strong> <a href="{download_url}">{download_url}</a><br />
           <strong>Expires at:</strong> {expires_at_iso}</p>
        <p>Install the backend, add the key, and start the service.</p>
      </body>
    </html>
    """.strip()
    return await send_email(to_email, subject, text_body, html_body=html_body)
