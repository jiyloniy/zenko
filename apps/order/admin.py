from django.contrib import admin
from .models import (
    Order, CastingStage, MontajStage, HangingStage, StoneSettingStage, PackagingStage, WarehouseStage,
    OutsourceWork, QualityControl, OrderStageLog, Stanok, StanokLog,
    AttachStage, SprayStage, PaintStage, StoneStage, AssemblyStage, PackStage,
)

@admin.register(Stanok)
class StanokAdmin(admin.ModelAdmin):
	list_display = ('name', 'model', 'is_active', 'created_at')
	list_filter = ('is_active',)
	search_fields = ('name', 'model')

# Bosqich loglari faqat o'qish uchun (readonly)
class OrderStageLogInline(admin.TabularInline):
	model = OrderStageLog
	extra = 0
	readonly_fields = ('stage', 'from_department', 'to_department', 'quantity', 'worker', 'accepted_by', 'note', 'created_at')
	can_delete = False
	show_change_link = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ('order_number', 'name', 'quantity', 'status', 'current_stage', 'deadline', 'created_by', 'created_at')
	list_filter = ('status', 'current_stage', 'deadline')
	search_fields = ('order_number', 'name', 'created_by__name')
	inlines = [OrderStageLogInline]
	readonly_fields = ('created_at', 'updated_at')

@admin.register(CastingStage)
class CastingStageAdmin(admin.ModelAdmin):
	list_display = ('order', 'status', 'total_quantity', 'defect_quantity', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(MontajStage)
class MontajStageAdmin(admin.ModelAdmin):
	list_display = ('order', 'status', 'total_quantity', 'assembled_quantity', 'defect_quantity', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(HangingStage)
class HangingStageAdmin(admin.ModelAdmin):
	list_display = ('order', 'status', 'total_quantity', 'hung_quantity', 'soaked_quantity', 'defect_quantity', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(StoneSettingStage)
class StoneSettingStageAdmin(admin.ModelAdmin):
	list_display = ('order', 'status', 'total_quantity', 'stones_set_quantity', 'defect_quantity', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(PackagingStage)
class PackagingStageAdmin(admin.ModelAdmin):
	list_display = ('order', 'status', 'total_quantity', 'packed_quantity', 'defect_quantity', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(WarehouseStage)
class WarehouseStageAdmin(admin.ModelAdmin):
	list_display = ('order', 'status', 'received_quantity', 'delivered_quantity', 'receiver', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(OutsourceWork)
class OutsourceWorkAdmin(admin.ModelAdmin):
	list_display = ('order', 'contractor', 'status', 'sent_quantity', 'received_quantity', 'defect_quantity', 'created_at')
	list_filter = ('status',)
	search_fields = ('order__order_number', 'order__name', 'contractor')
	readonly_fields = ('created_at', 'updated_at')

@admin.register(QualityControl)
class QualityControlAdmin(admin.ModelAdmin):
	list_display = ('order', 'stage', 'result', 'checked_quantity', 'passed_quantity', 'defect_quantity', 'inspector', 'created_at')
	list_filter = ('stage', 'result')
	search_fields = ('order__order_number', 'order__name', 'inspector__name')
	readonly_fields = ('created_at',)

@admin.register(OrderStageLog)
class OrderStageLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'stage', 'from_department', 'to_department', 'quantity', 'worker', 'accepted_by', 'created_at')
    list_filter = ('stage', 'worker', 'accepted_by')
    search_fields = ('order__order_number', 'order__name', 'worker__name', 'accepted_by__name')
    readonly_fields = ('order', 'stage', 'from_department', 'to_department', 'quantity', 'worker', 'accepted_by', 'note', 'created_at')


@admin.register(StanokLog)
class StanokLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'stanok', 'worker', 'quantity', 'defect', 'side', 'created_at')
    list_filter = ('side', 'stanok')
    search_fields = ('order__order_number', 'order__name', 'worker__name')


@admin.register(AttachStage)
class AttachStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'total_quantity', 'defect_quantity', 'created_at')
    list_filter = ('status',)


@admin.register(SprayStage)
class SprayStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'layer_number', 'layer_type', 'total_quantity', 'defect_quantity', 'created_at')
    list_filter = ('status', 'layer_type')


@admin.register(PaintStage)
class PaintStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'layer_number', 'total_quantity', 'defect_quantity', 'created_at')
    list_filter = ('status',)


@admin.register(StoneStage)
class StoneStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'total_quantity', 'defect_quantity', 'created_at')
    list_filter = ('status',)


@admin.register(AssemblyStage)
class AssemblyStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'total_quantity', 'defect_quantity', 'created_at')
    list_filter = ('status',)


@admin.register(PackStage)
class PackStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'total_quantity', 'packed_quantity', 'defect_quantity', 'created_at')
    list_filter = ('status',)
