from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('notifications/', views.notification_view, name='notification_view'),
    path('notifications/<int:pk>/open/', views.open_notification, name='open_notification'),
    path('notifications/read-all/', views.mark_all_read, name='mark_all_read'),
    path('mark_as_read/<int:announcement_id>/', views.mark_as_read, name='mark_as_read'),
    path('getprofile/', views.profile_view, name='getprofile'),
]
