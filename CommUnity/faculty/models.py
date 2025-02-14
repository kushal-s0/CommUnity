from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser

from Login.models import UserProfile
# Create your models here.

# Faculty Model
class Faculty(models.Model):
    id = models.OneToOneField(UserProfile, on_delete=models.CASCADE, primary_key=True)
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    locked_dates = models.JSONField()
    permissions = models.JSONField(default=list)

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
        return self.id,self.department,self.id.full_name