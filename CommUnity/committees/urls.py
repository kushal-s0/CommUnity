from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_club_committee, name='add_club_committee'),
    path('clubs/', views.club_list, name='club_list'),
    path('committees/', views.committees_list, name='committees_list'),
    path('club/<int:pk>/', views.club_detail, name='club_detail'),
    path('committee/<int:pk>/', views.committees_detail, name='committees_detail'),
    path('club/<int:pk>/edit/', views.edit_club_committee, name='edit_club_committee'),
    path('club/<int:pk>/delete/', views.delete_club_committee, name='delete_club_committee'),
    path('add_announcement/', views.add_announcement, name='add_announcement'),
    path('add_event/', views.add_event, name='add_event'),
]

