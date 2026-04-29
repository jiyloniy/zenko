from django.contrib import admin
from .models import Tosh, ToshQadashJarayon, ToshQadashLog, KleyRasxod, ToshRasxod, QabulJarayon


@admin.register(Tosh)
class ToshAdmin(admin.ModelAdmin):
    list_display  = ('name', 'code', 'is_active', 'created_at')
    list_filter   = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(ToshQadashJarayon)
class ToshQadashJarayonAdmin(admin.ModelAdmin):
    list_display  = ('order', 'status', 'created_by', 'updated_at')
    list_filter   = ('status',)
    search_fields = ('order__name', 'order__order_number')


@admin.register(ToshQadashLog)
class ToshQadashLogAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'hodim', 'smena', 'tosh', 'par_soni', 'sana')
    list_filter   = ('smena', 'sana')
    search_fields = ('hodim__name',)


@admin.register(KleyRasxod)
class KleyRasxodAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'smena', 'kley_gramm', 'sana')
    list_filter   = ('smena', 'sana')


@admin.register(ToshRasxod)
class ToshRasxodAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'tosh', 'smena', 'tosh_gramm', 'sana')
    list_filter   = ('smena', 'sana', 'tosh')


@admin.register(QabulJarayon)
class QabulJarayonAdmin(admin.ModelAdmin):
    list_display  = ('tosh_jarayon', 'status', 'updated_by', 'updated_at')
    list_filter   = ('status',)
