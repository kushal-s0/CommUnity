from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from events.models import Event
from Login.notify import notify
from Login.permissions import core_member_required, get_core_member, get_profile
from members.models import CoreMember, Member

from .forms import AssociationForm
from .models import AssociationImage, Associations

VISIBLE = Associations.VISIBLE_STATUSES


def _save_gallery(association, files):
    for image in files:
        AssociationImage.objects.create(association=association, image=image)


def _association_list(request, kind):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    associations = (
        Associations.objects.filter(type=kind, status__in=VISIBLE)
        .select_related('faculty_incharge__id')
        .annotate(upcoming_count=Count(
            'event', filter=Q(event__status='approved', event__date_time__gte=timezone.now())
        ))
        .order_by('name')
    )
    if query:
        associations = associations.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        associations = associations.filter(category=category)

    profile = get_profile(request.user)
    return render(request, 'committees/association_list.html', {
        'associations': associations,
        'kind': kind,
        'kind_label': 'Clubs' if kind == 'clubs' else 'Committees',
        'followed': profile.followed_ids if profile else [],
        'categories': [c for c, _ in Associations.CATEGORY if c != 'None'],
        'query': query,
        'category': category,
    })


def club_list(request):
    return _association_list(request, 'clubs')


def committees_list(request):
    return _association_list(request, 'committees')


def association_detail(request, pk):
    association = get_object_or_404(
        Associations.objects.select_related('faculty_incharge__id__id', 'owner__id__id'), pk=pk
    )
    profile = get_profile(request.user)
    core = get_core_member(request.user)
    is_team = core is not None and core.association_id == association.pk
    is_owner = is_team and association.owner_id == core.pk
    is_faculty = profile is not None and association.faculty_incharge_id == profile.pk
    if not association.is_visible and not (is_team or is_faculty or request.user.is_staff):
        raise Http404("Not found")

    events = Event.objects.filter(association=association, status='approved').select_related('location')
    core_members = CoreMember.objects.filter(association=association).select_related('id__id')
    members = [m for m in Member.objects.select_related('id__id') if association.pk in m.association_ids]

    return render(request, 'committees/association_detail.html', {
        'association': association,
        'is_team': is_team,
        'is_owner': is_owner,
        'is_faculty': is_faculty,
        'is_following': profile is not None and association.pk in profile.followed_ids,
        'upcoming_events': [e for e in events.order_by('date_time') if not e.is_completed],
        'past_events': [e for e in events.order_by('-date_time') if e.is_completed][:6],
        'core_members': core_members,
        'members': members,
        'announcements': association.announcement_set.order_by('-created_at')[:4],
        'transfer_candidates': core_members.exclude(pk=association.owner_id) if is_owner else [],
    })


@require_POST
def toggle_follow(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Log in to follow clubs and committees.',
                             'login_url': reverse('account_login')}, status=401)
    association = get_object_or_404(Associations, pk=pk, status__in=VISIBLE)
    profile = get_profile(request.user)
    followed = profile.followed_ids
    if association.pk in followed:
        followed.remove(association.pk)
        following = False
    else:
        followed.append(association.pk)
        following = True
    profile.preferences = followed
    profile.save(update_fields=['preferences'])
    return JsonResponse({
        'following': following,
        'message': f"You'll get updates from {association.name}." if following else f"Unfollowed {association.name}.",
    })


