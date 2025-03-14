from django.urls import path,include
from django.contrib import admin

from faculty import views

urlpatterns = [
    path('', views.faculty_view, name='faculty'),
    path('profile', views.profile_view, name='profile'),
    path('committee', views.faculty_committee, name='faculty_committee'),
    path('committee_member/<int:pk>/', views.committee_member_view, name='committee_member'),
    path('add_core_member', views.add_core_member_view, name='add_core_member'),
    path('select_student',views.select_student,name='select_student'),
]