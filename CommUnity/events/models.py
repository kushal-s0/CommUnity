from django.db import models
from Login.models import UserProfile
from faculty.models import Faculty
from committees.models import Club

# Create your models here.

# Events Model
class Event(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    )

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_time = models.DateTimeField()
    location = models.ForeignKey('events.Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='event_location')  # Allow events to exist without location
    club = models.ForeignKey('committees.Club', on_delete=models.CASCADE)
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='created_events')
    approved_by = models.ForeignKey('faculty.Faculty', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return self.title, self.date_time, self.club

# Location Model
# Location Model
class Location(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    booked_from = models.DateTimeField()
    booked_to = models.DateTimeField()
    event = models.ForeignKey('Event', on_delete=models.CASCADE, null=True, blank=True, related_name='event_location')



    def __str__(self):
        return self.name