"""Role helpers and view decorators used across every app."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect

from .models import UserProfile

FACULTY = 'faculty'
CORE_MEMBER = 'core_member'
MEMBER = 'member'
STUDENT = 'non_participating'


def get_profile(user):
    """Return the user's profile, creating it for accounts made outside signup (e.g. createsuperuser)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.userprofile
    except UserProfile.DoesNotExist:
        return UserProfile.objects.create(id=user, full_name=user.get_full_name())


def get_faculty(user):
    from faculty.models import Faculty

    profile = get_profile(user)
    if profile is None or profile.role != FACULTY:
        return None
    return Faculty.objects.get_or_create(id=profile)[0]


def get_core_member(user):
    from members.models import CoreMember

    profile = get_profile(user)
    if profile is None or profile.role != CORE_MEMBER:
        return None
    return CoreMember.objects.select_related('association').get_or_create(id=profile)[0]


def wants_json(request):
    return (
        request.content_type == 'application/json'
        or 'application/json' in request.headers.get('Accept', '')
    )


def role_required(*roles):
    """Allow the view only for logged-in users whose profile role is in `roles`."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if wants_json(request):
                    return JsonResponse({'message': 'Please log in first.'}, status=401)
                return redirect_to_login(request.get_full_path())
            if get_profile(request.user).role not in roles:
                if wants_json(request):
                    return JsonResponse({'message': "You don't have permission to do that."}, status=403)
                messages.error(request, "You don't have permission to access that page.")
                return redirect('home')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


faculty_required = role_required(FACULTY)
core_member_required = role_required(CORE_MEMBER)
