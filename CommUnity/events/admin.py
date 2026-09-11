from django.contrib import admin

from events.models import Event, EventLog, EventRegistration, FacultyLockDate, Location


class EventLogInline(admin.TabularInline):
    model = EventLog
    extra = 0
    readonly_fields = ('action', 'actor', 'note', 'created_at')
    can_delete = False


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'association', 'date_time', 'location', 'status', 'report_generated')
    list_filter = ('status', 'report_generated', 'association__category', 'location')
    search_fields = ('title', 'description', 'association__name')
    date_hierarchy = 'date_time'
    inlines = [EventLogInline]


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('event', 'participant', 'registered_at', 'attended')
    list_filter = ('attended',)


@admin.register(FacultyLockDate)
class FacultyLockDateAdmin(admin.ModelAdmin):
    list_display = ('locked_date', 'reason', 'created_by')


admin.site.register(Location)
