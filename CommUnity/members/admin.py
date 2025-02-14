from django.contrib import admin
from members.models import CoreMember, Member, Preference
# Register your models here.

admin.site.register(CoreMember)
admin.site.register(Member)
admin.site.register(Preference)