from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.shortcuts import render
from django.contrib import messages

from apps.order.models import Order
from apps.order.views.mixins import CastingManagerRequiredMixin


class QuyishPanelView(CastingManagerRequiredMixin, View):
    template_name = 'order/quyish_panel.html'

    def get(self, request):
        status_filter = request.GET.get('status', 'accepted')
        q = request.GET.get('q', '').strip()

        base_qs = Order.objects.select_related('brujka', 'created_by')

        accepted_qs = base_qs.filter(status=Order.Status.ACCEPTED)
        in_process_qs = base_qs.filter(status=Order.Status.IN_PROCESS)
        ready_qs = base_qs.filter(status=Order.Status.READY)

        if status_filter in ('accepted', 'in_process', 'ready'):
            filtered_qs = base_qs.filter(status=status_filter)
        else:
            filtered_qs = base_qs.filter(
                status__in=[Order.Status.ACCEPTED, Order.Status.IN_PROCESS, Order.Status.READY]
            )

        if q:
            filtered_qs = filtered_qs.filter(name__icontains=q)

        return render(request, self.template_name, {
            'orders': filtered_qs.order_by('deadline', '-priority'),
            'accepted_count': accepted_qs.count(),
            'in_process_count': in_process_qs.count(),
            'ready_count': ready_qs.count(),
            'status_filter': status_filter,
            'q': q,
            'active_nav': 'quyish',
            'Status': Order.Status,
        })

    def post(self, request):
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('new_status')
        order = get_object_or_404(Order, pk=order_id)
        if new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f'"{order.name}" holati yangilandi.')
        return redirect(f"{request.path}?status={request.POST.get('back_status', 'accepted')}&q={request.POST.get('back_q', '')}")
