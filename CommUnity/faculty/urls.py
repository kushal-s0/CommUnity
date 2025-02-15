from django.urls import path,include
from django.contrib import admin

from faculty import views

urlpatterns = [
    path('', views.faculty_view, name='faculty'),
    path('profile', views.profile_view, name='profile'),
]