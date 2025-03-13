from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Associations, Faculty, AssociationImage, CoreMember

# List all clubs
def club_list(request):
    clubs = Associations.objects.filter(type='clubs')  # Only clubs
    return render(request, 'committees/clubs_list.html', {'clubs': clubs})


def committees_list(request):
    committees = Associations.objects.filter(type='committees')
    request.session['url'] = 'committees_list'
    return render(request, 'committees/committees_list.html', {'committees': committees})

# Club detail view
def club_detail(request, pk):
    club = get_object_or_404(Associations, pk=pk)

    is_creator = False
    if request.user.is_authenticated and request.user.userprofile.role == 'core_member':
        core_member = CoreMember.objects.get(id=request.user.userprofile)
        is_creator = club.created_by == core_member

    return render(request, 'committees/club_detail.html', {
        'club': club,
        'is_creator': is_creator
    })


# Committee detail view
def committees_detail(request, pk):
    committee = get_object_or_404(Associations, pk=pk)
    url = request.session.get('url')
    print(type(url),url)
    is_creator = False
    if request.user.is_authenticated and request.user.userprofile.role == 'core_member':
        core_member = CoreMember.objects.get(id=request.user.userprofile)
        is_creator = committee.created_by == core_member

    return render(request, 'committees/committee_detail.html', context={'committee': committee, 'url': url, 'is_creator': is_creator})


@login_required
def add_club_committee(request):
    faculties = Faculty.objects.all()

    if request.method == "POST":
        print("POST Data:", request.POST)
        faculty_incharge_ssv_id = request.POST.get('faculty_incharge')

        if not faculty_incharge_ssv_id or faculty_incharge_ssv_id == "None":
            return HttpResponse("Please select a valid faculty member")

        try:
            faculty_incharge = Faculty.objects.get(id__ssv_id=faculty_incharge_ssv_id)
        except Faculty.DoesNotExist:
            return HttpResponse("Faculty not found")

        # Only core members can add clubs/committees
        if request.user.userprofile.role != 'core_member':
            return redirect('home')

        core_member = CoreMember.objects.get(id=request.user.userprofile)

        name = request.POST['name']
        description = request.POST['description']
        association_type = request.POST.get('type')  # Use .get() to avoid errors
        image = request.FILES.get('image')

        club = Associations(
            name=name,
            description=description,
            type=association_type,
            faculty_incharge=faculty_incharge,
            created_by=core_member
        )

        if image:
            club.image = image

        club.save()

        images = request.FILES.getlist('images')
        for image in images:
            AssociationImage.objects.create(association=club, image=image)

        return redirect('home')

    return render(request, 'committees/add_club.html', {'faculties': faculties})


@login_required
def edit_club_committee(request, pk):
    association = get_object_or_404(Associations, pk=pk)

    # Check if current user is a core member and the creator
    if request.user.userprofile.role != 'core_member' or association.created_by.id != request.user.userprofile:
        return HttpResponse("You do not have permission to edit this club/committee")

    faculties = Faculty.objects.all()

    if request.method == "POST":
        association.name = request.POST.get('name', association.name)
        association.description = request.POST.get('description', association.description)

        # Handle 'type' safely to avoid MultiValueDictKeyError
        association_type = request.POST.get('type', association.type)
        if association_type:
            association.type = association_type

        faculty_incharge_ssv_id = request.POST.get('faculty_incharge')
        if faculty_incharge_ssv_id:
            faculty_incharge = Faculty.objects.get(id__ssv_id=faculty_incharge_ssv_id)
            association.faculty_incharge = faculty_incharge

        # Handle main image
        image = request.FILES.get('image')
        if image:
            association.image = image

        association.save()

        # Handle additional images
        images = request.FILES.getlist('images')
        for image in images:
            AssociationImage.objects.create(association=association, image=image)

        return redirect('club_detail', pk=pk)

    # Render correct form based on type
    template = 'committees/edit_club.html' if association.type == 'clubs' else 'committees/edit_committee.html'

    return render(request, template, {'association': association, 'faculties': faculties})


@login_required
def delete_club_committee(request, pk):
    association = get_object_or_404(Associations, pk=pk)

    # Check if current user is a core member and the creator
    if request.user.userprofile.role != 'core_member' or association.created_by.id != request.user.userprofile:
        return HttpResponse("You do not have permission to delete this club/committee")

    if request.method == "POST":
        association.delete()
        return redirect('home')

    return render(request, 'committees/confirm_delete.html', {'association': association})

