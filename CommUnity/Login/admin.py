from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from Login.models import CustomUser, Notification, UserProfile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'id', 'role', 'ssv_id')
    list_filter = ('role',)
    search_fields = ('full_name', 'id__email', 'id__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'kind', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')
