from django.contrib import admin

from committees.models import Associations, Announcement
# Register your models here.

admin.site.register(Associations)
admin.site.register(Announcement)