from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.order.models import Order, PackagingStage
from apps.order.forms import PackagingForm
from apps.order.views.mixins import CEORequiredMixin


class PackagingUpdateView(CEORequiredMixin, View):
    template_name = 'order/stage_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage, _ = PackagingStage.objects.get_or_create(order=order, defaults={'total_quantity': order.quantity})
        form = PackagingForm(instance=stage)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_name': 'Upakovka bo\'limi',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(PackagingStage, order=order)
        form = PackagingForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Upakovka bo\'limi yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_name': 'Upakovka bo\'limi',
            'active_nav': 'orders',
        })
