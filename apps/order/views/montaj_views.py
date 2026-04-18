from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.order.models import Order, MontajStage
from apps.order.forms import MontajForm
from apps.order.views.mixins import CEORequiredMixin


class MontajUpdateView(CEORequiredMixin, View):
    template_name = 'order/stage_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage, _ = MontajStage.objects.get_or_create(order=order, defaults={'total_quantity': order.quantity})
        form = MontajForm(instance=stage)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_name': 'Montaj bo\'limi',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(MontajStage, order=order)
        form = MontajForm(request.POST, instance=stage)
        if form.is_valid():
            form.save()
            messages.success(request, 'Montaj bo\'limi yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'stage': stage,
            'stage_name': 'Montaj bo\'limi',
            'active_nav': 'orders',
        })
