from django.contrib import admin
from members.models import CoreMember, Member
# Register your models here.

admin.site.register(CoreMember)
admin.site.register(Member)
