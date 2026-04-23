from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, DeleteView
from django.views.generic.edit import CreateView, UpdateView

from apps.order.models import Order
from apps.order.forms import OrderForm
from apps.order.views.mixins import CEORequiredMixin


class OrderListView(CEORequiredMixin, ListView):
    model = Order
    template_name = 'order/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20

    def get_queryset(self):
        qs = Order.objects.select_related('created_by')
        status = self.request.GET.get('status')
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'orders'
        ctx['statuses'] = Order.Status.choices
        ctx['current_status'] = self.request.GET.get('status', '')
        ctx['q'] = self.request.GET.get('q', '')
        ctx['total'] = Order.objects.count()
        ctx['new_count'] = Order.objects.filter(status=Order.Status.NEW).count()
        ctx['in_process_count'] = Order.objects.filter(status=Order.Status.IN_PROCESS).count()
        ctx['ready_count'] = Order.objects.filter(status=Order.Status.READY).count()
        return ctx


class OrderCreateView(CEORequiredMixin, View):
    template_name = 'order/order_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': OrderForm(),
            'title': 'Yangi buyurtma',
            'active_nav': 'orders',
        })

    def post(self, request):
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            if not order.name.strip() or '#XXXX' in order.name:
                brujka = order.brujka
                bname = brujka.name if brujka else 'Buyurtma'
                color = brujka.color if brujka else ''
                date_str = order.deadline.strftime('%d.%m.%Y') if order.deadline else ''
                order.save()  # order_number generate bo'lishi uchun
                parts = [bname]
                if color:
                    parts.append(color)
                if date_str:
                    parts.append(date_str)
                order.name = f'#BRUJ — {order.order_number} — ' + ' — '.join(parts)
                order.save(update_fields=['name'])
                messages.success(request, f'"{order.name}" buyurtmasi yaratildi.')
                return redirect('order:order_detail', pk=order.pk)
            order.save()
            messages.success(request, f'"{order.name}" buyurtmasi yaratildi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'title': 'Yangi buyurtma',
            'active_nav': 'orders',
        })


class OrderUpdateView(CEORequiredMixin, View):
    template_name = 'order/order_form.html'

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        return render(request, self.template_name, {
            'form': OrderForm(instance=order),
            'order': order,
            'title': f'{order.name} — tahrirlash',
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{order.name}" yangilandi.')
            return redirect('order:order_detail', pk=order.pk)
        return render(request, self.template_name, {
            'form': form,
            'order': order,
            'title': f'{order.name} — tahrirlash',
            'active_nav': 'orders',
        })


class OrderDeleteView(CEORequiredMixin, DeleteView):
    model = Order
    template_name = 'order/order_confirm_delete.html'
    success_url = reverse_lazy('order:order_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'orders'
        ctx['cancel_url'] = reverse_lazy('order:order_list')
        return ctx

    def form_valid(self, form):
        messages.success(self.request, f'"{self.object.name}" o\'chirildi.')
        return super().form_valid(form)


class OrderDetailView(CEORequiredMixin, View):
    template_name = 'order/order_detail.html'

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('created_by'),
            pk=pk,
        )
        return render(request, self.template_name, {
            'order': order,
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        set_status = request.POST.get('set_status')
        if set_status and set_status in dict(Order.Status.choices):
            order.status = set_status
            order.save(update_fields=['status'])
            messages.success(request, 'Buyurtma holati yangilandi!')
        return redirect(request.path)
