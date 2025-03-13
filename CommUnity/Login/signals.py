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

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(id=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
