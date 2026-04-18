from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.order.models import Order, WarehouseStage
from apps.order.forms import WarehouseForm
from apps.order.views.mixins import CEORequiredMixin


class WarehouseUpdateView(CEORequiredMixin, View):
    template_name = 'order/stage_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage, _ = WarehouseStage.objects.get_or_create(order=order)
        form = WarehouseForm(instance=stage)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_name': 'Ombor',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(WarehouseStage, order=order)
        form = WarehouseForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ombor yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_name': 'Ombor',
            'active_nav': 'orders',
        })
