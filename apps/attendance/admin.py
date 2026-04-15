from django.contrib import admin

from apps.attendance.models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'shift', 'branch', 'check_in', 'check_out', 'status', 'is_overtime')
    list_filter = ('status', 'is_overtime', 'branch', 'shift', 'date')
    search_fields = ('user__name', 'user__username')
    date_hierarchy = 'date'
    raw_id_fields = ('user',)
    list_per_page = 50
