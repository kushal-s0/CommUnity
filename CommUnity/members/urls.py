from django.urls import path

from . import views

urlpatterns = [
    path('add_announcement/', views.add_announcement, name='add_announcement'),
    path('add_member/', views.add_member, name='add_member'),
    path('select_member/', views.select_member, name='select_member'),
    path('remove_member/<int:profile_id>/', views.remove_member, name='remove_member'),
    path('notice-board/', views.notice_board, name='notice_board'),
    path('<int:announcement_id>/', views.announcement_details, name='announcement_details'),
    path('<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),
]
