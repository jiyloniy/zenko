from django.contrib import admin
from .models import Tosh, ToshQadashJarayon, ToshQadashLog, KleyRasxod, ToshRasxod, QabulJarayon


@admin.register(Tosh)
class ToshAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'is_active', 'created_by', 'created_at')
    list_filter   = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Asosiy', {'fields': ('name', 'code', 'is_active')}),
        ('Meta', {'fields': ('created_by', 'created_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ToshQadashJarayon)
class ToshQadashJarayonAdmin(admin.ModelAdmin):
    list_display  = ('order', 'status', 'updated_by', 'updated_at')
    list_filter   = ('status', 'created_at', 'updated_at')
    search_fields = ('order__name', 'order__order_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Asosiy', {'fields': ('order', 'status')}),
        ('Eslatma', {'fields': ('izoh',)}),
        ('Meta', {'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ToshQadashLog)
class ToshQadashLogAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'hodim', 'smena', 'tosh', 'par_soni', 'sana', 'created_by')
    list_filter   = ('smena', 'sana', 'tosh')
    search_fields = ('hodim__name', 'jarayon__order__name')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Asosiy', {'fields': ('jarayon', 'hodim', 'tosh', 'smena', 'par_soni', 'sana')}),
        ('Eslatma', {'fields': ('izoh',)}),
        ('Meta', {'fields': ('created_by', 'created_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(KleyRasxod)
class KleyRasxodAdmin(admin.ModelAdmin):
    list_display  = ('smena', 'kley_gramm', 'sana', 'created_by')
    list_filter   = ('smena', 'sana')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Asosiy', {'fields': ('smena', 'kley_gramm', 'sana')}),
        ('Tafsil', {'fields': ('izoh',)}),
        ('Meta', {'fields': ('created_by', 'created_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ToshRasxod)
class ToshRasxodAdmin(admin.ModelAdmin):
    list_display  = ('tosh', 'smena', 'tosh_gramm', 'sana', 'created_by')
    list_filter   = ('smena', 'sana', 'tosh')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Asosiy', {'fields': ('tosh', 'smena', 'tosh_gramm', 'sana')}),
        ('Tafsil', {'fields': ('izoh',)}),
        ('Meta', {'fields': ('created_by', 'created_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(QabulJarayon)
class QabulJarayonAdmin(admin.ModelAdmin):
    list_display  = ('tosh_jarayon', 'status', 'updated_by', 'updated_at')
    list_filter   = ('status', 'created_at', 'updated_at')
    search_fields = ('tosh_jarayon__order__name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Asosiy', {'fields': ('tosh_jarayon', 'status')}),
        ('Eslatma', {'fields': ('izoh',)}),
        ('Meta', {'fields': ('updated_by', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
