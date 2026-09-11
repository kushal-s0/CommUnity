"""Scheduling rules and the event approval workflow."""

from datetime import timedelta

from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from Login.models import UserProfile
from Login.notify import notify

from . import google_calendar
from .models import Event, EventLog, FacultyLockDate


# --- Scheduling ---------------------------------------------------------------

def locked_date_for(date_time):
    return FacultyLockDate.objects.filter(locked_date=timezone.localtime(date_time).date()).first()


def find_conflicts(date_time, duration, location, exclude_id=None, statuses=('approved',)):
    """Events at the same venue whose time range overlaps [date_time, date_time + duration)."""
    if location is None or location.is_online:
        return []
    end = date_time + timedelta(hours=duration)
    longest = Event.objects.aggregate(longest=Max('duration'))['longest'] or 0
    candidates = Event.objects.filter(
        location=location,
        status__in=statuses,
        date_time__lt=end,
        date_time__gt=date_time - timedelta(hours=longest),
    ).select_related('association')
    if exclude_id:
        candidates = candidates.exclude(id=exclude_id)
    return [event for event in candidates if event.end_time > date_time]


def describe_conflict(event):
    start = timezone.localtime(event.date_time)
    end = timezone.localtime(event.end_time)
    return (
        f"{event.location} is already booked for “{event.title}” ({event.association.name}) "
        f"on {start:%d %b} from {start:%I:%M %p} to {end:%I:%M %p}."
    )


def slot_errors(date_time, duration, location, exclude_id=None):
    """Human-readable reasons the slot can't be used; empty when it's free."""
    errors = []
    if date_time < timezone.now():
        errors.append("The event must be scheduled in the future.")
    lock = locked_date_for(date_time)
    if lock:
        reason = f" ({lock.reason})" if lock.reason else ''
        errors.append(f"{lock.locked_date:%d %b %Y} is reserved by faculty{reason}. Please pick another date.")
    errors.extend(describe_conflict(e) for e in find_conflicts(date_time, duration, location, exclude_id))
    return errors


# --- Workflow -----------------------------------------------------------------

def log(event, action, actor=None, note=''):
    EventLog.objects.create(event=event, action=action, actor=actor, note=note)


def followers_of(association):
    return [
        profile for profile in UserProfile.objects.select_related('id').exclude(preferences=None)
        if association.pk in profile.followed_ids
    ]


def submit_event(event, actor, resubmitted=False):
    """Log the submission and ask the faculty in-charge to review it."""
    log(event, 'updated' if resubmitted else 'created', actor)
    faculty = event.association.faculty_incharge
    verb = 'updated and resubmitted' if resubmitted else 'submitted'
    notify(
        [faculty.id],
        f"Approval needed: {event.title}",
        f"{actor.display_name} {verb} “{event.title}” for {event.association.name}, "
        f"scheduled on {timezone.localtime(event.date_time):%d %b %Y, %I:%M %p} at {event.location}.",
        link=reverse('approve_clubs'),
        kind='warning',
    )


def review_event(event, faculty, action, remarks=''):
    """
    Approve or reject a pending event on behalf of `faculty`.

    Returns (ok, message). Approval re-checks venue conflicts and reserved
    dates, because two pending requests for the same slot can both exist.
    """
    remarks = (remarks or '').strip()
    details_link = reverse('event_details', args=[event.id])

    if event.status != 'pending':
        return False, f"“{event.title}” has already been {event.get_status_display().lower()}."

    if action == 'approve':
        conflicts = find_conflicts(event.date_time, event.duration, event.location, exclude_id=event.id)
        if conflicts:
            return False, f"Can't approve “{event.title}”: {describe_conflict(conflicts[0])}"
        lock = locked_date_for(event.date_time)
        if lock:
            return False, f"Can't approve “{event.title}”: {lock.locked_date:%d %b %Y} is a reserved date."

        event.status = 'approved'
        event.approved_by = faculty
        event.remarks = remarks
        event.reviewed_at = timezone.now()
        event.save()
        log(event, 'approved', faculty.id, remarks)

        synced, calendar_message = google_calendar.sync_event(event)
        if synced:
            log(event, 'calendar')

        note = f"\n\nFaculty remarks: {remarks}" if remarks else ''
        notify(
            [event.created_by],
            f"Event approved: {event.title}",
            f"{faculty.id.display_name} approved “{event.title}”. It is now on the college calendar.{note}",
            link=details_link,
            kind='success',
        )
        notify(
            followers_of(event.association),
            f"New event from {event.association.name}",
            f"“{event.title}” on {timezone.localtime(event.date_time):%d %b, %I:%M %p} at {event.location}.",
            link=details_link,
            email=False,
        )
        return True, f"“{event.title}” approved. {calendar_message}"

    if action == 'reject':
        event.status = 'rejected'
        event.remarks = remarks
        event.reviewed_at = timezone.now()
        event.save()
        log(event, 'rejected', faculty.id, remarks)
        notify(
            [event.created_by],
            f"Event not approved: {event.title}",
            f"{faculty.id.display_name} did not approve “{event.title}”."
            + (f"\n\nReason: {remarks}" if remarks else '')
            + "\n\nYou can edit the event and resubmit it.",
            link=details_link,
            kind='danger',
        )
        return True, f"“{event.title}” rejected. The organiser has been notified."

    return False, "Unknown action."


def cancel_event(event, actor, reason=''):
    """Cancel an event, remove it from Google Calendar and tell everyone involved."""
    was_approved = event.status == 'approved'
    event.status = 'cancelled'
    event.save(update_fields=['status'])
    google_calendar.unsync_event(event)
    log(event, 'cancelled', actor, reason)

    message = f"“{event.title}” ({event.association.name}) has been cancelled."
    if reason:
        message += f"\n\nReason: {reason}"
    recipients = [r.participant for r in event.registrations.select_related('participant__id')]
    recipients += [event.created_by]
    if was_approved:
        recipients.append(event.association.faculty_incharge.id)
    notify(
        [p for p in recipients if p.pk != actor.pk],
        f"Event cancelled: {event.title}",
        message,
        link=reverse('event_details', args=[event.id]),
        kind='danger',
    )
