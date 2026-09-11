"""
Google Calendar integration.

Approved events are pushed to a shared college calendar through a service
account. Every attendee also gets a one-click "Add to Google Calendar" link and
an .ics file, which work even when the service account isn't configured.
"""

import logging
from datetime import timezone as dt_timezone
from pathlib import Path
from urllib.parse import quote, urlencode

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def is_configured():
    return bool(settings.GOOGLE_CALENDAR_ID) and Path(settings.GOOGLE_SERVICE_ACCOUNT_FILE).is_file()


def get_calendar_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_file(
        settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def _details_url(event):
    return f"{settings.SITE_URL}/events/details/{event.id}/"


def _event_body(event):
    return {
        "summary": f"{event.title} · {event.association.name}",
        "description": f"{event.description}\n\nOrganised by {event.association.name}.\nDetails: {_details_url(event)}",
        "start": {"dateTime": event.date_time.isoformat(), "timeZone": settings.TIME_ZONE},
        "end": {"dateTime": event.end_time.isoformat(), "timeZone": settings.TIME_ZONE},
        "location": str(event.location),
    }


def create_google_calendar_event(event):
    service = get_calendar_service()
    created = service.events().insert(calendarId=settings.GOOGLE_CALENDAR_ID, body=_event_body(event)).execute()
    return created.get("id")


def update_google_calendar_event(event):
    service = get_calendar_service()
    service.events().update(
        calendarId=settings.GOOGLE_CALENDAR_ID,
        eventId=event.google_calendar_event_id,
        body=_event_body(event),
    ).execute()


def delete_google_calendar_event(event_id):
    service = get_calendar_service()
    service.events().delete(calendarId=settings.GOOGLE_CALENDAR_ID, eventId=event_id).execute()


def sync_event(event):
    """Create or update `event` on the shared calendar. Returns (ok, message)."""
    if not is_configured():
        return False, "Google Calendar isn't configured, so it was not synced."
    try:
        if event.google_calendar_event_id:
            update_google_calendar_event(event)
        else:
            event.google_calendar_event_id = create_google_calendar_event(event)
            event.save(update_fields=['google_calendar_event_id'])
    except Exception as exc:
        logger.exception("Google Calendar sync failed for event %s", event.pk)
        return False, f"Google Calendar sync failed: {exc}"
    return True, "Added to the college Google Calendar."


def unsync_event(event):
    """Remove `event` from the shared calendar if it was synced. Returns True on success."""
    if not event.google_calendar_event_id or not is_configured():
        return False
    try:
        delete_google_calendar_event(event.google_calendar_event_id)
    except Exception:
        logger.exception("Could not delete Google Calendar entry for event %s", event.pk)
        return False
    event.google_calendar_event_id = None
    event.save(update_fields=['google_calendar_event_id'])
    return True


def shared_calendar_url():
    if not settings.GOOGLE_CALENDAR_ID:
        return ''
    return (
        "https://calendar.google.com/calendar/embed?src="
        f"{quote(settings.GOOGLE_CALENDAR_ID)}&ctz={quote(settings.TIME_ZONE)}"
    )


# --- Personal calendar links ---------------------------------------------------

def _utc_stamp(value):
    return value.astimezone(dt_timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def google_calendar_link(event):
    params = {
        'action': 'TEMPLATE',
        'text': event.title,
        'dates': f"{_utc_stamp(event.date_time)}/{_utc_stamp(event.end_time)}",
        'details': f"{event.description}\n\nOrganised by {event.association.name}.\n{_details_url(event)}",
        'location': str(event.location),
    }
    return "https://calendar.google.com/calendar/render?" + urlencode(params)


def _ics_escape(text):
    return (
        str(text).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
        .replace('\r\n', '\\n').replace('\n', '\\n')
    )


def _fold(line):
    """RFC 5545 line folding: continuation lines start with a single space."""
    chunks = [line[:73]]
    rest = line[73:]
    while rest:
        chunks.append(' ' + rest[:72])
        rest = rest[72:]
    return '\r\n'.join(chunks)


def build_ics(events, calendar_name='CommUnity Events'):
    stamp = _utc_stamp(timezone.now())
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//CommUnity//College Events//EN',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_ics_escape(calendar_name)}',
        f'X-WR-TIMEZONE:{settings.TIME_ZONE}',
    ]
    for event in events:
        lines += [
            'BEGIN:VEVENT',
            f'UID:community-event-{event.id}@{settings.SITE_URL.split("//")[-1]}',
            f'DTSTAMP:{stamp}',
            f'DTSTART:{_utc_stamp(event.date_time)}',
            f'DTEND:{_utc_stamp(event.end_time)}',
            f'SUMMARY:{_ics_escape(event.title)}',
            f'DESCRIPTION:{_ics_escape(event.description)}',
            f'LOCATION:{_ics_escape(event.location)}',
            f'ORGANIZER;CN={_ics_escape(event.association.name)}:mailto:{settings.DEFAULT_FROM_EMAIL.split("<")[-1].rstrip(">")}',
            f'URL:{_details_url(event)}',
            f'STATUS:{"CANCELLED" if event.status == "cancelled" else "CONFIRMED"}',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    return '\r\n'.join(_fold(line) for line in lines) + '\r\n'
