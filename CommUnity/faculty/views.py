import json
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from committees.models import Associations
from events.models import Event, EventLog, FacultyLockDate
from events.services import describe_conflict, find_conflicts, locked_date_for, review_event
from Login.models import UserProfile
from Login.notify import notify
from Login.permissions import CORE_MEMBER, FACULTY, STUDENT, MEMBER, faculty_required, get_faculty, get_profile
from members.models import CoreMember, Member

from .forms import FacultyLockDateForm

VISIBLE = Associations.VISIBLE_STATUSES


def _events_per_month(events, months=6):
    """Counts of approved events for the last `months` calendar months, oldest first."""
    today = timezone.localdate()
    keys, year, month = [], today.year, today.month
    for _ in range(months):
        keys.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    counts = {key: 0 for key in reversed(keys)}
    for event in events:
        local = timezone.localtime(event.date_time)
        if (local.year, local.month) in counts:
            counts[(local.year, local.month)] += 1
    peak = max(counts.values())
    return [
        {
            'label': date(y, m, 1).strftime('%b'),
            'full': date(y, m, 1).strftime('%B %Y'),
            'count': count,
            'pct': round(count / peak * 100) if peak else 0,
            'is_peak': peak > 0 and count == peak,
        }
        for (y, m), count in counts.items()
    ], peak


@faculty_required
def faculty_view(request):
    faculty = get_faculty(request.user)
    associations = Associations.objects.filter(faculty_incharge=faculty)
    events = Event.objects.filter(association__faculty_incharge=faculty).select_related('association', 'location')
    approved = list(events.filter(status='approved'))
    upcoming = sorted([e for e in approved if not e.is_completed], key=lambda e: e.date_time)
    completed = sorted([e for e in approved if e.is_completed], key=lambda e: e.date_time, reverse=True)
    reports_due = [e for e in completed if not e.report_generated]
    pending_events = list(events.filter(status='pending').order_by('date_time'))
    pending_associations = list(associations.filter(status__in=['pending', 'delete_pending']))
    chart, chart_peak = _events_per_month(approved)

    stats = [
        {'label': 'Awaiting your review', 'value': len(pending_events) + len(pending_associations),
         'hint': 'events and club requests', 'url': reverse('approve_clubs'), 'accent': True},
        {'label': 'Upcoming events', 'value': len(upcoming), 'hint': 'approved and scheduled',
         'url': reverse('view_calendar')},
        {'label': 'Clubs and committees', 'value': associations.filter(status__in=VISIBLE).count(),
         'hint': 'under your guidance', 'url': reverse('faculty_committee')},
        {'label': 'Reports submitted', 'value': len(completed) - len(reports_due),
         'hint': f"{len(reports_due)} still due" if reports_due else 'all caught up', 'url': reverse('faculty_reports')},
    ]
    return render(request, 'faculty/dashboard.html', {
        'faculty': faculty,
        'stats': stats,
        'pending_events': pending_events[:5],
        'pending_associations': pending_associations[:5],
        'upcoming': upcoming[:5],
        'reports_due': reports_due[:5],
        'chart': chart,
        'chart_peak': chart_peak,
        'chart_total': sum(row['count'] for row in chart),
    })


@faculty_required
def profile_view(request):
    return redirect('getprofile')


@faculty_required
def faculty_committee(request):
    faculty = get_faculty(request.user)
    associations = Associations.objects.filter(faculty_incharge=faculty).order_by('name')
    return render(request, 'faculty/associations.html', {
        'clubs': [a for a in associations if a.type == 'clubs'],
        'committees': [a for a in associations if a.type == 'committees'],
    })


def _association_members(request, pk):
    association = get_object_or_404(Associations.objects.select_related('faculty_incharge__id'), pk=pk)
    profile = get_profile(request.user)
    allowed = request.user.is_staff or (profile is not None and (
        association.faculty_incharge_id == profile.pk
        or CoreMember.objects.filter(id=profile, association=association).exists()
    ))
    if not allowed:
        messages.error(request, "You don't have access to this team's member list.")
        return redirect(association.get_absolute_url())
    return render(request, 'faculty/association_members.html', {
        'association': association,
        'core_members': CoreMember.objects.filter(association=association).select_related('id__id'),
        'members': [m for m in Member.objects.select_related('id__id') if pk in m.association_ids],
    })


