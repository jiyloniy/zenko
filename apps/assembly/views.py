from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import AssemblyStage, Order, StageTransfer
from apps.order.stage_helpers import handle_stage_post
from apps.users.models import User

ASSEMBLY_ROLES = {'ASSEMBLYMANAGER', 'CEO'}


class AssemblyRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = getattr(request.user, 'role', None)
        role_name = role.name if role else ''
        if not (request.user.is_superuser or role_name in ASSEMBLY_ROLES):
            messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


def _assembly_stats(order):
    logs = order.stage_logs.filter(stage=Order.CurrentStage.MONTAJ)
    total_done = logs.aggregate(s=Sum('quantity'))['s'] or 0
    try:
        defect = order.assembly.defect_quantity
    except AssemblyStage.DoesNotExist:
        defect = 0
    return {'total_entered': total_done, 'defect': defect, 'good': max(total_done - defect, 0), 'remaining': max(order.quantity - total_done, 0)}


class AssemblyDashboardView(AssemblyRequiredMixin, View):
    def get(self, request):
        all_orders = Order.objects.filter(Q(current_stage='montaj') | Q(assembly__isnull=False)).distinct()
        today = timezone.now().date()
        pending_transfers = StageTransfer.objects.filter(to_stage=StageTransfer.Stage.MONTAJ, status=StageTransfer.Status.PENDING).select_related('order', 'sent_by').order_by('-sent_at')
        return render(request, 'assembly/dashboard.html', {
            'total': all_orders.count(), 'pending': all_orders.filter(assembly__status='pending').count(),
            'in_process': all_orders.filter(assembly__status='in_process').count(), 'completed': all_orders.filter(assembly__status='completed').count(),
            'overdue': all_orders.filter(deadline__lt=today).exclude(status__in=['delivered', 'cancelled']).count(),
            'pending_transfers': pending_transfers, 'active_nav': 'dashboard',
        })


class AssemblyOrderListView(AssemblyRequiredMixin, View):
    def get(self, request):
        qs = Order.objects.filter(Q(current_stage='montaj') | Q(assembly__isnull=False)).distinct().select_related('assembly').order_by('-created_at')
        status_filter = request.GET.get('status', '')
        q = request.GET.get('q', '')
        if status_filter:
            qs = qs.filter(assembly__status=status_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q))
        return render(request, 'assembly/order_list.html', {'orders': qs, 'current_status': status_filter, 'q': q, 'stage_statuses': AssemblyStage.Status.choices, 'active_nav': 'orders'})


class AssemblyOrderDetailView(AssemblyRequiredMixin, View):
    template_name = 'assembly/order_detail.html'

    def _ctx(self, pk):
        order = get_object_or_404(Order.objects.select_related('created_by', 'assembly'), pk=pk)
        stage, _ = AssemblyStage.objects.get_or_create(order=order, defaults={'total_quantity': order.quantity})
        logs = order.stage_logs.filter(stage=Order.CurrentStage.MONTAJ).select_related('worker').order_by('-created_at')
        transfers = order.transfers.filter(from_stage=StageTransfer.Stage.MONTAJ).select_related('sent_by', 'accepted_by').order_by('-sent_at')
        incoming = order.transfers.filter(to_stage=StageTransfer.Stage.MONTAJ, status=StageTransfer.Status.PENDING).select_related('sent_by').order_by('-sent_at')
        return {
            'order': order, 'stage': stage, 'logs': logs, 'transfers': transfers, 'incoming': incoming,
            'workers': User.objects.filter(is_active=True).order_by('name'),
            'stats': _assembly_stats(order), 'active_nav': 'orders',
            'next_stages': [(StageTransfer.Stage.PACKAGING, "Upakovka bo'limi")],
        }

    def get(self, request, pk):
        return render(request, self.template_name, self._ctx(pk))

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(AssemblyStage, order=order)
        return handle_stage_post(request, pk, order, stage, request.POST.get('action'), 'assembly', AssemblyStage, Order.CurrentStage.MONTAJ, StageTransfer.Stage.MONTAJ, "Montaj bo'limi")
