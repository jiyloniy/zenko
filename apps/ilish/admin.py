from django.contrib import admin
from .models import Vishilka, IlishJarayon, IlishJarayonLog


@admin.register(Vishilka)
class VishilkaAdmin(admin.ModelAdmin):
    list_display  = ('nomi', 'quantity', 'broshka_per_vishilka', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('nomi',)


@admin.register(IlishJarayon)
class IlishJarayonAdmin(admin.ModelAdmin):
    list_display  = ('order', 'status', 'created_by', 'updated_at')
    list_filter   = ('status',)
    search_fields = ('order__name', 'order__order_number')


@admin.register(IlishJarayonLog)
class IlishJarayonLogAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'hodim', 'smena', 'vishilka', 'vishilka_soni', 'sana')
    list_filter   = ('smena', 'sana')
    search_fields = ('hodim__name', 'jarayon__order__name')
