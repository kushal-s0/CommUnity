from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, HttpResponse
from .models import Associations
from django.contrib.auth.decorators import login_required
from .models import Faculty

from django.shortcuts import render,get_object_or_404
from .models import Associations

# List all clubs
def club_list(request):
    clubs = Associations.objects.filter(type='clubs')  # Only clubs
    return render(request, 'committees/clubs_list.html', {'clubs': clubs})


def committees_list(request):
    committees = Associations.objects.filter(type='committees')
    return render(request, 'committees/committees_list.html', {'committees': committees})

def committees_detail(request, pk):
    committee = get_object_or_404(Associations, pk=pk)
    return render(request, 'committees/committee_detail.html', {'committee': committee})

def club_detail(request, pk):
    club = get_object_or_404(Associations, pk=pk)
    return render(request, 'committees/club_detail.html', {'club': club})

@login_required
def add_club_committee(request):
    faculties = Faculty.objects.all()

    if request.method == "POST":
        print("POST Data:", request.POST)
        faculty_incharge_ssv_id = request.POST.get('faculty_incharge')

        # Check if faculty_incharge_ssv_id is valid
        if not faculty_incharge_ssv_id or faculty_incharge_ssv_id == "None":
            return HttpResponse("Please select a valid faculty member")

        try:
            # Fetch Faculty by UserProfile's ssv_id
            faculty_incharge = Faculty.objects.get(id__ssv_id=faculty_incharge_ssv_id)
            print("Faculty In-Charge:", faculty_incharge.id.full_name)
        except Faculty.DoesNotExist:
            return HttpResponse("Faculty not found")

        # Only core members can add clubs/committees
        if not request.user.userprofile.role == 'core_member':
            return redirect('home')

        # Create and save the club/committee
        name = request.POST['name']
        description = request.POST['description']
        type = request.POST['type']
        image = request.FILES.get('image')

        club = Associations(
            name=name,
            description=description,
            type=type,
            faculty_incharge=faculty_incharge
        )

        if image:
            club.image = image

        club.save()
        return redirect('home')

    faculty_members = Faculty.objects.all()
    return render(request, 'committees/add_club.html', {'faculty_members': faculty_members})
