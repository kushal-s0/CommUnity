from django.urls import path

from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('create/', views.create_event, name='create_event'),
    path('calendar/', views.view_calendar, name='view_calendar'),
    path('calendar.ics', views.calendar_feed, name='calendar_feed'),
    path('get_calendar_events/', views.get_calendar_events, name='get_calendar_events'),
    path('check-slot/', views.check_slot, name='check_slot'),
    path('details/<int:event_id>/', views.event_details, name='event_details'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/cancel/', views.cancel_event_view, name='cancel_event'),
    path('<int:event_id>/review/', views.review_event_view, name='review_event'),
    path('<int:event_id>/register/', views.toggle_registration, name='toggle_registration'),
    path('<int:event_id>/attendees/', views.event_attendees, name='event_attendees'),
    path('<int:event_id>/ics/', views.event_ics, name='event_ics'),
    path('<int:event_id>/report/', views.event_report, name='event_report'),
    path('<int:event_id>/report/generate/', views.generate_event_report, name='generate_event_report'),
]
