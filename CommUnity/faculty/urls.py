from django.urls import path

from faculty import views

urlpatterns = [
    path('', views.faculty_view, name='faculty'),
    path('profile', views.profile_view, name='profile'),
    path('committee', views.faculty_committee, name='faculty_committee'),
    path('committee_member/<int:pk>/', views.committee_member_view, name='committee_member'),
    path('club_member/<int:pk>/', views.club_member_view, name='club_member'),
    path('add_core_member', views.add_core_member_view, name='add_core_member'),
    path('select_student', views.select_student, name='select_student'),
    path('approve_clubs/', views.approve_clubs, name='approve_clubs'),
    path('faculty-lock-dates/', views.manage_faculty_lock_dates, name='manage_faculty_lock_dates'),
    path('reports/', views.faculty_reports, name='faculty_reports'),
]
