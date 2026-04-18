from django.contrib import admin

from apps.attendance.models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'branch', 'date', 'check_in', 'check_out', 'status', 'created_at')
    list_filter = ('branch', 'status', 'date')
    search_fields = ('user__name', 'user__username')
    date_hierarchy = 'date'
    raw_id_fields = ('user',)
