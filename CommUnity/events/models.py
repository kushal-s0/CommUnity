from datetime import timedelta

from django.db import models
from django.utils import timezone

from committees.models import Associations
from faculty.models import Faculty
from Login.models import UserProfile


class Location(models.Model):
    id = models.AutoField(primary_key=True)
    location = models.CharField(max_length=255, default='online')
    capacity = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['location']

    @property
    def is_online(self):
        return self.location.strip().lower() == 'online'

    def __str__(self):
        return self.location.title()


# Faculty Lock Date Model (For Exams & College Fest)
class FacultyLockDate(models.Model):
    locked_date = models.DateField(unique=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['locked_date']

    def __str__(self):
        return f"{self.locked_date} - {self.reason if self.reason else 'Locked'}"


class Event(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_time = models.DateTimeField()
    duration = models.IntegerField(default=1)  # hours
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    association = models.ForeignKey(Associations, on_delete=models.CASCADE)
    created_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='created_events')
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    poster = models.ImageField(upload_to='event_posters/', blank=True, null=True)
    max_participants = models.PositiveIntegerField(blank=True, null=True)
    registration_open = models.BooleanField(default=True)

    # Review workflow
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(Faculty, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, default='')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)

    # Post-event report
    report_generated = models.BooleanField(default=False)
    report_content = models.TextField(blank=True, null=True)
    report_generated_at = models.DateTimeField(blank=True, null=True)
    report_pdf = models.FileField(upload_to='reports/', blank=True, null=True)
    report_data = models.JSONField(default=dict, blank=True)
    report_provider = models.CharField(max_length=40, blank=True, default='')

    class Meta:
        ordering = ['date_time']

    @property
    def end_time(self):
        return self.date_time + timedelta(hours=self.duration)

    @property
    def phase(self):
        """upcoming / ongoing / completed, based on the scheduled time."""
        now = timezone.now()
        if now < self.date_time:
            return 'upcoming'
        if now < self.end_time:
            return 'ongoing'
        return 'completed'

    @property
    def is_completed(self):
        return self.phase == 'completed'

    @property
    def display_status(self):
        """Single label combining review status and lifecycle phase."""
        if self.status == 'approved':
            return {'upcoming': 'Scheduled', 'ongoing': 'Live now', 'completed': 'Completed'}[self.phase]
        return self.get_status_display()

    @property
    def status_tone(self):
        if self.status == 'approved':
            return {'upcoming': 'approved', 'ongoing': 'live', 'completed': 'completed'}[self.phase]
        return self.status

    @property
    def seats_left(self):
        if not self.max_participants:
            return None
        return max(self.max_participants - self.registrations.count(), 0)

    @property
    def can_register(self):
        return (
            self.status == 'approved'
            and self.registration_open
            and self.phase == 'upcoming'
            and self.seats_left != 0
        )

    def __str__(self):
        return f"{self.title} - {self.date_time} - {self.association.name}"


class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    participant = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='event_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)

    class Meta:
        ordering = ['registered_at']
        constraints = [
            models.UniqueConstraint(fields=['event', 'participant'], name='unique_event_registration'),
        ]

    def __str__(self):
        return f"{self.participant.display_name} -> {self.event.title}"


class EventLog(models.Model):
    """Audit trail of everything that happens to an event, shown as a timeline."""

    ACTION_CHOICES = (
        ('created', 'Submitted for approval'),
        ('updated', 'Updated and resubmitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('calendar', 'Added to Google Calendar'),
        ('report', 'Post-event report generated'),
        ('report_edited', 'Post-event report edited'),
    )

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='logs')
    actor = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    note = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.event.title}: {self.action}"
