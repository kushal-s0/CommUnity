from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Associations, Faculty, AssociationImage, CoreMember
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.mail import send_mail
from django.conf import settings

from django.contrib.auth.models import User
from Login.models import UserProfile
from members.models import CoreMember, Member

from .models import Announcement
from .forms import AnnouncementForm 

from django.contrib import messages



from Login.models import UserProfile
# List all clubs
def club_list(request):
    user = request.user
    
    
    if request.method == "POST":
        print("POST request received")
        if not request.user.is_authenticated:  
            print("User not logged in")
            return JsonResponse({'error': 'User not authenticated'}, status=401)  # Return JSON, not HTML
        
        
        data = json.loads(request.body)
        club_id = int(data.get("club_id"))
        selected = data.get("selected")
        print("Received data:", club_id)

        user_profile = UserProfile.objects.get(id=user)
        preferences = UserProfile.objects.get(id=user).preferences
        

        if selected:
            if club_id not in preferences:
                preferences.append(club_id)  # Add to preferences
        else:
            if club_id in preferences:
                preferences.remove(club_id)  # Remove from preferences
        
        user_profile.preferences = preferences
        user_profile.save()
        
        print("Saved Preferences:", preferences)

        return JsonResponse({"message": "Preferences updated", "preferences": preferences})

    clubs = Associations.objects.filter(type='clubs',status__in=["approved", "delete_pending"])   

    preferences = []
    if request.user.is_authenticated:
        preferences = UserProfile.objects.get(id=user).preferences

    print("Preferences:", preferences)
    context = {
        'clubs': clubs,
        'preferences': preferences
    }
    return render(request, 'committees/clubs_list.html', context)
    

def committees_list(request):
    user = request.user
    
    
    if request.method == "POST":
        if not request.user.is_authenticated:  
            print("User not logged in")
            return JsonResponse({'error': 'User not authenticated'}, status=401)  # Return JSON, not HTML
        
        
        data = json.loads(request.body)
        committee_id = int(data.get("committee_id"))
        selected = data.get("selected")
        

        user_profile = UserProfile.objects.get(id=user)
        preferences = UserProfile.objects.get(id=user).preferences
        

        if selected:
            if committee_id not in preferences:
                preferences.append(committee_id)  # Add to preferences
        else:
            if committee_id in preferences:
                preferences.remove(committee_id)  # Remove from preferences
        
        user_profile.preferences = preferences
        user_profile.save()
        print("Saved Preferences:", preferences)

        return JsonResponse({"message": "Preferences updated", "preferences": preferences})

    committees = Associations.objects.filter(type='committees',status__in=["approved", "delete_pending"])  

    preferences = []
    if request.user.is_authenticated:
        preferences = UserProfile.objects.get(id=user).preferences
    context = {
        'committees': committees,
        'preferences': preferences
    }
    return render(request, 'committees/committees_list.html', context)



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
    current_user = request.user
    user_profile = current_user.userprofile
    core_member = CoreMember.objects.get(id=user_profile)
    if core_member.assosiation != None:
        return redirect('home')
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
            created_by=core_member,
            status='pending'
        )

        core_member.assosiation = club
        if image:
            club.image = image

        club.save()
        core_member.save()

        images = request.FILES.getlist('images')
        for image in images:
            AssociationImage.objects.create(association=club, image=image)

        send_mail(
            subject=f"Approval Required for {name}",
            message=f"Dear {faculty_incharge.id.full_name},\n\n"
                    f"A new {association_type} named '{name}' has been created by {core_member.id.full_name}. "
                    f"Please review the details of {name} and approve it if everything is in order.\n\n",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[faculty_incharge.id.id.email],
            fail_silently=False,
        )
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
        association.status = "delete_pending"
        association.save()

        send_mail(
            subject=f"Deletion Request for {association.name}",
            message=f"Dear {association.faculty_incharge.id.full_name},\n\n"
                    f"The {association.type} '{association.name}' has been requested for deletion by {association.created_by.id.full_name}. "
                    f"Please review the request and approve it.\n\n",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[association.faculty_incharge.id.id.email],
            fail_silently=False,
        )
        return redirect('home')

    return render(request, 'committees/confirm_delete.html', {'association': association})

def add_announcement(request):


    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            print(data)
            user = request.user
            user = UserProfile.objects.get(id=user)

            core_member = CoreMember.objects.get(id=user)
            print("Core member :",core_member)
            club=core_member.club
            print("Club :",club)
            # announcement = Announcement.objects.create(
            #     title=data['title'],
            #     message=data['message'],
            #     created_by=core_member,
            #     club=core_member.club
            # )
            # print(announcement)
            # announcement.save()
            # form.save()
            return redirect('add_announcement')  # Redirect after successful submission
    else:
        form = AnnouncementForm()

    return render(request, 'committees/add_announcement.html', {'form': form})



def add_event(request):

    return render(request, 'committees/add_event.html')