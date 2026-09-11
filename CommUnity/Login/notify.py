"""Deliver a notification in-app and (optionally) by e-mail in one call."""

import logging

from django.conf import settings
from django.core.mail import send_mass_mail

from .models import Notification

logger = logging.getLogger(__name__)


def absolute_url(path):
    if not path or path.startswith('http'):
        return path
    return f"{settings.SITE_URL}{path}"


def notify(recipients, title, message='', link='', kind='info', email=True):
    """
    Create a Notification for every profile in `recipients` and e-mail them.

    E-mail failures are logged rather than raised, so a missing SMTP setup
    never breaks the action that triggered the notification.
    """
    profiles = list({p.pk: p for p in recipients if p is not None}.values())
    if not profiles:
        return

    Notification.objects.bulk_create([
        Notification(recipient=p, title=title, message=message, link=link, kind=kind)
        for p in profiles
    ])

    if not email:
        return
    body = message
    if link:
        body += f"\n\nOpen in CommUnity: {absolute_url(link)}"
    mails = [
        (f"[CommUnity] {title}", body, settings.DEFAULT_FROM_EMAIL, [p.id.email])
        for p in profiles if p.id.email
    ]
    try:
        send_mass_mail(mails, fail_silently=False)
    except Exception:
        logger.exception("Could not send notification e-mail '%s'", title)
