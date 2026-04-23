from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import SprayStage, Order, OrderStageLog, StageTransfer
from apps.users.models import User

SPRAY_ROLES = {'SPRAYMANAGER', 'CEO'}


class SprayRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = getattr(request.user, 'role', None)
        role_name = role.name if role else ''
        if not (request.user.is_superuser or role_name in SPRAY_ROLES):
            messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


def _spray_stats(order):
    logs = order.stage_logs.filter(stage=Order.CurrentStage.SPRAY)
    total_done = logs.aggregate(s=Sum('quantity'))['s'] or 0
    try:
        defect = order.spray.defect_quantity
    except SprayStage.DoesNotExist:
        defect = 0
    return {
        'total_entered': total_done,
        'defect': defect,
        'good': max(total_done - defect, 0),
        'remaining': max(order.quantity - total_done, 0),
    }


class SprayDashboardView(SprayRequiredMixin, View):
    def get(self, request):
        all_orders = Order.objects.filter(
            Q(current_stage='spray') | Q(spray__isnull=False)
        ).distinct()

        today = timezone.now().date()
        pending_transfers = StageTransfer.objects.filter(
            to_stage=StageTransfer.Stage.SPRAY,
            status=StageTransfer.Status.PENDING,
        ).select_related('order', 'sent_by').order_by('-sent_at')

        return render(request, 'spray/dashboard.html', {
            'total':      all_orders.count(),
            'pending':    all_orders.filter(spray__status='pending').count(),
            'in_process': all_orders.filter(spray__status='in_process').count(),
            'completed':  all_orders.filter(spray__status='completed').count(),
            'overdue':    all_orders.filter(deadline__lt=today).exclude(status__in=['delivered', 'cancelled']).count(),
            'pending_transfers': pending_transfers,
            'active_nav': 'dashboard',
        })


class SprayOrderListView(SprayRequiredMixin, View):
    def get(self, request):
        qs = Order.objects.filter(
            Q(current_stage='spray') | Q(spray__isnull=False)
        ).distinct().select_related('spray').order_by('-created_at')

        status_filter = request.GET.get('status', '')
        q = request.GET.get('q', '')
        if status_filter:
            qs = qs.filter(spray__status=status_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q))

        return render(request, 'spray/order_list.html', {
            'orders': qs,
            'current_status': status_filter,
            'q': q,
            'stage_statuses': SprayStage.Status.choices,
            'active_nav': 'orders',
        })


