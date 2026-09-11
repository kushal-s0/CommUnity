from django.conf import settings

from .permissions import CORE_MEMBER, FACULTY, get_profile


def community(request):
    """Navigation data every page needs: role, unread count, pending approvals."""
    context = {'COLLEGE_NAME': settings.COLLEGE_NAME}
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return context

    from committees.models import Announcement, Associations
    from events.models import Event
    from faculty.models import Faculty
    from members.models import CoreMember

    profile = get_profile(user)
    unread = profile.notifications.filter(is_read=False).count()
    if profile.followed_ids:
        unread += (
            Announcement.objects.filter(club_id__in=profile.followed_ids)
            .exclude(id__in=profile.notification_read or [])
            .count()
        )

    context.update(nav_profile=profile, nav_role=profile.role, unread_notifications=unread)

    if profile.role == FACULTY:
        context['pending_approvals'] = (
            Associations.objects.filter(faculty_incharge_id=profile.pk, status__in=['pending', 'delete_pending']).count()
            + Event.objects.filter(association__faculty_incharge_id=profile.pk, status='pending').count()
        )
        context['nav_can_lock_dates'] = Faculty.objects.filter(id=profile, can_lock_dates=True).exists()
    elif profile.role == CORE_MEMBER:
        core = CoreMember.objects.select_related('association').filter(id=profile).first()
        context['nav_association'] = core.association if core else None
    return context