@core_member_required
def add_club_committee(request):
    core = get_core_member(request.user)
    if core.association:
        messages.info(request, f"You already manage {core.association.name}. A core member belongs to one club or committee.")
        return redirect(core.association.get_absolute_url())

    form = AssociationForm(request.POST or None, request.FILES or None,
                           initial={'type': request.GET.get('type', 'clubs')})
    if request.method == 'POST' and form.is_valid():
        association = form.save(commit=False)
        association.created_by = core
        association.owner = core
        association.status = 'pending'
        association.save()
        core.association = association
        core.save()
        _save_gallery(association, request.FILES.getlist('images'))
        notify(
            [association.faculty_incharge.id],
            f"New {association.get_type_display()[:-1].lower()} request: {association.name}",
            f"{core.id.display_name} created “{association.name}” and chose you as faculty in-charge. "
            "Please review and approve it.",
            link=reverse('approve_clubs'),
            kind='warning',
        )
        messages.success(request, f"“{association.name}” was sent to {association.faculty_incharge.id.display_name} for approval.")
        return redirect(association.get_absolute_url())

    return render(request, 'committees/association_form.html', {'form': form, 'mode': 'create'})


@core_member_required
def edit_club_committee(request, pk):
    association = get_object_or_404(Associations, pk=pk)
    core = get_core_member(request.user)
    if core.association_id != association.pk:
        messages.error(request, "Only this team's core members can edit it.")
        return redirect(association.get_absolute_url())

    form = AssociationForm(request.POST or None, request.FILES or None, instance=association)
    if request.method == 'POST' and form.is_valid():
        association = form.save()
        _save_gallery(association, request.FILES.getlist('images'))
        if 'faculty_incharge' in form.changed_data and association.status == 'pending':
            notify([association.faculty_incharge.id], f"New request: {association.name}",
                   f"{core.id.display_name} asked you to be faculty in-charge of “{association.name}”.",
                   link=reverse('approve_clubs'), kind='warning')
        messages.success(request, "Changes saved.")
        return redirect(association.get_absolute_url())

    return render(request, 'committees/association_form.html', {
        'form': form, 'mode': 'edit', 'association': association,
        'gallery': association.images.order_by('-uploaded_at'),
    })


@core_member_required
def delete_club_committee(request, pk):
    association = get_object_or_404(Associations, pk=pk)
    core = get_core_member(request.user)
    if association.owner_id != core.pk:
        messages.error(request, "Only the owner can request deletion.")
        return redirect(association.get_absolute_url())

    if request.method == 'POST':
        association.status = 'delete_pending'
        association.save(update_fields=['status'])
        notify(
            [association.faculty_incharge.id],
            f"Deletion requested: {association.name}",
            f"{core.id.display_name} asked to delete “{association.name}”. Please review the request.",
            link=f"{reverse('approve_clubs')}?tab=deletions",
            kind='danger',
        )
        messages.success(request, "Deletion request sent to the faculty in-charge.")
        return redirect(association.get_absolute_url())

    return render(request, 'committees/confirm_delete.html', {'association': association})


@core_member_required
@require_POST
def transfer_ownership(request, pk):
    association = get_object_or_404(Associations, pk=pk)
    core = get_core_member(request.user)
    if association.owner_id != core.pk:
        messages.error(request, "Only the current owner can transfer ownership.")
        return redirect(association.get_absolute_url())

    new_owner = (
        CoreMember.objects.filter(pk=request.POST.get('new_owner'), association=association)
        .exclude(pk=core.pk).select_related('id').first()
    )
    if new_owner is None:
        messages.error(request, "Pick a core member of this team.")
        return redirect(association.get_absolute_url())

    association.owner = new_owner
    association.save(update_fields=['owner'])
    notify([new_owner.id], f"You now own {association.name}",
           f"{core.id.display_name} transferred ownership of “{association.name}” to you.",
           link=association.get_absolute_url(), kind='success')
    messages.success(request, f"Ownership transferred to {new_owner.id.display_name}.")
    return redirect(association.get_absolute_url())


@core_member_required
@require_POST
def delete_association_image(request, pk, image_id):
    image = get_object_or_404(AssociationImage, pk=image_id, association_id=pk)
    core = get_core_member(request.user)
    if core.association_id != pk:
        messages.error(request, "Only this team's core members can manage its gallery.")
    else:
        image.image.delete(save=False)
        image.delete()
        messages.success(request, "Photo removed from the gallery.")
    return redirect('edit_club_committee', pk=pk)
