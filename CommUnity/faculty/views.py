from django.shortcuts import render

# Create your views here.

def faculty_view(request):
    return render(request, 'faculty.html')
def profile_view(request):
    return render(request, 'profile.html')