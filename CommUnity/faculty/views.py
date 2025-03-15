from django.shortcuts import render,get_object_or_404
from faculty.models import Faculty
from committees.models import Associations
from Login.models import UserProfile
from committees.models import Associations
from members.models import CoreMember, Member

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from django.db.models import Q

from django.contrib.auth import get_user_model

User = get_user_model()

# Create your views here.

def faculty_view(request):
    return render(request, 'faculty.html')
def profile_view(request):   
    active_user = request.user
    user = get_object_or_404(User, username=active_user.username)
    print(user.email)
    user_profile = get_object_or_404(UserProfile, id=user)
    faculty = Faculty.objects.get(id=user_profile)
    associations = Associations.objects.filter(faculty_incharge=faculty)
    print(associations)
    context = {'user': user,'user_profile': user_profile,'faculty': faculty,'associations': associations}
    return render(request, 'profile.html', context)
def committee_member_view( request,pk):
    committee = get_object_or_404(Associations, pk=pk)
    members = Member.objects.filter(club=committee)
    core_members = CoreMember.objects.filter(club=committee)
    context = {'committee': committee, 'members': members, 'core_members': core_members}
    print(context)

    return render(request, 'committee_member.html', context)


def faculty_committee(request):
    try:
        user = request.user
        user_profile = get_object_or_404(UserProfile, id=user)
        faculty = Faculty.objects.get(id=user_profile)
        
        
        from django.db.models import Q
        associations = Associations.objects.filter(faculty_incharge=faculty)
        
        clubs = [a for a in associations if a.type == 'clubs']
        committees = [a for a in associations if a.type == 'committees']
                
        request.session['url'] = 'faculty_committee'
        content = {'clubs': clubs, 'comm': committees}
        return render(request, 'committee.html', content)
    

    except (UserProfile.DoesNotExist, Faculty.DoesNotExist):
        # Handle case where user isn't associated with faculty
        content = {'clubs': [], 'comm': []}
        return render(request, 'committee.html', content)

@csrf_exempt  # Use this only if CSRF protection is disabled; otherwise, use CSRF token
def search_students(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query', '').lower()

        students = UserProfile.objects.filter(name__icontains=query) | UserProfile.objects.filter(email__icontains=query)
        student_list = [{'name': student.name, 'email': student.email} for student in students]

        return JsonResponse({'students': student_list})

    return JsonResponse({'error': 'Invalid request'}, status=400)
def add_core_member_view(request):
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
    
    return render(request, 'add_core_member.html')

def select_student(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')

            if not student_id:
                return JsonResponse({'message': 'Student ID not provided'}, status=400)

            # Fetch the student from the database (modify based on your model structure)
            student = get_object_or_404(User, username=student_id)  # Assuming username is the student ID
            student_user = get_object_or_404(UserProfile, id=student)
            print(student_user)
            student_user.role = 'Core Member'
            student_user.save()

            core_update = CoreMember.objects.create(id=student_user)
            core_update.save()
            # Do something with the selected student (e.g., add to a list, update, etc.)
            # Example: Returning student details
            return JsonResponse({
                'message': f'Student {student.username} selected successfully!',
                'student': {
                    'id': student.username,
                    'email': student.email,
                }
            })

        except User.DoesNotExist:
            return JsonResponse({'message': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)

    return render(request, 'add_core_member.html')