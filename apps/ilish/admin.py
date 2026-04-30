from django.contrib import admin
from .models import Vishilka, IlishJarayon, IlishJarayonLog, QadoqlashJarayon, QadoqlashLog


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
    readonly_fields = ('created_at', 'updated_at')


@admin.register(IlishJarayonLog)
class IlishJarayonLogAdmin(admin.ModelAdmin):
    list_display  = ('jarayon', 'hodim', 'smena', 'vishilka', 'vishilka_soni', 'sana')
    list_filter   = ('smena', 'sana')
    search_fields = ('hodim__name', 'jarayon__order__name')
    readonly_fields = ('created_at',)


@admin.register(QadoqlashJarayon)
class QadoqlashJarayonAdmin(admin.ModelAdmin):
    list_display   = ('__str__', 'status', 'created_by', 'updated_at')
    list_filter    = ('status',)
    search_fields  = ('ilish_jarayon__order__name', 'ilish_jarayon__order__order_number')
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'ilish_jarayon__order', 'created_by', 'updated_by',
        )


@admin.register(QadoqlashLog)
class QadoqlashLogAdmin(admin.ModelAdmin):
    list_display  = ('smena', 'par_soni', 'sana', 'created_by')
    list_filter   = ('smena', 'sana')
    readonly_fields = ('created_at',)
