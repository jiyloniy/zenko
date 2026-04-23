from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.order.models import Order
from apps.order.views.mixins import CastingManagerRequiredMixin


class CastingOrderListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        status_filter = request.GET.get('status', 'accepted')
        q = request.GET.get('q', '').strip()

        if status_filter not in {'accepted', 'in_process', 'ready'}:
            status_filter = 'accepted'

        qs = Order.objects.select_related('brujka', 'created_by').filter(status=status_filter)
        if q:
            qs = qs.filter(name__icontains=q)

        counts = {
            'accepted': Order.objects.filter(status='accepted').count(),
            'in_process': Order.objects.filter(status='in_process').count(),
            'ready': Order.objects.filter(status='ready').count(),
        }

        return render(request, 'casting/order_list.html', {
            'orders': qs.order_by('deadline', '-priority'),
            'status_filter': status_filter,
            'q': q,
            'counts': counts,
            'active_nav': 'orders',
        })


class CastingOrderDetailView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('brujka', 'created_by'),
            pk=pk,
        )
        return render(request, 'casting/order_detail.html', {
            'order': order,
            'active_nav': 'orders',
        })
