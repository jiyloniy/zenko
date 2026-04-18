
# Bosqich harakati logi uchun to‘liq forma
from apps.order.models import OrderStageLog
from django import forms
class OrderStageLogForm(forms.ModelForm):
    class Meta:
        model = OrderStageLog
        fields = ('stage', 'from_department', 'to_department', 'quantity', 'worker', 'accepted_by', 'note')
        widgets = {
            'stage': forms.Select(attrs={'class': 'form-control'}),
            'from_department': forms.TextInput(attrs={'class': 'form-control'}),
            'to_department': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'worker': forms.Select(attrs={'class': 'form-control'}),
            'accepted_by': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
from django import forms
from apps.order.models import (
    Order, CastingStage, MontajStage, HangingStage,
    StoneSettingStage, PackagingStage, WarehouseStage,
    OutsourceWork, QualityControl,
)


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('name', 'quantity', 'image', 'deadline', 'status', 'current_stage', 'note')
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class CastingForm(forms.ModelForm):
    class Meta:
        model = CastingStage
        fields = ('status', 'total_quantity', 'defect_quantity', 'note', 'started_at', 'finished_at')
        widgets = {
            'started_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'finished_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class MontajForm(forms.ModelForm):
    class Meta:
        model = MontajStage
        fields = ('status', 'total_quantity', 'assembled_quantity', 'defect_quantity',
                  'worker', 'note', 'started_at', 'finished_at')
        widgets = {
            'started_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'finished_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class HangingForm(forms.ModelForm):
    class Meta:
        model = HangingStage
        fields = ('status', 'total_quantity', 'hung_quantity', 'soaked_quantity',
                  'defect_quantity', 'worker', 'note', 'started_at', 'finished_at')
        widgets = {
            'started_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'finished_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class StoneSettingForm(forms.ModelForm):
    class Meta:
        model = StoneSettingStage
        fields = ('status', 'total_quantity', 'stones_set_quantity', 'defect_quantity',
                  'worker', 'note', 'started_at', 'finished_at')
        widgets = {
            'started_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'finished_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class PackagingForm(forms.ModelForm):
    class Meta:
        model = PackagingStage
        fields = ('status', 'total_quantity', 'packed_quantity', 'defect_quantity',
                  'worker', 'note', 'started_at', 'finished_at')
        widgets = {
            'started_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'finished_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class WarehouseForm(forms.ModelForm):
    class Meta:
        model = WarehouseStage
        fields = ('status', 'received_quantity', 'delivered_quantity',
                  'receiver', 'note', 'received_at', 'delivered_at')
        widgets = {
            'received_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'delivered_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class OutsourceForm(forms.ModelForm):
    class Meta:
        model = OutsourceWork
        fields = ('status', 'work_description', 'contractor', 'contractor_phone',
                  'sent_quantity', 'received_quantity', 'defect_quantity', 'cost',
                  'return_to_stage', 'note', 'sent_at', 'received_at')
        widgets = {
            'sent_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'received_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'work_description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class QualityControlForm(forms.ModelForm):
    class Meta:
        model = QualityControl
        fields = ('stage', 'result', 'checked_quantity', 'passed_quantity',
                  'defect_quantity', 'defect_reason', 'inspector', 'note', 'checked_at')
        widgets = {
            'checked_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'defect_reason': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
