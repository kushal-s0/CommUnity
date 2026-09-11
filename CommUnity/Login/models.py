from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)


# User Model (Extension)
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('faculty', 'Faculty'),
        ('core_member', 'Core Member'),
        ('member', 'Member'),
        ('non_participating', 'Non Participating')
    )

    id = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    ssv_id = models.IntegerField(null=True, blank=True, unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='non_participating')
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    preferences = models.JSONField(default=list, null=True, blank=True)  # IDs of followed associations
    notification_read = models.JSONField(default=list, null=True, blank=True)  # IDs of read announcements

    def save(self, *args, **kwargs):
        # Automatically assign ssv_id if not provided
        if self.ssv_id is None:
            last_ssv = UserProfile.objects.order_by('-ssv_id').first()
            self.ssv_id = (last_ssv.ssv_id + 1) if last_ssv and last_ssv.ssv_id else 1000
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.full_name or self.id.get_full_name() or self.id.email.split('@')[0]

    @property
    def initials(self):
        parts = self.display_name.split()
        return ''.join(p[0] for p in parts[:2]).upper() or '?'

    @property
    def avatar_url(self):
        """URL of an uploaded picture, or None when only the stock default is set."""
        if self.profile_picture and not self.profile_picture.name.endswith('default.jpg'):
            try:
                return self.profile_picture.url
            except ValueError:
                return None
        return None

    @property
    def followed_ids(self):
        return [int(pk) for pk in (self.preferences or []) if str(pk).isdigit()]

    def __str__(self):
        return f"{self.id.username}, {self.full_name}, {self.role}"


class Notification(models.Model):
    """In-app notification for a single user (approvals, rejections, reminders)."""

    KIND_CHOICES = (
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Alert'),
    )

    recipient = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.display_name}: {self.title}"
