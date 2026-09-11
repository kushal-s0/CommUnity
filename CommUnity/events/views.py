import csv
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from committees.models import Associations
from Login.notify import notify
from Login.permissions import CORE_MEMBER, FACULTY, core_member_required, get_core_member, get_faculty, get_profile
from members.models import CoreMember

from . import google_calendar
from .ai_report import active_provider, generate_report
from .forms import EventForm, EventReportForm, ReportEditForm
from .models import Event, EventRegistration, FacultyLockDate, Location
from .pdf import build_report_pdf
from .services import (cancel_event, describe_conflict, find_conflicts, log, review_event, slot_errors,
                       submit_event)

EVENT_RELATIONS = ('association__faculty_incharge__id__id', 'location', 'created_by__id', 'approved_by__id')


def _access(request, event):
    """Return (profile, is_organiser, is_reviewer) for the current user and `event`."""
    profile = get_profile(request.user)
    if profile is None:
        return None, False, False
    is_organiser = event.created_by_id == profile.pk or (
        profile.role == CORE_MEMBER
        and CoreMember.objects.filter(id=profile, association_id=event.association_id).exists()
    )
    is_reviewer = profile.role == FACULTY and event.association.faculty_incharge_id == profile.pk
    return profile, is_organiser, is_reviewer


def _get_event(event_id):
    return get_object_or_404(Event.objects.select_related(*EVENT_RELATIONS), id=event_id)


# --- Browsing -------------------------------------------------------------------

def event_list(request):
    when = request.GET.get('when', 'upcoming')
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')

    events = (
        Event.objects.filter(status='approved')
        .select_related('association', 'location')
        .annotate(reg_count=Count('registrations'))
    )
    if query:
        events = events.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(association__name__icontains=query)
        )
    if category:
        events = events.filter(association__category=category)

    if when == 'past':
        event_rows = [e for e in events.order_by('-date_time') if e.is_completed]
    else:
        when = 'upcoming'
        event_rows = [e for e in events.order_by('date_time') if not e.is_completed]

    page = Paginator(event_rows, 12).get_page(request.GET.get('page'))
    return render(request, 'events/event_list.html', {
        'page': page,
        'when': when,
        'query': query,
        'category': category,
        'categories': [c for c, _ in Associations.CATEGORY if c != 'None'],
    })


def view_calendar(request):
    today = timezone.localdate()
    return render(request, 'events/view_calendar.html', {
        'categories': [c for c, _ in Associations.CATEGORY if c != 'None'],
        'lock_dates': FacultyLockDate.objects.filter(locked_date__gte=today)[:6],
        'shared_calendar_url': google_calendar.shared_calendar_url(),
    })


def get_calendar_events(request):
    """JSON feed for FullCalendar: approved events plus reserved dates as background."""
    events = Event.objects.filter(status='approved').select_related('association', 'location')
    start, end = parse_datetime(request.GET.get('start', '') or ''), parse_datetime(request.GET.get('end', '') or '')
    if start and end:
        events = events.filter(date_time__lt=end, date_time__gte=start - timedelta(days=3))

    feed = [
        {
            'id': event.id,
            'title': event.title,
            'start': event.date_time.isoformat(),
            'end': event.end_time.isoformat(),
            'url': reverse('event_details', args=[event.id]),
            'classNames': [f"cat-{event.association.category.lower()}"],
            'extendedProps': {
                'location': str(event.location),
                'association': event.association.name,
                'category': event.association.category_label,
            },
        }
        for event in events
    ]
    feed += [
        {
            'start': lock.locked_date.isoformat(),
            'allDay': True,
            'display': 'background',
            'title': lock.reason or 'Reserved',
            'classNames': ['locked-day'],
        }
        for lock in FacultyLockDate.objects.all()
    ]
    return JsonResponse(feed, safe=False)


