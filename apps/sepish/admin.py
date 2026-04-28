from django.contrib import admin
from .models import Kraska, SepishJarayon, SepishJarayonLog


@admin.register(Kraska)
class KraskaAdmin(admin.ModelAdmin):
    list_display  = ('code', 'name', 'color_hex', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('code', 'name')


@admin.register(SepishJarayon)
class SepishJarayonAdmin(admin.ModelAdmin):
    list_display  = ('order', 'status', 'created_by', 'updated_at')
    list_filter   = ('status',)
    search_fields = ('order__name', 'order__order_number')


@admin.register(SepishJarayonLog)
class SepishJarayonLogAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'smena', 'par_soni', 'kraska', 'kraska_gramm', 'sana', 'created_by')
    list_filter   = ('smena', 'sana')
