from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import Order, CastingStage, OrderStageLog
from apps.order.views.mixins import CEORequiredMixin
from apps.users.models import User as CustomUser


STAGE_STATUS_FLOW = [
    CastingStage.Status.PENDING,
    CastingStage.Status.IN_PROCESS,
    CastingStage.Status.COMPLETED,
]


def _casting_stats(order):
    logs = order.stage_logs.filter(stage=Order.CurrentStage.CASTING)
    total_done = logs.aggregate(s=Sum('quantity'))['s'] or 0
    # defect: from stage record directly
    try:
        defect = order.casting.defect_quantity
    except CastingStage.DoesNotExist:
        defect = 0
    good = total_done - defect
    remaining = order.quantity - total_done
    return {
        'total_entered': total_done,
        'defect': defect,
        'good': good,
        'remaining': max(remaining, 0),
    }


class CastingUpdateView(CEORequiredMixin, View):
    template_name = 'order/casting_detail.html'

    def get(self, request, pk):
        order = get_object_or_404(
            Order.objects.select_related('created_by', 'casting'),
            pk=pk,
        )
        stage, _ = CastingStage.objects.get_or_create(
            order=order,
            defaults={'total_quantity': order.quantity},
        )
        logs = order.stage_logs.filter(
            stage=Order.CurrentStage.CASTING,
        ).select_related('worker').order_by('-created_at')
        workers = CustomUser.objects.filter(is_active=True).order_by('name')
        stats = _casting_stats(order)
        return render(request, self.template_name, {
            'order': order,
            'stage': stage,
            'logs': logs,
            'workers': workers,
            'stats': stats,
            'active_nav': 'orders',
            'status_flow': STAGE_STATUS_FLOW,
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(CastingStage, order=order)
        action = request.POST.get('action')

        # ── STATUS O'ZGARTIRISH ──
        if action == 'set_status':
            new_status = request.POST.get('status')
            allowed = {
                CastingStage.Status.PENDING: CastingStage.Status.IN_PROCESS,
                CastingStage.Status.IN_PROCESS: CastingStage.Status.COMPLETED,
            }
            if new_status == allowed.get(stage.status):
                if new_status == CastingStage.Status.IN_PROCESS and not stage.started_at:
                    stage.started_at = timezone.now()
                if new_status == CastingStage.Status.COMPLETED and not stage.finished_at:
                    stage.finished_at = timezone.now()
                    order.current_stage = Order.CurrentStage.MONTAJ
                    order.save(update_fields=['current_stage'])
                stage.status = new_status
                stage.save()
                messages.success(request, f"Status: {stage.get_status_display()}")
            else:
                messages.error(request, "Noto'g'ri status o'tishi.")
            return redirect('order:casting_edit', pk=pk)

        # ── LOG QO'SHISH ──
        if action == 'add_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan, yangi harakat qo'shib bo'lmaydi.")
                return redirect('order:casting_edit', pk=pk)
            try:
                quantity = int(request.POST.get('quantity', 0))
                defect = int(request.POST.get('defect_quantity', 0))
            except (ValueError, TypeError):
                messages.error(request, "Miqdor noto'g'ri.")
                return redirect('order:casting_edit', pk=pk)
            if quantity <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('order:casting_edit', pk=pk)
            worker_id = request.POST.get('worker_id') or None
            worker = None
            if worker_id:
                try:
                    worker = CustomUser.objects.get(pk=worker_id)
                except CustomUser.DoesNotExist:
                    pass
            note = request.POST.get('note', '').strip()
            OrderStageLog.objects.create(
                order=order,
                stage=Order.CurrentStage.CASTING,
                from_department='',
                to_department="Quyish bo'limi",
                quantity=quantity,
                worker=worker,
                note=note,
            )
            # Update defect on stage
            stage.defect_quantity = max(stage.defect_quantity, defect)
            stage.defect_quantity = defect
            if stage.status == CastingStage.Status.PENDING:
                stage.status = CastingStage.Status.IN_PROCESS
                stage.started_at = stage.started_at or timezone.now()
            stage.save()
            messages.success(request, f"{quantity} dona quyish logi qo'shildi.")
            return redirect('order:casting_edit', pk=pk)

        # ── LOG O'CHIRISH ──
        if action == 'delete_log':
            log_id = request.POST.get('log_id')
            OrderStageLog.objects.filter(pk=log_id, order=order, stage=Order.CurrentStage.CASTING).delete()
            messages.success(request, "Log o'chirildi.")
            return redirect('order:casting_edit', pk=pk)

        return redirect('order:casting_edit', pk=pk)
