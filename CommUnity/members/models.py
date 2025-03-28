from django.db import models

from Login.models import UserProfile

# Create your models here.
# Core Members Model
class CoreMember(models.Model):
    id = models.OneToOneField(UserProfile, on_delete=models.CASCADE, primary_key=True)
    association = models.ForeignKey('committees.Associations', on_delete=models.CASCADE,null=True,blank=True)#change
    position = models.CharField(max_length=100,null=True,blank=True)
    can_approve_members = models.BooleanField(default=False)
    can_edit_events = models.BooleanField(default=False)
    can_edit_club_page = models.BooleanField(default=False)
    permissions = models.JSONField(default=list, blank=True)

    def add_permission(self, permission):
        if permission not in self.permissions:
            self.permissions.append(permission)
            self.save()

    def remove_permission(self, permission):
        if permission in self.permissions:
            self.permissions.remove(permission)
            self.save()

    def has_permission(self, permission):
        return permission in self.permissions
    def __str__(self):
        return f"{self.id}"
    
# Members Model
class Member(models.Model):
    id = models.OneToOneField(UserProfile, on_delete=models.CASCADE, primary_key=True)
    association = models.JSONField(default=list, blank=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    NOTIFICATION_CHOICES = (
        ('email', 'Email'),
        ('none', 'None')
    )
    notification_preference = models.CharField(max_length=10, choices=NOTIFICATION_CHOICES)


    def __str__(self):
        return f"{self.id}" 

