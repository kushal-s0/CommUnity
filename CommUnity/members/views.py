from django.shortcuts import render
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.models import User
from Login.models import UserProfile

from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Q
from django.db import transaction
from django.contrib.auth import get_user_model

from django.shortcuts import render,get_object_or_404,redirect
from faculty.models import Faculty
from committees.models import Associations
from Login.models import UserProfile
from committees.models import Associations
from members.models import CoreMember, Member
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from django.db.models import Q

from django.contrib.auth import get_user_model

User = get_user_model()
from committees.models import Announcement

# Create your views here.


def add_announcement(request):
    user = request.user
    user_profile = UserProfile.objects.get(id=user.id)  # Ensure correct user lookup
    role = user_profile.role
    associations = []  # Initialize as an empty list

    if role == 'core_member':
        core_member = CoreMember.objects.get(id=user_profile)
        associations = [core_member.association] if core_member.association else []

    elif role == 'member':
        member = Member.objects.get(id=user_profile)
        member_association_ids = member.association.values_list('id', flat=True)  # Get list of IDs
        associations = Associations.objects.filter(id__in=member_association_ids)  # Get matching Associations

    if request.method == "POST":
        title = request.POST.get('title')
        message = request.POST.get('message')
        club_id = request.POST.get('club')
        created_by_id = request.POST.get('created_by')

        if title and message and club_id and created_by_id:
            print(title, message, club_id, created_by_id)
            # Announcement.objects.create(
            #     title=title,
            #     message=message,
            #     club_id=club_id,
            #     created_by_id=created_by_id
            # )
            return redirect('home')

    context = {
        'clubs': associations,  # Ensure iterable
        'user': user_profile
    }
    print(context['clubs'])
    return render(request, 'add_announcement.html', context)

@csrf_exempt  # Use this only if CSRF protection is disabled; otherwise, use CSRF token
def search_members(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '').lower()

        students = UserProfile.objects.filter(
            (Q(name__icontains=query) | Q(email__icontains=query)) & 
            (Q(role='non_participant') | Q(role='member'))
        )
        print(students.query) 
        student_list = [{'name': student.name, 'email': student.email} for student in students]

        return JsonResponse({'students': student_list})

    return JsonResponse({'error': 'Invalid request'}, status=400)
def add_member(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '').lower()

        if query:
            # Filter users based on username OR email
            users = get_user_model().objects.filter(Q(username__icontains=query) | Q(email__icontains=query))

            # Get matching UserProfile records for these users
            students = UserProfile.objects.filter(
                Q(id__in=users.values_list('id', flat=True)) &
                (Q(role='non_participating') | Q(role='member'))
            )

            # Serialize data
            student_list = [{'id': student.id.username, 'name': student.full_name, 'email': student.id.email} for student in students]

            return JsonResponse({'students': student_list})
    
    return render(request, 'add_member.html')

def select_member(request):
    print("Select Member")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            role = data.get('role')  # New role parameter

            if not student_id or not role:
                return JsonResponse({'message': 'Student ID or role not provided'}, status=400)

            student = get_object_or_404(get_user_model(), username=student_id)
            student_user = get_object_or_404(UserProfile, id=student)
            print("Student User :",student_user)

            if role == 'member':
                student_user.role = 'member'
            elif role == 'core_member':
                student_user.role = 'core_member'
            
            print("Student User :",student_user)
            student_user.save()

            current_user = UserProfile.objects.get(id=request.user)
            print("Current User :",current_user)
            core = CoreMember.objects.get(id=current_user)
            print("Core :",core)
            club = Associations.objects.filter(owner=core).first()
            if not club:
                return JsonResponse({'message': 'No association found for this Core Member'}, status=400)
            
            print("Club :",club)

            if role == 'member':
                print("Member")
                member = Member.objects.get(id=student_user)
                print("Member :",member)
                member.association.append(club.id)
                member.save()

            elif role == 'core_member':
                print("Assigning Core Member Role")
                core_member = get_object_or_404(CoreMember, id=student_user)
                
                # Ensure association updates correctly
                with transaction.atomic():
                    core_member.association = club
                    core_member.save()
                print("Core Member Association Updated:", core_member.association)
                core_member.refresh_from_db()
                print("After updating Core Member :",core_member.association)

            return JsonResponse({
                'message': f'Student {student.username} selected as {role} successfully!',
                'student': {'id': student.username, 'email': student.email, 'role': role}
            })

        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)