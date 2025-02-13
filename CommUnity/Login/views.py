from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
# Create your views here.



def home_view(request):
    return render(request, 'account/home.html')