def committee_member_view(request, pk):
    return _association_members(request, pk)


def club_member_view(request, pk):
    return _association_members(request, pk)


@faculty_required
def add_core_member_view(request):
    faculty = get_faculty(request.user)
    if request.method == 'POST':
        query = json.loads(request.body or '{}').get('query', '').strip()
        if len(query) < 2:
            return JsonResponse({'students': []})
        students = (
            UserProfile.objects.select_related('id')
            .filter(Q(full_name__icontains=query) | Q(id__username__icontains=query) | Q(id__email__icontains=query))
            .filter(role__in=[STUDENT, MEMBER])[:15]
        )
        return JsonResponse({'students': [
            {'id': s.id.username, 'name': s.display_name, 'email': s.id.email, 'status': s.get_role_display()}
            for s in students
        ]})

    my_associations = Associations.objects.filter(faculty_incharge=faculty).order_by('name')
    return render(request, 'faculty/add_core_member.html', {
        'associations': my_associations,
        'core_members': CoreMember.objects.filter(
            Q(association__faculty_incharge=faculty) | Q(association__isnull=True)
        ).select_related('id__id', 'association').order_by('association__name'),
    })


@faculty_required
@require_POST
def select_student(request):
    faculty = get_faculty(request.user)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid request.'}, status=400)

    student = UserProfile.objects.select_related('id').filter(id__username=data.get('student_id')).first()
    if student is None:
        return JsonResponse({'message': 'Student not found.'}, status=404)
    if student.role not in (STUDENT, MEMBER):
        return JsonResponse({'message': f"{student.display_name} is already {student.get_role_display().lower()}."}, status=400)

    association = None
    if data.get('association_id'):
        association = Associations.objects.filter(pk=data['association_id'], faculty_incharge=faculty).first()
        if association is None:
            return JsonResponse({'message': 'You can only assign students to your own clubs and committees.'}, status=403)

    student.role = CORE_MEMBER
    student.save()
    core = CoreMember.objects.get(id=student)
    if association:
        core.association = association
        core.save()
        if association.owner_id is None:
            association.owner = core
            association.save(update_fields=['owner'])

    team = f" of {association.name}" if association else ''
    notify([student], "You're now a core member",
           f"{faculty.id.display_name} made you a core member{team}. "
           + ("You can now manage your team's events." if association else
              "You can now create your club or committee on CommUnity."),
           link=reverse('dashboard'), kind='success')
    return JsonResponse({
        'message': f"{student.display_name} is now a core member{team}.",
        'student': {'id': student.id.username, 'email': student.id.email},
    })


