from django.contrib import admin

from committees.models import Associations, Announcement, AssociationImage
# Register your models here.

admin.site.register(Associations)
admin.site.register(Announcement)
admin.site.register(AssociationImage)