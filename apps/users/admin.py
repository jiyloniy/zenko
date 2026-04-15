from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import Department, Role, Shift, User


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'description', 'created_at')
    list_filter = ('branch',)
    search_fields = ('name', 'description')


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name', 'description')


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'start_time', 'end_time', 'break_start', 'break_end')
    list_filter = ('branch',)
    search_fields = ('name',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
   

    list_display = ('name', 'username', 'role', 'department', 'shift', 'branch', 'is_active')
    list_filter = ('is_active', 'role', 'department', 'branch', 'shift')
    search_fields = ('name', 'username', 'phone')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('name', 'phone')}),
        ('Ish ma\'lumotlari', {'fields': ('role', 'department', 'shift', 'branch')}),
        ('Ruxsatlar', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Muhim sanalar', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'name', 'phone', 'role', 'department', 'shift', 'branch'),
        }),
    )

    filter_horizontal = ('groups', 'user_permissions')


