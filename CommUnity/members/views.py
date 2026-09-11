import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from committees.models import Announcement, Associations
from events.models import Event
from Login.models import UserProfile
from Login.notify import notify
from Login.permissions import CORE_MEMBER, FACULTY, MEMBER, STUDENT, core_member_required, get_core_member, get_profile

from .forms import AnnouncementForm
from .models import CoreMember, Member


def _team_association(request):
    """The association managed by the current core member, or None with an error message."""
    association = get_core_member(request.user).association
    if association is None:
        messages.error(request, "You aren't part of a club or committee yet.")
    return association


@core_member_required
def add_announcement(request):
    association = _team_association(request)
    if association is None:
        return redirect('dashboard')

    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        announcement = form.save(commit=False)
        announcement.club = association
        announcement.created_by = get_profile(request.user)
        announcement.save()
        messages.success(request, "Announcement posted. Followers will see it in their notifications.")
        return redirect('announcement_details', announcement_id=announcement.id)

    return render(request, 'members/announcement_form.html', {
        'form': form,
        'association': association,
        'recent': association.announcement_set.order_by('-created_at')[:5],
    })


def announcement_details(request, announcement_id):
    announcement = get_object_or_404(Announcement.objects.select_related('club', 'created_by'), id=announcement_id)
    profile = get_profile(request.user)
    if profile and announcement.id not in (profile.notification_read or []):
        profile.notification_read = (profile.notification_read or []) + [announcement.id]
        profile.save(update_fields=['notification_read'])
    core = get_core_member(request.user)
    return render(request, 'members/announcement_details.html', {
        'announcement': announcement,
        'can_delete': core is not None and core.association_id == announcement.club_id,
        'more': Announcement.objects.filter(club=announcement.club).exclude(id=announcement.id).order_by('-created_at')[:4],
    })


@core_member_required
@require_POST
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if get_core_member(request.user).association_id != announcement.club_id:
        messages.error(request, "You can only remove your own team's announcements.")
        return redirect('announcement_details', announcement_id=announcement.id)
    announcement.delete()
    messages.success(request, "Announcement removed.")
    return redirect('notice_board')


def notice_board(request):
    club = request.GET.get('club', '')
    announcements = Announcement.objects.select_related('club', 'created_by').order_by('-created_at')
    if club.isdigit():
        announcements = announcements.filter(club_id=club)
    upcoming = [
        e for e in Event.objects.filter(status='approved', date_time__gte=timezone.now())
        .select_related('association', 'location')[:6]
    ]
    return render(request, 'members/notice_board.html', {
        'page': Paginator(announcements, 10).get_page(request.GET.get('page')),
        'upcoming': upcoming,
        'associations': Associations.objects.filter(status__in=Associations.VISIBLE_STATUSES).order_by('name'),
        'club': club,
    })


# --- Team management -------------------------------------------------------------

@core_member_required
def add_member(request):
    association = _team_association(request)
    if association is None:
        if request.method == 'POST':
            return JsonResponse({'students': [], 'message': 'No association'}, status=400)
        return redirect('dashboard')

    if request.method == 'POST':
        query = json.loads(request.body or '{}').get('query', '').strip()
        if len(query) < 2:
            return JsonResponse({'students': []})
        profiles = (
            UserProfile.objects.select_related('id')
            .filter(Q(full_name__icontains=query) | Q(id__username__icontains=query) | Q(id__email__icontains=query))
            .exclude(role=FACULTY)[:15]
        )
        member_ids = {m.pk for m in Member.objects.all() if association.pk in m.association_ids}
        core_by_profile = dict(CoreMember.objects.filter(id__in=profiles).values_list('id', 'association__name'))
        results = []
        for p in profiles:
            if p.pk in member_ids or p.role == CORE_MEMBER and core_by_profile.get(p.pk) == association.name:
                status = 'In your team'
            elif p.role == CORE_MEMBER:
                status = f"Core member of {core_by_profile.get(p.pk) or 'no team yet'}"
            else:
                status = p.get_role_display()
            results.append({
                'id': p.id.username,
                'name': p.display_name,
                'email': p.id.email,
                'status': status,
                'selectable': status != 'In your team' and p.role != CORE_MEMBER,
            })
        return JsonResponse({'students': results})

    core_members = CoreMember.objects.filter(association=association).select_related('id__id')
    members = [m for m in Member.objects.select_related('id__id') if association.pk in m.association_ids]
    return render(request, 'members/manage_members.html', {
        'association': association,
        'core_members': core_members,
        'members': members,
        'is_owner': association.owner_id == get_core_member(request.user).pk,
    })


@core_member_required
@require_POST
def select_member(request):
    core = get_core_member(request.user)
    association = core.association
    if association is None:
        return JsonResponse({'message': "You aren't part of a club or committee yet."}, status=400)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid request.'}, status=400)
    role = data.get('role')
    student = UserProfile.objects.select_related('id').filter(id__username=data.get('student_id')).first()
    if student is None:
        return JsonResponse({'message': 'Student not found.'}, status=404)
    if student.role == FACULTY:
        return JsonResponse({'message': 'Faculty members cannot join as students.'}, status=400)
    if student.role == CORE_MEMBER:
        return JsonResponse({'message': f"{student.display_name} is already a core member."}, status=400)

    if role == MEMBER:
        if student.role != MEMBER:
            student.role = MEMBER
            student.save()
        member = Member.objects.get(id=student)
        ids = member.association_ids
        if association.pk in ids:
            return JsonResponse({'message': f"{student.display_name} is already in {association.name}."}, status=400)
        member.association = ids + [association.pk]
        member.save()
    elif role == CORE_MEMBER:
        if association.owner_id != core.pk:
            return JsonResponse({'message': 'Only the owner can add core members.'}, status=403)
        student.role = CORE_MEMBER
        student.save()
        new_core = CoreMember.objects.get(id=student)
        new_core.association = association
        new_core.save()
    else:
        return JsonResponse({'message': 'Choose a role.'}, status=400)

    role_label = 'core member' if role == CORE_MEMBER else 'member'
    notify([student], f"Welcome to {association.name}",
           f"{core.id.display_name} added you to {association.name} as a {role_label}.",
           link=association.get_absolute_url(), kind='success')
    return JsonResponse({
        'message': f"{student.display_name} added to {association.name} as a {role_label}.",
        'student': {'id': student.id.username, 'email': student.id.email, 'role': role},
    })


@core_member_required
@require_POST
def remove_member(request, profile_id):
    core = get_core_member(request.user)
    association = core.association
    target = get_object_or_404(UserProfile, pk=profile_id)
    if association is None:
        return redirect('dashboard')

    if target.role == MEMBER:
        member = Member.objects.get(id=target)
        remaining = [pk for pk in member.association_ids if pk != association.pk]
        if remaining:
            member.association = remaining
            member.save()
        else:
            target.role = STUDENT
            target.save()
        messages.success(request, f"{target.display_name} was removed from {association.name}.")
    elif target.role == CORE_MEMBER and CoreMember.objects.filter(id=target, association=association).exists():
        if association.owner_id != core.pk:
            messages.error(request, "Only the owner can remove core members.")
        elif target.pk == core.pk:
            messages.error(request, "Transfer ownership before leaving the team.")
        else:
            target.role = STUDENT
            target.save()
            messages.success(request, f"{target.display_name} is no longer a core member of {association.name}.")
    else:
        messages.error(request, "That person isn't part of your team.")
    return redirect('add_member')
