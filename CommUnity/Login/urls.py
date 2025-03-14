from . import views
from django.urls import path

urlpatterns = [
    path('', views.home_view, name='home'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    
]
