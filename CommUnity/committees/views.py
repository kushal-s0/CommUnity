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
from django.contrib import messages

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
    request.session['url'] = 'club_list'
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
    request.session['url'] = 'committees_list'

    return render(request, 'committees/committees_list.html', context)



# Club detail view
def club_detail(request, pk):
    club = get_object_or_404(Associations, pk=pk)
    url = request.session.get('url','club_list')
    print("url:",type(url),url)

    is_creator = False
    is_owner = False
    can_edit = False

    if request.user.is_authenticated and request.user.userprofile.role == 'core_member':
        core_member = CoreMember.objects.get(id=request.user.userprofile)
        is_creator = club.created_by == core_member
        is_owner = club.owner == core_member
        if core_member:
            can_edit = CoreMember.objects.filter(association=club,id=core_member.id).exists()
    core_members = CoreMember.objects.filter(association=club).exclude(id=club.owner.id)

    return render(request, 'committees/club_detail.html',context={
        'club': club,
        'url': url,
        'is_creator': is_creator,
        'is_owner': is_owner,
        'core_members': core_members,
        'can_edit': can_edit
    })


# Committee detail view
def committees_detail(request, pk):
    committee = get_object_or_404(Associations, pk=pk)
    url = request.session.get('url')
    print("url:",type(url),url)
    is_creator = False
    is_owner = False
    can_edit = False
    if request.user.is_authenticated and request.user.userprofile.role == 'core_member':
        core_member = CoreMember.objects.get(id=request.user.userprofile)
        is_creator = committee.created_by == core_member
        is_owner = committee.owner == core_member
        if core_member:
            can_edit = CoreMember.objects.filter(association=committee,id=core_member.id).exists()
    core_members = CoreMember.objects.filter(association=committee).exclude(id=committee.owner.id)

    return render(request, 'committees/committee_detail.html', context={'committee': committee, 'url': url, 'is_creator': is_creator,'is_owner': is_owner,'core_members': core_members,'can_edit': can_edit})

@login_required
def add_club_committee(request):
    faculties = Faculty.objects.all()
    current_user = request.user
    user_profile = current_user.userprofile
    core_member = CoreMember.objects.get(id=user_profile)
    if core_member.association != None:
        return HttpResponse("You are already a member of a committee")
    if request.method == "POST":
        print("POST Data:", request.POST)
        faculty_incharge_ssv_id = request.POST.get('faculty_incharge')

        if not faculty_incharge_ssv_id or faculty_incharge_ssv_id == "None":
            return HttpResponse("Select a faculty!")

        try:
            faculty_incharge = Faculty.objects.get(id__ssv_id=faculty_incharge_ssv_id)
        except Faculty.DoesNotExist:
            return HttpResponse("Faculty does not exist1")

        # Only core members can add clubs/committees
        if request.user.userprofile.role != 'core_member':
            return redirect('home')

        core_member = CoreMember.objects.get(id=request.user.userprofile)

        name = request.POST['name']
        description = request.POST['description']
        association_type = request.POST.get('type')  # Use .get() to avoid errors
        category = request.POST.get('category')
        image = request.FILES.get('image')

        club = Associations(
            name=name,
            description=description,
            type=association_type,
            faculty_incharge=faculty_incharge,
            category=category,
            created_by=core_member,
            owner=core_member,
            status='pending'
        )

        core_member.association = club
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
    core_members = CoreMember.objects.filter(association=association)

    if request.user.userprofile.role != 'core_member' or not core_members.filter(id=request.user.userprofile).exists():
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

        if association.type == 'clubs':
            return redirect('club_detail', pk=pk)
        else:
            return redirect('committees_detail', pk=pk)


    # Render correct form based on type
    template = 'committees/edit_club.html' if association.type == 'clubs' else 'committees/edit_committee.html'

    return render(request, template, {'association': association, 'faculties': faculties})


@login_required
def delete_club_committee(request, pk):
    association = get_object_or_404(Associations, pk=pk)

    # Check if current user is a core member and the creator
    if request.user.userprofile.role != 'core_member' or association.owner.id != request.user.userprofile:
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





def add_event(request):

    return render(request, 'committees/add_event.html')



@login_required
def transfer_ownership(request, pk):
    club = get_object_or_404(Associations, pk=pk)

    if request.method == "POST":
        new_owner_str = request.POST.get("new_owner")
        try:
            username, full_name, role = new_owner_str.split(", ")
            new_owner = CoreMember.objects.get(
                id__id__username=username,  # CustomUser.username
                id__full_name=full_name,  # UserProfile.full_name
                id__role=role  # UserProfile.role
            )
            print(f"✅ Found CoreMember: {new_owner}")  # Debugging
        except (ValueError, CoreMember.DoesNotExist):
            print("❌ Error: Invalid core member selection")
            return HttpResponse("Invalid core member selected", status=400)

        if new_owner == club.owner:
            return HttpResponse("You are already the owner")

        club.owner = new_owner
        club.save()
        if club.type == 'clubs':
            return redirect('club_detail', pk=pk)
        else:
            return redirect('committees_detail', pk=pk)


    core_members = CoreMember.objects.filter(association=club).exclude(id=club.owner.id)

    return render(request, 'committees/club_detail.html', {
        'club': club,
        'core_members': core_members
    })

