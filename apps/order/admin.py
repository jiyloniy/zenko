from django.contrib import admin
from .models import Order, Brujka


@admin.register(Brujka)
class BrujkaAdmin(admin.ModelAdmin):
    list_display = ('name', 'coating_type', 'color', 'is_active', 'created_at')
    list_filter = ('coating_type', 'is_active')
    search_fields = ('name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'brujka', 'name', 'quantity', 'status', 'priority', 'deadline', 'created_by', 'created_at')
    list_filter = ('status', 'priority', 'deadline')
    search_fields = ('order_number', 'name', 'created_by__name')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    autocomplete_fields = ('brujka',)
