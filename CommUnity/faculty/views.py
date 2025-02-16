from django.shortcuts import render
from faculty.models import Faculty
# Create your views here.

def faculty_view(request):
    return render(request, 'faculty.html')
def profile_view(request):

    data = Faculty.objects.filter(id=request.user.id)

    return render(request, 'profile.html', {'data': data})