@faculty_required
def approve_clubs(request):
    faculty = get_faculty(request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '').strip()
        tab = request.POST.get('tab', 'events')

        if action in ('approve', 'reject', 'approve_delete', 'reject_delete'):
            association = get_object_or_404(Associations, id=request.POST.get('club_id'), faculty_incharge=faculty)
            owner = association.owner or association.created_by
            recipients = [owner.id] if owner else []
            link = association.get_absolute_url()
            reason = f"\n\nRemarks: {remarks}" if remarks else ''

            if action == 'approve' and association.status == 'pending':
                association.status = 'approved'
                association.save(update_fields=['status'])
                notify(recipients, f"{association.name} is approved",
                       f"{faculty.id.display_name} approved “{association.name}”. You can now schedule events.{reason}",
                       link=link, kind='success')
                messages.success(request, f"“{association.name}” approved.")
            elif action == 'reject' and association.status == 'pending':
                association.status = 'rejected'
                association.save(update_fields=['status'])
                notify(recipients, f"{association.name} was not approved",
                       f"{faculty.id.display_name} did not approve “{association.name}”.{reason}",
                       link=link, kind='danger')
                messages.warning(request, f"“{association.name}” rejected.")
            elif action == 'approve_delete' and association.status == 'delete_pending':
                name = association.name
                team = [c.id for c in CoreMember.objects.filter(association=association).select_related('id')]
                association.delete()
                notify(team, f"{name} was deleted", f"{faculty.id.display_name} approved the deletion of “{name}”.",
                       kind='danger')
                messages.success(request, f"“{name}” deleted.")
            elif action in ('reject_delete', 'reject') and association.status == 'delete_pending':
                association.status = 'approved'
                association.save(update_fields=['status'])
                notify(recipients, f"Deletion declined: {association.name}",
                       f"{faculty.id.display_name} kept “{association.name}” active.{reason}", link=link)
                messages.info(request, f"“{association.name}” will stay active.")
            else:
                messages.error(request, "That request has already been handled.")

        elif action in ('approve_event', 'reject_event'):
            event = get_object_or_404(Event, id=request.POST.get('event_id'), association__faculty_incharge=faculty)
            ok, message = review_event(event, faculty, 'approve' if action == 'approve_event' else 'reject', remarks)
            (messages.success if ok else messages.error)(request, message)

        return redirect(f"{reverse('approve_clubs')}?tab={tab}")

    event_requests = list(
        Event.objects.filter(status='pending', association__faculty_incharge=faculty)
        .select_related('association', 'location', 'created_by__id').order_by('date_time')
    )
    for event in event_requests:
        event.conflicts = [describe_conflict(c) for c in
                           find_conflicts(event.date_time, event.duration, event.location, exclude_id=event.id)]
        event.pending_clashes = find_conflicts(event.date_time, event.duration, event.location,
                                               exclude_id=event.id, statuses=('pending',))
        event.lock = locked_date_for(event.date_time)

    pending_clubs = Associations.objects.filter(status='pending', faculty_incharge=faculty).select_related('created_by__id')
    delete_requests = Associations.objects.filter(status='delete_pending', faculty_incharge=faculty).select_related('owner__id')
    tab = request.GET.get('tab') or (
        'events' if event_requests else 'associations' if pending_clubs else 'deletions' if delete_requests else 'events'
    )
    return render(request, 'faculty/approvals.html', {
        'event_requests': event_requests,
        'pending_clubs': pending_clubs,
        'delete_requests': delete_requests,
        'history': EventLog.objects.filter(
            event__association__faculty_incharge=faculty, action__in=['approved', 'rejected', 'cancelled']
        ).select_related('event', 'actor').order_by('-created_at')[:15],
        'tab': tab,
        'faculty': faculty,
    })


@faculty_required
def manage_faculty_lock_dates(request):
    faculty = get_faculty(request.user)
    if not faculty.can_lock_dates:
        messages.error(request, "Reserving dates needs permission from the administrator.")
        return redirect('faculty')

    form = FacultyLockDateForm(request.POST or None)
    if request.method == 'POST':
        if request.POST.get('delete'):
            FacultyLockDate.objects.filter(pk=request.POST['delete']).delete()
            messages.success(request, "Date released. Events can be scheduled on it again.")
            return redirect('manage_faculty_lock_dates')
        if form.is_valid():
            lock = form.save(commit=False)
            lock.created_by = faculty
            lock.save()
            clashes = Event.objects.filter(status__in=['approved', 'pending'], date_time__date=lock.locked_date)
            messages.success(request, f"{lock.locked_date:%d %b %Y} is now reserved.")
            if clashes:
                titles = ', '.join(f"“{e.title}”" for e in clashes)
                messages.warning(request, f"Already scheduled on that day: {titles}. Review them with the organisers.")
            return redirect('manage_faculty_lock_dates')

    today = timezone.localdate()
    upcoming = list(FacultyLockDate.objects.filter(locked_date__gte=today).select_related('created_by__id'))
    for lock in upcoming:
        lock.events = Event.objects.filter(status__in=['approved', 'pending'], date_time__date=lock.locked_date)
    return render(request, 'faculty/lock_dates.html', {
        'form': form,
        'upcoming': upcoming,
        'past': FacultyLockDate.objects.filter(locked_date__lt=today).order_by('-locked_date')[:8],
    })


@faculty_required
def faculty_reports(request):
    faculty = get_faculty(request.user)
    events = [
        e for e in Event.objects.filter(association__faculty_incharge=faculty, status='approved')
        .select_related('association', 'location').order_by('-date_time')
        if e.is_completed
    ]
    return render(request, 'faculty/reports.html', {
        'submitted': [e for e in events if e.report_generated],
        'due': [e for e in events if not e.report_generated],
    })
