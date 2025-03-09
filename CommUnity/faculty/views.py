from django.shortcuts import render
from faculty.models import Faculty
from committees.models import Associations
from Login.models import UserProfile
# Create your views here.

def faculty_view(request):
    return render(request, 'faculty.html')
def profile_view(request):   

    return render(request, 'profile.html')


def faculty_committee(request):
    try:
        user = request.user
        user_profile = UserProfile.objects.get(id=user)
        faculty = Faculty.objects.get(id=user_profile)
        
        
        from django.db.models import Q
        associations = Associations.objects.filter(faculty_incharge=faculty)
        
        clubs = [a for a in associations if a.type == 'clubs']
        committees = [a for a in associations if a.type == 'committees']
                
        content = {'clubs': clubs, 'comm': committees}
        return render(request, 'committee.html', content)
    
    except (UserProfile.DoesNotExist, Faculty.DoesNotExist):
        # Handle case where user isn't associated with faculty
        content = {'clubs': [], 'comm': []}
        return render(request, 'committee.html', content)