def calendar_feed(request):
    """Subscribable iCal feed of every approved event (recent and upcoming)."""
    events = Event.objects.filter(
        status='approved', date_time__gte=timezone.now() - timedelta(days=180)
    ).select_related('association', 'location')
    response = HttpResponse(google_calendar.build_ics(events), content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = 'inline; filename="community-events.ics"'
    return response


def event_ics(request, event_id):
    event = get_object_or_404(Event.objects.select_related('association', 'location'), id=event_id, status='approved')
    response = HttpResponse(google_calendar.build_ics([event], calendar_name=event.title),
                            content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="event-{event.id}.ics"'
    return response


def event_details(request, event_id):
    event = _get_event(event_id)
    profile, is_organiser, is_reviewer = _access(request, event)
    if event.status != 'approved' and not (is_organiser or is_reviewer or request.user.is_staff):
        raise Http404("Event not found")

    registration = EventRegistration.objects.filter(event=event, participant=profile).first() if profile else None
    context = {
        'event': event,
        'is_organiser': is_organiser,
        'is_reviewer': is_reviewer,
        'registration': registration,
        'registration_count': event.registrations.count(),
        'can_register_role': profile is None or profile.role != FACULTY,
        'logs': event.logs.select_related('actor'),
        'google_link': google_calendar.google_calendar_link(event) if event.status == 'approved' else '',
        'can_generate_report': is_organiser and event.status == 'approved' and event.is_completed,
        'more_events': [
            e for e in Event.objects.filter(association=event.association, status='approved',
                                            date_time__gte=timezone.now()).exclude(id=event.id)[:3]
        ],
    }
    if is_reviewer and event.status == 'pending':
        context['conflicts'] = [describe_conflict(c) for c in
                                find_conflicts(event.date_time, event.duration, event.location, exclude_id=event.id)]
    return render(request, 'events/event_details.html', context)


# --- Organiser actions -----------------------------------------------------------

@core_member_required
def create_event(request):
    core = get_core_member(request.user)
    association = core.association
    if association is None:
        messages.error(request, "Create or join a club/committee before scheduling events.")
        return redirect('dashboard')
    if not association.is_visible:
        messages.error(request, f"{association.name} must be approved by the faculty in-charge before it can host events.")
        return redirect('dashboard')

    form = EventForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.association = association
        event.created_by = core.id
        event.status = 'pending'
        event.save()
        submit_event(event, core.id)
        messages.success(
            request,
            f"“{event.title}” was sent to {association.faculty_incharge.id.display_name} for approval.",
        )
        return redirect('event_details', event_id=event.id)

    return render(request, 'events/event_form.html', {'form': form, 'association': association, 'mode': 'create'})


@login_required
def edit_event(request, event_id):
    event = _get_event(event_id)
    profile, is_organiser, _ = _access(request, event)
    if not is_organiser:
        messages.error(request, "Only the organising team can edit this event.")
        return redirect('event_details', event_id=event.id)
    if event.status not in ('pending', 'rejected'):
        messages.info(request, "Approved events can't be edited. Cancel it and submit a new one, "
                               "or contact the faculty in-charge.")
        return redirect('event_details', event_id=event.id)

    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.status = 'pending'
        event.reviewed_at = None
        event.save()
        submit_event(event, profile, resubmitted=True)
        messages.success(request, f"Changes saved. “{event.title}” was resubmitted for approval.")
        return redirect('event_details', event_id=event.id)

    return render(request, 'events/event_form.html', {
        'form': form, 'association': event.association, 'mode': 'edit', 'event': event,
    })


@login_required
@require_POST
def cancel_event_view(request, event_id):
    event = _get_event(event_id)
    profile, is_organiser, is_reviewer = _access(request, event)
    if not (is_organiser or is_reviewer):
        messages.error(request, "You can't cancel this event.")
    elif event.status in ('cancelled', 'rejected') or event.is_completed:
        messages.error(request, "This event can no longer be cancelled.")
    else:
        cancel_event(event, profile, request.POST.get('reason', '').strip())
        messages.success(request, f"“{event.title}” was cancelled and everyone registered has been notified.")
    return redirect('event_details', event_id=event.id)


@login_required
@require_POST
def review_event_view(request, event_id):
    event = _get_event(event_id)
    _, _, is_reviewer = _access(request, event)
    if not is_reviewer:
        messages.error(request, "Only the faculty in-charge can review this event.")
        return redirect('event_details', event_id=event.id)

    ok, message = review_event(event, get_faculty(request.user), request.POST.get('action'),
                               request.POST.get('remarks', ''))
    (messages.success if ok else messages.error)(request, message)
    if request.POST.get('next') == 'approvals':
        return redirect('approve_clubs')
    return redirect('event_details', event_id=event.id)


@login_required
def check_slot(request):
    """Live availability check used by the event form while the organiser types."""
    try:
        date_time = timezone.make_aware(datetime.strptime(request.GET['date_time'], '%Y-%m-%dT%H:%M'))
        duration = int(request.GET['duration'])
        location = Location.objects.get(pk=request.GET['location'])
    except (KeyError, ValueError, Location.DoesNotExist):
        return JsonResponse({'ok': None, 'errors': [], 'warnings': []})

    exclude = request.GET.get('exclude', '')
    exclude_id = int(exclude) if exclude.isdigit() else None
    errors = slot_errors(date_time, max(duration, 1), location, exclude_id=exclude_id)
    pending = find_conflicts(date_time, max(duration, 1), location, exclude_id=exclude_id, statuses=('pending',))
    warnings = [
        f"“{e.title}” ({e.association.name}) has also requested {location} at this time and is awaiting approval."
        for e in pending
    ]
    return JsonResponse({'ok': not errors, 'errors': errors, 'warnings': warnings})


# --- Participants ----------------------------------------------------------------

@login_required
@require_POST
def toggle_registration(request, event_id):
    event = get_object_or_404(Event, id=event_id, status='approved')
    profile = get_profile(request.user)
    if profile.role == FACULTY:
        messages.info(request, "Faculty don't need to register for events.")
        return redirect('event_details', event_id=event.id)

    registration = EventRegistration.objects.filter(event=event, participant=profile).first()
    if registration:
        if event.phase != 'upcoming':
            messages.error(request, "Registrations can't be changed once the event has started.")
        else:
            registration.delete()
            messages.info(request, "Your registration was cancelled.")
    elif not event.can_register:
        messages.error(request, "Registration is closed for this event.")
    else:
        EventRegistration.objects.create(event=event, participant=profile)
        messages.success(request, "You're registered! Add it to your calendar so you don't miss it.")
    return redirect('event_details', event_id=event.id)


@login_required
def event_attendees(request, event_id):
    event = _get_event(event_id)
    _, is_organiser, is_reviewer = _access(request, event)
    if not (is_organiser or is_reviewer):
        messages.error(request, "Only the organisers and faculty in-charge can see the attendee list.")
        return redirect('event_details', event_id=event.id)

    registrations = list(event.registrations.select_related('participant__id'))
    if request.method == 'POST' and is_organiser:
        attended_ids = {int(pk) for pk in request.POST.getlist('attended') if pk.isdigit()}
        for registration in registrations:
            registration.attended = registration.pk in attended_ids
        EventRegistration.objects.bulk_update(registrations, ['attended'])
        messages.success(request, f"Attendance saved: {len(attended_ids)} of {len(registrations)} present.")
        return redirect('event_attendees', event_id=event.id)

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="event-{event.id}-attendees.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Email', 'Registered at', 'Attended'])
        for r in registrations:
            writer.writerow([r.participant.display_name, r.participant.id.email,
                             timezone.localtime(r.registered_at).strftime('%Y-%m-%d %H:%M'),
                             'Yes' if r.attended else 'No'])
        return response

    return render(request, 'events/attendees.html', {
        'event': event,
        'registrations': registrations,
        'attended_count': sum(r.attended for r in registrations),
        'is_organiser': is_organiser,
    })


# --- Post-event report ---------------------------------------------------------

def _save_report(event, text, data, provider):
    event.report_content = text
    event.report_data = data
    event.report_provider = provider
    event.report_generated = True
    event.report_generated_at = timezone.now()
    pdf_bytes = build_report_pdf(event, text, data)
    if event.report_pdf:
        event.report_pdf.delete(save=False)
    filename = f"event_report_{event.id}_{timezone.localtime():%Y%m%d%H%M%S}.pdf"
    event.report_pdf.save(filename, ContentFile(pdf_bytes), save=False)
    event.save()


@login_required
def generate_event_report(request, event_id):
    event = _get_event(event_id)
    profile, is_organiser, _ = _access(request, event)
    if not is_organiser:
        messages.error(request, "Only the organising team can write the report for this event.")
        return redirect('event_details', event_id=event.id)
    if event.status != 'approved' or not event.is_completed:
        messages.error(request, "The report can be generated once the event has taken place.")
        return redirect('event_details', event_id=event.id)

    attended = event.registrations.filter(attended=True).count()
    initial = event.report_data or {
        'organizer': event.association.name,
        'attendees': attended or event.registrations.count() or None,
    }
    form = EventReportForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        text, provider, warning = generate_report(event, data)
        first_report = not event.report_generated
        _save_report(event, text, data, provider)
        log(event, 'report', profile, provider)
        if warning:
            messages.warning(request, f"AI generation wasn't available ({warning}) so a structured draft was "
                                      "built from your inputs. Review and edit it below.")
        else:
            messages.success(request, f"Draft generated with {provider}. Review it and edit anything that needs changing.")
        if first_report:
            notify(
                [event.association.faculty_incharge.id],
                f"Report submitted: {event.title}",
                f"{event.association.name} submitted the post-event report for “{event.title}”.",
                link=reverse('event_report', args=[event.id]),
                email=False,
            )
        return redirect(f"{reverse('event_report', args=[event.id])}?edit=1")

    return render(request, 'events/generate_report_form.html', {
        'form': form,
        'event': event,
        'provider': active_provider(),
        'registered': event.registrations.count(),
        'attended': attended,
    })


def event_report(request, event_id):
    event = _get_event(event_id)
    profile, is_organiser, is_reviewer = _access(request, event)
    if not event.report_generated or event.status != 'approved':
        if is_organiser and event.status == 'approved' and event.is_completed:
            return redirect('generate_event_report', event_id=event.id)
        raise Http404("No report yet")

    form = ReportEditForm(request.POST or None, initial={'report_content': event.report_content})
    if request.method == 'POST':
        if not is_organiser:
            messages.error(request, "Only the organising team can edit this report.")
            return redirect('event_report', event_id=event.id)
        if form.is_valid():
            _save_report(event, form.cleaned_data['report_content'], event.report_data, event.report_provider)
            log(event, 'report_edited', profile)
            messages.success(request, "Report saved and the PDF was rebuilt.")
            return redirect('event_report', event_id=event.id)

    return render(request, 'events/report_detail.html', {
        'event': event,
        'form': form,
        'is_organiser': is_organiser,
        'is_reviewer': is_reviewer,
        'editing': is_organiser and (request.GET.get('edit') == '1' or form.errors),
    })
