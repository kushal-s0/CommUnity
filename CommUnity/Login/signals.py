# Faculty/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Faculty
from Login.models import UserProfile

@receiver(post_save, sender=Faculty)
def set_ssv_id(sender, instance, created, **kwargs):
    if created and instance.id and not instance.id.ssv_id:
        instance.id.ssv_id = instance.id.pk  
        instance.id.save()
