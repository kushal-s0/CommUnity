from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

from Login.models import UserProfile
from faculty.models import Faculty
from members.models import CoreMember, Member
from committees.models import Associations
# Create your views here.



# def home_view(request):
#     return render(request, 'account/home.html')

def home_view(request):
    #check if user is logged in
    if request.user.is_authenticated:
        user = request.user

        
        #print (user)
        role = UserProfile.objects.get(id=user).role
        #print(role)

        #check if user is faculty
        if role == 'faculty':
            return redirect('faculty')

        else:
            #check if user is core member
            if role == 'core_member':
                user = UserProfile.objects.get(id=user)
                core_member = CoreMember.objects.get(id=user)
                print(core_member)
            return render(request, 'account/home.html')
    else:
        return render(request, 'account/home.html')

def edit_profile(request):
    user = request.user
    user_profile = UserProfile.objects.get(id=user)

    # Initialize variables to avoid UnboundLocalError
    faculty = None
    core_member = None
    member = None

    if user_profile.role == 'faculty':
        faculty = Faculty.objects.filter(id=user_profile).first()
    elif user_profile.role == 'core_member':
        core_member = CoreMember.objects.filter(id=user_profile).first()
    elif user_profile.role == 'member':
        member = Member.objects.filter(id=user_profile).first()

    context = {
        'user': user,
        'user_profile': user_profile,
        'faculty': faculty,
        'core_member': core_member,
        'member': member
    }

    if request.method == 'POST':
        user_profile.full_name = request.POST.get('full_name')
        user_profile.save()

        if user_profile.role == 'faculty':
            faculty.department = request.POST.get('department')
            faculty.designation = request.POST.get('designation')
            faculty.save()
        elif user_profile.role == 'core_member':
            core_member.club = request.POST.get('club')
            core_member.position = request.POST.get('position')
            core_member.save()
        elif user_profile.role == 'member':
            member.club = request.POST.get('club')
            member.position = request.POST.get('position')
            member.save()

        return redirect('home')
    
    return render(request, 'account/edit_profile.html', context)

