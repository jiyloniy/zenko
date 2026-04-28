from django.contrib import admin
from apps.casting.models import (
    Stanok, Zamak, RasxodLog, AdditionalOrder, AdditionalHomLog,
    AdditionalTayorLog, HomMahsulotLog, QuyishRasxod
)


@admin.register(Stanok)
class StanokAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')
    list_filter = ('status',)
    search_fields = ('name',)


@admin.register(Zamak)
class ZamakAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(RasxodLog)
class RasxodLogAdmin(admin.ModelAdmin):
    list_display = ('stanok', 'zamak', 'miqdor', 'sana', 'created_by')
    list_filter = ('sana', 'stanok')
    search_fields = ('stanok__name', 'zamak__name')
    readonly_fields = ('created_at',)


@admin.register(QuyishRasxod)
class QuyishRasxodAdmin(admin.ModelAdmin):
    list_display = ('nomi', 'miqdor', 'sana', 'created_by')
    list_filter = ('sana',)
    search_fields = ('nomi',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AdditionalOrder)
class AdditionalOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'name', 'quantity', 'status', 'created_by')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'order_number')
    readonly_fields = ('order_number', 'created_at', 'updated_at')


@admin.register(AdditionalHomLog)
class AdditionalHomLogAdmin(admin.ModelAdmin):
    list_display = ('add_order', 'stanok', 'miqdor', 'sana', 'created_by')
    list_filter = ('sana',)
    search_fields = ('add_order__name', 'stanok__name')
    readonly_fields = ('created_at',)


@admin.register(AdditionalTayorLog)
class AdditionalTayorLogAdmin(admin.ModelAdmin):
    list_display = ('add_order', 'miqdor', 'sana', 'created_by')
    list_filter = ('sana',)
    search_fields = ('add_order__name',)
    readonly_fields = ('created_at',)


@admin.register(HomMahsulotLog)
class HomMahsulotLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'stanok', 'miqdor', 'sana', 'created_by')
    list_filter = ('sana', 'stanok')
    search_fields = ('order__name', 'stanok__name')
    readonly_fields = ('created_at',)


