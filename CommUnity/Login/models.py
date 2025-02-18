from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser

# User Model (Extension)
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('faculty', 'Faculty'),
        ('core_member', 'Core Member'),
        ('member', 'Member'),
        ('non_participating', 'Non Participating')
    )

    id = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True)
    ssv_id = models.IntegerField(null=True, blank=True, unique=True)  # New field
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES,default='non_participating')
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg',null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id.username}, {self.full_name}, {self.role}"