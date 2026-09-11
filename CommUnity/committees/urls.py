from django.urls import path

from . import views

urlpatterns = [
    path('add/', views.add_club_committee, name='add_club_committee'),
    path('clubs/', views.club_list, name='club_list'),
    path('committees/', views.committees_list, name='committees_list'),
    path('club/<int:pk>/', views.association_detail, name='club_detail'),
    path('committee/<int:pk>/', views.association_detail, name='committees_detail'),
    path('club/<int:pk>/edit/', views.edit_club_committee, name='edit_club_committee'),
    path('club/<int:pk>/delete/', views.delete_club_committee, name='delete_club_committee'),
    path('<int:pk>/follow/', views.toggle_follow, name='toggle_follow'),
    path('<int:pk>/images/<int:image_id>/delete/', views.delete_association_image, name='delete_association_image'),
    path('transfer-ownership/<int:pk>/', views.transfer_ownership, name='transfer_ownership'),
]
