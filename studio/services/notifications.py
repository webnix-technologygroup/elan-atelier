from __future__ import annotations

from smtplib import SMTPException
from urllib import error, parse, request

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from studio.models import Booking, NotificationLog


def _send_telegram(
    *,
    kind: str,
    text: str,
    booking: Booking | None,
    dedupe_key: str | None,
) -> NotificationLog | None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return None
    telegram_key = f"telegram:{dedupe_key}" if dedupe_key else None
    if (
        telegram_key
        and NotificationLog.objects.filter(dedupe_key=telegram_key).exists()
    ):
        return None
    log = NotificationLog.objects.create(
        type=kind,
        channel="telegram",
        recipient=str(chat_id),
        text=text,
        booking=booking,
        dedupe_key=telegram_key,
    )
    try:
        payload = parse.urlencode({"chat_id": chat_id, "text": text}).encode()
        endpoint = "https://api.telegram.org/bot" + token + "/sendMessage"
        with request.urlopen(endpoint, data=payload, timeout=5) as response:
            response.read()
        log.status = "sent"
        log.sent_at = timezone.now()
    except (error.URLError, TimeoutError, ValueError) as exc:
        log.status = "failed"
        log.error = f"Telegram request failed: {type(exc).__name__}"
    log.save(update_fields=["status", "sent_at", "error"])
    return log


def send_notification(
    *,
    kind: str,
    recipient: str,
    text: str,
    booking: Booking | None = None,
    dedupe_key: str | None = None,
    notify_admin: bool = False,
) -> NotificationLog | None:
    if dedupe_key and NotificationLog.objects.filter(dedupe_key=dedupe_key).exists():
        return None
    log = NotificationLog.objects.create(
        type=kind,
        channel="email",
        recipient=recipient,
        text=text,
        booking=booking,
        dedupe_key=dedupe_key,
    )
    try:
        send_mail("Élan Atelier", text, settings.DEFAULT_FROM_EMAIL, [recipient])
        log.status = "sent"
        log.sent_at = timezone.now()
    except (SMTPException, OSError, ValueError) as exc:
        log.status = "failed"
        log.error = f"Email backend failed: {type(exc).__name__}"
    log.save(update_fields=["status", "sent_at", "error"])
    if notify_admin:
        _send_telegram(
            kind=kind,
            text=text,
            booking=booking,
            dedupe_key=dedupe_key,
        )
    return log
