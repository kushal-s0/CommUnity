# Faculty/signals.py

# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import Faculty
# from Login.models import UserProfile

# @receiver(post_save, sender=Faculty)
# def set_ssv_id(sender, instance, created, **kwargs):
#     if created and instance.id and not instance.id.ssv_id:
#         instance.id.ssv_id = instance.id.pk  
#         instance.id.save()


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
from faculty.models import Faculty
from members.models import CoreMember, Member

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(id=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

@receiver(post_save, sender=UserProfile)
def create_or_update_faculty(sender, instance, **kwargs):
    if instance.role == 'faculty':
        Faculty.objects.get_or_create(id=instance)
    else:
        Faculty.objects.filter(id=instance).delete()

@receiver(post_save, sender=UserProfile)
def create_or_update_core_member(sender, instance, **kwargs):
    if instance.role == 'core_member':
        CoreMember.objects.get_or_create(id=instance)
    else:
        CoreMember.objects.filter(id=instance).delete()

@receiver(post_save, sender=UserProfile)
def create_or_update_member(sender, instance, **kwargs):
    if instance.role == 'member':
        Member.objects.get_or_create(id=instance)
    else:
        Member.objects.filter(id=instance).delete()