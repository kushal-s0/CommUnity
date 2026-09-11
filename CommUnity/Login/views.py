from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from committees.models import Announcement, AssociationImage, Associations
from events.models import Event, EventRegistration
from members.models import CoreMember, Member

from .forms import ProfileForm
from .models import Notification, UserProfile
from .permissions import CORE_MEMBER, FACULTY, get_core_member, get_faculty, get_profile

VISIBLE = Associations.VISIBLE_STATUSES

CATEGORY_INFO = [
    ('Technical', 'Hackathons, coding contests and hands-on workshops.', 'fa-microchip'),
    ('Cultural', 'Music, dance, drama, art and the festivals in between.', 'fa-masks-theater'),
    ('Sports', 'Tournaments, fitness drives and inter-college meets.', 'fa-futbol'),
    ('Social', 'Outreach, volunteering and community service.', 'fa-hand-holding-heart'),
    ('Academic', 'Seminars, study circles and professional chapters.', 'fa-book-open'),
    ('Other', 'Everything else that makes campus life richer.', 'fa-shapes'),
]


def _upcoming(queryset):
    """Approved events that haven't finished yet, soonest first."""
    recent = queryset.filter(status='approved', date_time__gte=timezone.now() - timedelta(days=3))
    return [e for e in recent.order_by('date_time') if not e.is_completed]


def home_view(request):
    profile = get_profile(request.user)
    if profile and profile.role == FACULTY:
        return redirect('faculty')

    associations = list(Associations.objects.filter(status__in=VISIBLE).order_by('name'))
    upcoming = _upcoming(Event.objects.select_related('association', 'location'))
    return render(request, 'account/home.html', {
        'featured_images': AssociationImage.objects.filter(association__status__in=VISIBLE)
                           .select_related('association').order_by('-uploaded_at')[:9],
        'announcements': Announcement.objects.select_related('club').order_by('-created_at')[:5],
        'upcoming_events': upcoming[:6],
        'categories': [
            {'name': name, 'blurb': blurb, 'icon': icon,
             'associations': [a for a in associations if a.category == name]}
            for name, blurb, icon in CATEGORY_INFO
        ],
        'stats': {
            'clubs': sum(a.type == 'clubs' for a in associations),
            'committees': sum(a.type == 'committees' for a in associations),
            'events': len(upcoming),
            'students': UserProfile.objects.exclude(role=FACULTY).count(),
        },
    })


@login_required
def dashboard(request):
    profile = get_profile(request.user)
    if profile.role == FACULTY:
        return redirect('faculty')

    context = {'profile': profile}
    if profile.role == CORE_MEMBER:
        core = get_core_member(request.user)
        association = core.association
        context.update(core=core, association=association)
        if association:
            events = list(
                Event.objects.filter(association=association).select_related('location')
                .annotate(reg_count=Count('registrations')).order_by('-date_time')
            )
            pending = [e for e in events if e.status == 'pending']
            upcoming = [e for e in events if e.status == 'approved' and not e.is_completed]
            reports_due = [e for e in events if e.status == 'approved' and e.is_completed and not e.report_generated]
            team_size = (CoreMember.objects.filter(association=association).count()
                         + sum(association.pk in m.association_ids for m in Member.objects.all()))
            context.update(
                team_events=events[:10],
                reports_due=reports_due,
                stats=[
                    {'label': 'Awaiting approval', 'value': len(pending), 'hint': 'with your faculty in-charge'},
                    {'label': 'Upcoming events', 'value': len(upcoming), 'hint': 'approved and scheduled'},
                    {'label': 'Reports due', 'value': len(reports_due), 'hint': 'for completed events',
                     'accent': bool(reports_due)},
                    {'label': 'Team size', 'value': team_size, 'hint': 'core and general members'},
                ],
            )

    registrations = EventRegistration.objects.filter(participant=profile).select_related(
        'event__association', 'event__location')
    my_events = sorted(
        [r.event for r in registrations if r.event.status == 'approved' and not r.event.is_completed],
        key=lambda e: e.date_time,
    )
    registered_ids = {r.event_id for r in registrations}
    followed = Associations.objects.filter(pk__in=profile.followed_ids, status__in=VISIBLE)
    suggested = [e for e in _upcoming(Event.objects.filter(association__in=followed).select_related(
        'association', 'location')) if e.id not in registered_ids][:4]

    if profile.role != CORE_MEMBER:
        context['stats'] = [
            {'label': 'Registered events', 'value': len(my_events), 'hint': 'coming up'},
            {'label': 'Following', 'value': followed.count(), 'hint': 'clubs and committees'},
            {'label': 'Events attended', 'value': registrations.filter(attended=True).count(), 'hint': 'marked by organisers'},
        ]
    member = Member.objects.filter(id=profile).first()
    context.update(
        my_events=my_events[:5],
        suggested=suggested,
        followed=followed,
        member_associations=Associations.objects.filter(pk__in=member.association_ids) if member else [],
        notifications=profile.notifications.all()[:5],
    )
    return render(request, 'account/dashboard.html', context)


