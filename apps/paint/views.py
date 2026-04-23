from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import PaintStage, Order, StageTransfer
from apps.order.stage_helpers import handle_stage_post
from apps.users.models import User

PAINT_ROLES = {'PAINTMANAGER', 'CEO'}


class PaintRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = getattr(request.user, 'role', None)
        role_name = role.name if role else ''
        if not (request.user.is_superuser or role_name in PAINT_ROLES):
            messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


def _paint_stats(order):
    from django.db.models import Sum
    logs = order.stage_logs.filter(stage=Order.CurrentStage.PAINT)
    total_done = logs.aggregate(s=Sum('quantity'))['s'] or 0
    try:
        defect = order.paint.defect_quantity
    except PaintStage.DoesNotExist:
        defect = 0
    return {'total_entered': total_done, 'defect': defect, 'good': max(total_done - defect, 0), 'remaining': max(order.quantity - total_done, 0)}


class PaintDashboardView(PaintRequiredMixin, View):
    def get(self, request):
        all_orders = Order.objects.filter(Q(current_stage='paint') | Q(paint__isnull=False)).distinct()
        today = timezone.now().date()
        pending_transfers = StageTransfer.objects.filter(to_stage=StageTransfer.Stage.PAINT, status=StageTransfer.Status.PENDING).select_related('order', 'sent_by').order_by('-sent_at')
        return render(request, 'paint/dashboard.html', {
            'total': all_orders.count(), 'pending': all_orders.filter(paint__status='pending').count(),
            'in_process': all_orders.filter(paint__status='in_process').count(), 'completed': all_orders.filter(paint__status='completed').count(),
            'overdue': all_orders.filter(deadline__lt=today).exclude(status__in=['delivered', 'cancelled']).count(),
            'pending_transfers': pending_transfers, 'active_nav': 'dashboard',
        })


class PaintOrderListView(PaintRequiredMixin, View):
    def get(self, request):
        qs = Order.objects.filter(Q(current_stage='paint') | Q(paint__isnull=False)).distinct().select_related('paint').order_by('-created_at')
        status_filter = request.GET.get('status', '')
        q = request.GET.get('q', '')
        if status_filter:
            qs = qs.filter(paint__status=status_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q))
        return render(request, 'paint/order_list.html', {'orders': qs, 'current_status': status_filter, 'q': q, 'stage_statuses': PaintStage.Status.choices, 'active_nav': 'orders'})


class PaintOrderDetailView(PaintRequiredMixin, View):
    template_name = 'paint/order_detail.html'

    def _ctx(self, pk):
        order = get_object_or_404(Order.objects.select_related('created_by', 'paint'), pk=pk)
        stage, _ = PaintStage.objects.get_or_create(order=order, defaults={'total_quantity': order.quantity})
        logs = order.stage_logs.filter(stage=Order.CurrentStage.PAINT).select_related('worker').order_by('-created_at')
        transfers = order.transfers.filter(from_stage=StageTransfer.Stage.PAINT).select_related('sent_by', 'accepted_by').order_by('-sent_at')
        incoming = order.transfers.filter(to_stage=StageTransfer.Stage.PAINT, status=StageTransfer.Status.PENDING).select_related('sent_by').order_by('-sent_at')
        return {
            'order': order, 'stage': stage, 'logs': logs, 'transfers': transfers, 'incoming': incoming,
            'workers': User.objects.filter(is_active=True).order_by('name'),
            'stats': _paint_stats(order), 'active_nav': 'orders',
            'next_stages': [(StageTransfer.Stage.PACKAGING, "Upakovka bo'limi"), (StageTransfer.Stage.STONE, "Tosh qadash bo'limi"), (StageTransfer.Stage.MONTAJ, "Montaj bo'limi")],
        }

    def get(self, request, pk):
        return render(request, self.template_name, self._ctx(pk))

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(PaintStage, order=order)
        return handle_stage_post(request, pk, order, stage, request.POST.get('action'), 'paint', PaintStage, Order.CurrentStage.PAINT, StageTransfer.Stage.PAINT, "Bo'yash bo'limi")
