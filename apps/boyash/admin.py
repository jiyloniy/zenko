from django.contrib import admin
from .models import BoyashVishilka, BoyashJarayon, BoyashJarayonLog


@admin.register(BoyashVishilka)
class BoyashVishilkaAdmin(admin.ModelAdmin):
    list_display  = ('nomi', 'quantity', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('nomi',)


@admin.register(BoyashJarayon)
class BoyashJarayonAdmin(admin.ModelAdmin):
    list_display  = ('order', 'status', 'created_by', 'updated_at')
    list_filter   = ('status',)
    search_fields = ('order__name', 'order__order_number')


@admin.register(BoyashJarayonLog)
class BoyashJarayonLogAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'smena', 'vishilka', 'vishilka_soni', 'sana', 'created_by')
    list_filter   = ('smena', 'sana')
