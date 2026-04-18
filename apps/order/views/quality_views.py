from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView

from apps.order.models import Order, QualityControl
from apps.order.forms import QualityControlForm
from apps.order.views.mixins import CEORequiredMixin


class QualityCreateView(CEORequiredMixin, View):
    template_name = 'order/quality_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = QualityControlForm()
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': 'Sifat nazorati',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = QualityControlForm(request.POST)
        if form.is_valid():
            qc = form.save(commit=False)
            qc.order = order
            qc.save()
            messages.success(request, 'Sifat nazorati qo\'shildi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': 'Sifat nazorati',
            'active_nav': 'orders',
        })


class QualityUpdateView(CEORequiredMixin, View):
    template_name = 'order/quality_form.html'

    def get(self, request, pk, qc_pk):
        order = get_object_or_404(Order, pk=pk)
        qc = get_object_or_404(QualityControl, pk=qc_pk, order=order)
        form = QualityControlForm(instance=qc)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'qc': qc,
            'title': 'Sifat nazorati — tahrirlash',
            'active_nav': 'orders',
        })

    def post(self, request, pk, qc_pk):
        order = get_object_or_404(Order, pk=pk)
        qc = get_object_or_404(QualityControl, pk=qc_pk, order=order)
        form = QualityControlForm(request.POST, instance=qc)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sifat nazorati yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'qc': qc,
            'title': 'Sifat nazorati — tahrirlash',
            'active_nav': 'orders',
        })


class QualityDeleteView(CEORequiredMixin, DeleteView):
    model = QualityControl
    template_name = 'order/order_confirm_delete.html'
    pk_url_kwarg = 'qc_pk'

    def get_success_url(self):
        return reverse_lazy('order:order_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'orders'
        ctx['cancel_url'] = reverse_lazy('order:order_detail', kwargs={'pk': self.kwargs['pk']})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Sifat nazorati o\'chirildi.')
        return super().form_valid(form)
