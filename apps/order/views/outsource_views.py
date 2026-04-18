from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView

from apps.order.models import Order, OutsourceWork
from apps.order.forms import OutsourceForm
from apps.order.views.mixins import CEORequiredMixin


class OutsourceCreateView(CEORequiredMixin, View):
    template_name = 'order/outsource_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OutsourceForm()
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': 'Yangi tashqi ishlov',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OutsourceForm(request.POST)
        if form.is_valid():
            outsource = form.save(commit=False)
            outsource.order = order
            outsource.sent_by = request.user
            outsource.save()
            messages.success(request, 'Tashqi ishlov qo\'shildi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': 'Yangi tashqi ishlov',
            'active_nav': 'orders',
        })


class OutsourceUpdateView(CEORequiredMixin, View):
    template_name = 'order/outsource_form.html'

    def get(self, request, pk, outsource_pk):
        order = get_object_or_404(Order, pk=pk)
        outsource = get_object_or_404(OutsourceWork, pk=outsource_pk, order=order)
        form = OutsourceForm(instance=outsource)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'outsource': outsource,
            'title': f'{outsource.contractor} — tahrirlash',
            'active_nav': 'orders',
        })

    def post(self, request, pk, outsource_pk):
        order = get_object_or_404(Order, pk=pk)
        outsource = get_object_or_404(OutsourceWork, pk=outsource_pk, order=order)
        form = OutsourceForm(request.POST, instance=outsource)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tashqi ishlov yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'outsource': outsource,
            'title': f'{outsource.contractor} — tahrirlash',
            'active_nav': 'orders',
        })


class OutsourceDeleteView(CEORequiredMixin, DeleteView):
    model = OutsourceWork
    template_name = 'order/order_confirm_delete.html'
    pk_url_kwarg = 'outsource_pk'

    def get_success_url(self):
        return reverse_lazy('order:order_detail', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'orders'
        ctx['cancel_url'] = reverse_lazy('order:order_detail', kwargs={'pk': self.kwargs['pk']})
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Tashqi ishlov o\'chirildi.')
        return super().form_valid(form)