class SprayOrderDetailView(SprayRequiredMixin, View):
    template_name = 'spray/order_detail.html'

    def _ctx(self, pk):
        order = get_object_or_404(Order.objects.select_related('created_by', 'spray'), pk=pk)
        stage, _ = SprayStage.objects.get_or_create(order=order, defaults={'total_quantity': order.quantity})
        logs = order.stage_logs.filter(stage=Order.CurrentStage.SPRAY).select_related('worker').order_by('-created_at')
        transfers = order.transfers.filter(from_stage=StageTransfer.Stage.SPRAY).select_related('sent_by', 'accepted_by').order_by('-sent_at')
        incoming = order.transfers.filter(to_stage=StageTransfer.Stage.SPRAY, status=StageTransfer.Status.PENDING).select_related('sent_by').order_by('-sent_at')
        stats = _spray_stats(order)
        return {
            'order': order, 'stage': stage, 'logs': logs,
            'transfers': transfers, 'incoming': incoming,
            'workers': User.objects.filter(is_active=True).order_by('name'),
            'stats': stats, 'active_nav': 'orders',
            'next_stages': [
                (StageTransfer.Stage.PAINT,     "Bo'yash bo'limi"),
                (StageTransfer.Stage.PACKAGING, "Upakovka bo'limi"),
            ],
        }

    def get(self, request, pk):
        return render(request, self.template_name, self._ctx(pk))

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(SprayStage, order=order)
        action = request.POST.get('action')

        if action == 'set_status':
            new_status = request.POST.get('status')
            allowed = {SprayStage.Status.PENDING: SprayStage.Status.IN_PROCESS, SprayStage.Status.IN_PROCESS: SprayStage.Status.COMPLETED}
            if new_status == allowed.get(stage.status):
                if new_status == SprayStage.Status.IN_PROCESS:
                    stage.started_at = stage.started_at or timezone.now()
                if new_status == SprayStage.Status.COMPLETED:
                    stage.finished_at = stage.finished_at or timezone.now()
                stage.status = new_status
                stage.save()
                messages.success(request, f"Status: {stage.get_status_display()}")
            else:
                messages.error(request, "Noto'g'ri status o'tishi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'add_log':
            if stage.status == SprayStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('spray:order_detail', pk=pk)
            try:
                quantity = int(request.POST.get('quantity', 0))
                defect   = int(request.POST.get('defect_quantity', 0))
            except (ValueError, TypeError):
                messages.error(request, "Miqdor noto'g'ri.")
                return redirect('spray:order_detail', pk=pk)
            if quantity <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('spray:order_detail', pk=pk)
            total_so_far = order.stage_logs.filter(stage=Order.CurrentStage.SPRAY).aggregate(s=Sum('quantity'))['s'] or 0
            if total_so_far + quantity > order.quantity:
                messages.warning(request, f"Ogohlantirish: Jami ({total_so_far + quantity}) buyurtma miqdoridan ({order.quantity}) oshib ketadi!")
            worker_id = request.POST.get('worker_id') or None
            worker = None
            if worker_id:
                try:
                    worker = User.objects.get(pk=worker_id)
                except User.DoesNotExist:
                    pass
            OrderStageLog.objects.create(
                order=order, stage=Order.CurrentStage.SPRAY,
                from_department='', to_department="Sepish bo'limi",
                quantity=quantity, worker=worker,
                note=request.POST.get('note', '').strip(),
            )
            stage.defect_quantity = defect
            if stage.status == SprayStage.Status.PENDING:
                stage.status = SprayStage.Status.IN_PROCESS
                stage.started_at = stage.started_at or timezone.now()
            stage.save()
            messages.success(request, f"{quantity} dona log qo'shildi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'edit_log':
            if stage.status == SprayStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('spray:order_detail', pk=pk)
            log = get_object_or_404(OrderStageLog, pk=request.POST.get('log_id'), order=order, stage=Order.CurrentStage.SPRAY)
            try:
                quantity = int(request.POST.get('quantity', 0))
            except (ValueError, TypeError):
                messages.error(request, "Miqdor noto'g'ri.")
                return redirect('spray:order_detail', pk=pk)
            if quantity <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('spray:order_detail', pk=pk)
            log.quantity = quantity
            log.note = request.POST.get('note', '').strip()
            worker_id = request.POST.get('worker_id') or None
            log.worker = User.objects.get(pk=worker_id) if worker_id else None
            log.save()
            messages.success(request, "Log yangilandi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'delete_log':
            if stage.status == SprayStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('spray:order_detail', pk=pk)
            OrderStageLog.objects.filter(pk=request.POST.get('log_id'), order=order, stage=Order.CurrentStage.SPRAY).delete()
            messages.success(request, "Log o'chirildi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'send_transfer':
            if stage.status != SprayStage.Status.COMPLETED:
                messages.error(request, "Avval bosqichni yakunlang.")
                return redirect('spray:order_detail', pk=pk)
            to_stage = request.POST.get('to_stage', '')
            if to_stage not in dict(StageTransfer.Stage.choices):
                messages.error(request, "Noto'g'ri bo'lim.")
                return redirect('spray:order_detail', pk=pk)
            try:
                qty = int(request.POST.get('transfer_quantity', 0))
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('spray:order_detail', pk=pk)
            transfer = StageTransfer.objects.create(
                order=order, from_stage=StageTransfer.Stage.SPRAY, to_stage=to_stage,
                sent_quantity=qty, sent_by=request.user,
                note=request.POST.get('transfer_note', '').strip(),
            )
            order.current_stage = to_stage
            order.save(update_fields=['current_stage'])
            messages.success(request, f"{qty} dona {transfer.get_to_stage_display()}ga yuborildi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'edit_transfer':
            transfer = get_object_or_404(
                StageTransfer, pk=request.POST.get('transfer_id'), order=order,
                from_stage=StageTransfer.Stage.SPRAY, status=StageTransfer.Status.PENDING, sent_by=request.user,
            )
            try:
                qty = int(request.POST.get('sent_quantity', 0))
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('spray:order_detail', pk=pk)
            transfer.sent_quantity = qty
            transfer.note = request.POST.get('transfer_note', '').strip()
            transfer.save()
            messages.success(request, "Transfer yangilandi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'delete_transfer':
            transfer = get_object_or_404(
                StageTransfer, pk=request.POST.get('transfer_id'), order=order,
                from_stage=StageTransfer.Stage.SPRAY, status=StageTransfer.Status.PENDING, sent_by=request.user,
            )
            order.current_stage = StageTransfer.Stage.SPRAY
            order.save(update_fields=['current_stage'])
            transfer.delete()
            messages.success(request, "Transfer bekor qilindi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'accept_transfer':
            transfer = get_object_or_404(
                StageTransfer, pk=request.POST.get('transfer_id'),
                order=order, to_stage=StageTransfer.Stage.SPRAY, status=StageTransfer.Status.PENDING,
            )
            try:
                accepted_qty = int(request.POST.get('accepted_quantity', 0))
            except (ValueError, TypeError):
                accepted_qty = 0
            transfer.accepted_quantity = accepted_qty
            transfer.rejected_quantity = max(transfer.sent_quantity - accepted_qty, 0)
            transfer.accepted_by = request.user
            transfer.accept_note = request.POST.get('accept_note', '').strip()
            transfer.accepted_at = timezone.now()
            transfer.status = StageTransfer.Status.ACCEPTED
            transfer.save()
            messages.success(request, f"{accepted_qty} dona qabul qilindi.")
            return redirect('spray:order_detail', pk=pk)

        if action == 'reject_transfer':
            transfer = get_object_or_404(
                StageTransfer, pk=request.POST.get('transfer_id'), order=order, status=StageTransfer.Status.PENDING,
            )
            transfer.status = StageTransfer.Status.REJECTED
            transfer.accepted_by = request.user
            transfer.accept_note = request.POST.get('accept_note', '').strip()
            transfer.accepted_at = timezone.now()
            transfer.save()
            messages.warning(request, "Transfer rad etildi.")
            return redirect('spray:order_detail', pk=pk)

        return redirect('spray:order_detail', pk=pk)