@login_required
def profile_view(request):
    profile = get_profile(request.user)
    faculty = get_faculty(request.user)
    member = Member.objects.filter(id=profile).first()
    return render(request, 'account/profile.html', {
        'profile': profile,
        'faculty': faculty,
        'core': get_core_member(request.user),
        'member': member,
        'member_associations': Associations.objects.filter(pk__in=member.association_ids) if member else [],
        'in_charge': Associations.objects.filter(faculty_incharge=faculty).order_by('name') if faculty else [],
        'followed': Associations.objects.filter(pk__in=profile.followed_ids, status__in=VISIBLE),
        'registrations': EventRegistration.objects.filter(participant=profile)
                         .select_related('event__association').order_by('-event__date_time')[:6],
    })


@login_required
def edit_profile(request):
    profile = get_profile(request.user)
    faculty = get_faculty(request.user)
    core = get_core_member(request.user)
    member = Member.objects.filter(id=profile).first()
    team_record = core or member

    initial = {'full_name': profile.full_name}
    if faculty:
        initial.update(department=faculty.department, designation=faculty.designation)
    if team_record:
        initial['position'] = team_record.position

    form = ProfileForm(request.POST or None, request.FILES or None, initial=initial, role=profile.role)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        profile.full_name = data['full_name']
        if data.get('profile_picture'):
            profile.profile_picture = data['profile_picture']
        profile.save()
        if faculty:
            faculty.department = data.get('department', '')
            faculty.designation = data.get('designation', '')
            faculty.save()
        if team_record and 'position' in data:
            team_record.position = data['position']
            team_record.save()
        messages.success(request, "Profile updated.")
        return redirect('getprofile')

    return render(request, 'account/edit_profile.html', {'form': form, 'profile': profile})


@login_required
def notification_view(request):
    profile = get_profile(request.user)
    read_ids = set(profile.notification_read or [])
    announcements = list(
        Announcement.objects.filter(club_id__in=profile.followed_ids)
        .select_related('club').order_by('-created_at')[:30]
    )
    for announcement in announcements:
        announcement.is_unread = announcement.id not in read_ids
    return render(request, 'account/notification.html', {
        'personal': profile.notifications.all()[:50],
        'announcements': announcements,
        'tab': request.GET.get('tab', 'updates'),
    })


@login_required
def open_notification(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=get_profile(request.user))
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    if notification.link and url_has_allowed_host_and_scheme(notification.link, allowed_hosts={request.get_host()}):
        return redirect(notification.link)
    return redirect('notification_view')


@login_required
@require_POST
def mark_all_read(request):
    profile = get_profile(request.user)
    profile.notifications.filter(is_read=False).update(is_read=True)
    followed_announcements = Announcement.objects.filter(club_id__in=profile.followed_ids).values_list('id', flat=True)
    profile.notification_read = sorted(set(profile.notification_read or []) | set(followed_announcements))
    profile.save(update_fields=['notification_read'])
    messages.success(request, "All caught up!")
    return redirect('notification_view')


@login_required
@require_POST
def mark_as_read(request, announcement_id):
    profile = get_profile(request.user)
    read = profile.notification_read or []
    if announcement_id not in read:
        profile.notification_read = read + [announcement_id]
        profile.save(update_fields=['notification_read'])
    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('notification_view')
