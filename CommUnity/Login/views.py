from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm

from Login.models import UserProfile
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

        #check if user is core member
        if role == 'core_member':
            return redirect('core_member')
        
        if role == 'member':
            return redirect('member')
        
        if role == 'non_participating':
            return render(request, 'account/home.html')
    else:
        return render(request, 'account/home.html')