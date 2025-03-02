from django.db import models
from faculty.models import Faculty
from members.models import CoreMember

# Associations Model
class Associations(models.Model):
    ROLE_CHOICES = (
        ('committees', 'Committees'),
        ('clubs', 'Clubs')
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=15, choices=ROLE_CHOICES)
    faculty_incharge = models.ForeignKey('faculty.Faculty', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='association_images/', null=True, blank=True)

    def __str__(self):
        return self.name
# Announcements Model
class Announcement(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    club = models.ForeignKey('committees.Associations', on_delete=models.CASCADE)
    created_by = models.ForeignKey('members.CoreMember', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)    

    def __str__(self):  
        return self.title