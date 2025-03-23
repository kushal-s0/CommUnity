from django.shortcuts import render
from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.models import User
from Login.models import UserProfile

from django.contrib.auth.decorators import login_required

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Q

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
# Create your views here.

def members_announcement(request):
    return render(request,'add_announcement.html')
@csrf_exempt  # Use this only if CSRF protection is disabled; otherwise, use CSRF token
def search_members(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '').lower()

        students = UserProfile.objects.filter(name__icontains=query) | UserProfile.objects.filter(email__icontains=query)
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
            students = UserProfile.objects.filter(id__in=users.values_list('id', flat=True))

            # Serialize data
            student_list = [{'id': student.id.username, 'name': student.full_name, 'email': student.id.email} for student in students]

            return JsonResponse({'students': student_list})
    
    return render(request, 'add_member.html')

def select_member(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            role = data.get('role')  # New role parameter

            if not student_id or not role:
                return JsonResponse({'message': 'Student ID or role not provided'}, status=400)

            student = get_object_or_404(get_user_model(), username=student_id)
            student_user = get_object_or_404(UserProfile, id=student)

            if role == 'member':
                student_user.role = 'member'
            elif role == 'core_member':
                student_user.role = 'core_member'
                

            student_user.save()

            if role == 'member':
                member = Member.objects.get_or_create(id=student_user)

            elif role == 'core_member':
                core_member = CoreMember.objects.get_or_create(id=student_user)


            return JsonResponse({
                'message': f'Student {student.username} selected as {role} successfully!',
                'student': {'id': student.username, 'email': student.email, 'role': role}
            })

        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)