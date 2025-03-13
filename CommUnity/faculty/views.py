from django.shortcuts import render,get_object_or_404
from faculty.models import Faculty
from committees.models import Associations
from Login.models import UserProfile
from committees.models import Associations
from members.models import CoreMember, Member

from django.contrib.auth.models import User
# Create your views here.

def faculty_view(request):
    return render(request, 'faculty.html')
def profile_view(request):   
    active_user = request.user
    user = User.objects.get(username=active_user)
    print(user.email)
    user_profile = UserProfile.objects.get(id=active_user)
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
        user_profile = UserProfile.objects.get(id=user)
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