from django.db import models
from faculty.models import Faculty
from members.models import CoreMember
from Login.models import UserProfile

# Associations Model
class Associations(models.Model):
    ROLE_CHOICES = (
        ('committees', 'Committees'),
        ('clubs', 'Clubs')
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=15, choices=ROLE_CHOICES)
    faculty_incharge = models.ForeignKey('faculty.Faculty', on_delete=models.CASCADE)
    created_by = models.ForeignKey('members.CoreMember', on_delete=models.CASCADE, null=True, blank=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='association_images/', null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.name}-{self.status}"
# Announcements Model
class Announcement(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    club = models.ForeignKey('committees.Associations', on_delete=models.CASCADE)
    created_by = models.ForeignKey('members.CoreMember', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)    

    def __str__(self):  
        return f"{self.id},{self.title}"

class Nofification(models.Model):
    PRIORITY = (
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low')
    )
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    priority = models.CharField(max_length=15, choices=PRIORITY)
    message = models.TextField()
    created_by = models.ForeignKey('members.CoreMember', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    message_to = models.ForeignKey('Login.UserProfile', on_delete=models.CASCADE) #message_to
    email = models.EmailField(blank=True, null=True)
    def __str__(self):  
        return f"{self.id},{self.title}"

class AssociationImage(models.Model):
    association = models.ForeignKey(Associations, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='association_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.association.name} - Image {self.id}"
