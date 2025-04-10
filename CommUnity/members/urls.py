from . import views
from django.urls import path

urlpatterns = [
    path('add_announcement/', views.add_announcement, name='add_announcement'),
    path('add_member/', views.add_member, name='add_member'),
    path('select_member/',views.select_member,name='select_member'),
    path('<int:announcement_id>/', views.announcement_details, name='announcement_details'),
]
