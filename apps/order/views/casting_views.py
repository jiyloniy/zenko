from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.order.models import Order, CastingStage
from apps.order.forms import CastingForm
from apps.order.views.mixins import CEORequiredMixin


class CastingUpdateView(CEORequiredMixin, View):
    template_name = 'order/stage_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage, _ = CastingStage.objects.get_or_create(order=order, defaults={'total_quantity': order.quantity})
        form = CastingForm(instance=stage)
        # Bosqich loglari
        stage_logs = order.stage_logs.filter(stage=Order.CurrentStage.CASTING).select_related('worker', 'accepted_by').order_by('-created_at')
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_logs': stage_logs,
            'stage_name': "Quyish bo'limi",
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(CastingStage, order=order)
        form = CastingForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            # Harakat logini qo'shish (misol uchun, miqdor va ishchi)
            quantity = form.cleaned_data.get('total_quantity', 0)
            note = form.cleaned_data.get('note', '')
            from apps.order.models import OrderStageLog
            OrderStageLog.objects.create(
                order=order,
                stage=Order.CurrentStage.CASTING,
                from_department='',
                to_department='Quyish',
                quantity=quantity,
                worker=request.user,
                accepted_by=None,
                note=note,
            )
            messages.success(request, "Quyish bo'limi yangilandi va logga yozildi.")
            return redirect('order:order_detail', pk=order.pk)
        # Bosqich loglari
        stage_logs = order.stage_logs.filter(stage=Order.CurrentStage.CASTING).select_related('worker', 'accepted_by').order_by('-created_at')
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_logs': stage_logs,
            'stage_name': "Quyish bo'limi",
            'active_nav': 'orders',
        })
