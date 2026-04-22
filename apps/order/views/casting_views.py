from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import Order, CastingStage, OrderStageLog, StageTransfer
from apps.order.views.mixins import CEORequiredMixin
from apps.users.models import User


STAGE_STATUS_FLOW = [
    CastingStage.Status.PENDING,
    CastingStage.Status.IN_PROCESS,
    CastingStage.Status.COMPLETED,
]


def _casting_stats(order):
    logs = order.stage_logs.filter(stage=Order.CurrentStage.CASTING)
    total_done = logs.aggregate(s=Sum('quantity'))['s'] or 0
    try:
        defect = order.casting.defect_quantity
    except CastingStage.DoesNotExist:
        defect = 0
    good = max(total_done - defect, 0)
    remaining = max(order.quantity - total_done, 0)
    return {
        'total_entered': total_done,
        'defect': defect,
        'good': good,
        'remaining': remaining,
    }


class CastingUpdateView(CEORequiredMixin, View):
    template_name = 'order/casting_detail.html'

    def _get_context(self, request, pk):
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
        transfers = order.transfers.filter(
            from_stage=StageTransfer.Stage.CASTING,
        ).select_related('sent_by', 'accepted_by').order_by('-sent_at')
        incoming = order.transfers.filter(
            to_stage=StageTransfer.Stage.CASTING,
            status=StageTransfer.Status.PENDING,
        ).select_related('sent_by').order_by('-sent_at')
        workers = User.objects.filter(is_active=True).order_by('name')
        stats = _casting_stats(order)
        return {
            'order': order,
            'stage': stage,
            'logs': logs,
            'transfers': transfers,
            'incoming': incoming,
            'workers': workers,
            'stats': stats,
            'active_nav': 'orders',
            'next_stages': [
                (StageTransfer.Stage.MONTAJ, "Montaj bo'limi"),
                (StageTransfer.Stage.HANGING, "Ilish bo'limi"),
                (StageTransfer.Stage.STONE_SETTING, "Tosh qadash bo'limi"),
                (StageTransfer.Stage.PACKAGING, "Upakovka bo'limi"),
                (StageTransfer.Stage.WAREHOUSE, "Ombor"),
            ],
        }

    def get(self, request, pk):
        ctx = self._get_context(request, pk)
        return render(request, self.template_name, ctx)

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
                if new_status == CastingStage.Status.IN_PROCESS:
                    stage.started_at = stage.started_at or timezone.now()
                if new_status == CastingStage.Status.COMPLETED:
                    stage.finished_at = stage.finished_at or timezone.now()
                stage.status = new_status
                stage.save()
                messages.success(request, f"Status: {stage.get_status_display()}")
            else:
                messages.error(request, "Noto'g'ri status o'tishi.")
            return redirect('order:casting_edit', pk=pk)

        # ── LOG QO'SHISH (faqat COMPLETED bo'lmasa) ──
        if action == 'add_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan, yangi log qo'shib bo'lmaydi.")
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
                    worker = User.objects.get(pk=worker_id)
                except User.DoesNotExist:
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
            stage.defect_quantity = defect
            if stage.status == CastingStage.Status.PENDING:
                stage.status = CastingStage.Status.IN_PROCESS
                stage.started_at = stage.started_at or timezone.now()
            stage.save()
            messages.success(request, f"{quantity} dona log qo'shildi.")
            return redirect('order:casting_edit', pk=pk)

        # ── LOG O'CHIRISH ──
        if action == 'delete_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('order:casting_edit', pk=pk)
            log_id = request.POST.get('log_id')
            OrderStageLog.objects.filter(
                pk=log_id, order=order, stage=Order.CurrentStage.CASTING,
            ).delete()
            messages.success(request, "Log o'chirildi.")
            return redirect('order:casting_edit', pk=pk)

        # ── TRANSFER YUBORISH ──
        if action == 'send_transfer':
            if stage.status != CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlanmagan. Avval 'Yakunlash' tugmasini bosing.")
                return redirect('order:casting_edit', pk=pk)
            to_stage = request.POST.get('to_stage', '')
            if to_stage not in dict(StageTransfer.Stage.choices):
                messages.error(request, "Noto'g'ri bo'lim tanlandi.")
                return redirect('order:casting_edit', pk=pk)
            try:
                qty = int(request.POST.get('transfer_quantity', 0))
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('order:casting_edit', pk=pk)
            note = request.POST.get('transfer_note', '').strip()
            transfer = StageTransfer.objects.create(
                order=order,
                from_stage=StageTransfer.Stage.CASTING,
                to_stage=to_stage,
                sent_quantity=qty,
                sent_by=request.user,
                note=note,
            )
            # Update order current_stage to next
            order.current_stage = to_stage
            order.save(update_fields=['current_stage'])
            messages.success(
                request,
                f"{qty} dona {transfer.get_to_stage_display()}ga yuborildi. Qabul kutilmoqda."
            )
            return redirect('order:casting_edit', pk=pk)

        # ── TRANSFER QABUL QILISH ──
        if action == 'accept_transfer':
            transfer_id = request.POST.get('transfer_id')
            transfer = get_object_or_404(
                StageTransfer, pk=transfer_id, order=order,
                to_stage=StageTransfer.Stage.CASTING,
                status=StageTransfer.Status.PENDING,
            )
            try:
                accepted_qty = int(request.POST.get('accepted_quantity', 0))
            except (ValueError, TypeError):
                accepted_qty = 0
            rejected_qty = max(transfer.sent_quantity - accepted_qty, 0)
            accept_note = request.POST.get('accept_note', '').strip()
            transfer.accepted_quantity = accepted_qty
            transfer.rejected_quantity = rejected_qty
            transfer.accepted_by = request.user
            transfer.accept_note = accept_note
            transfer.accepted_at = timezone.now()
            transfer.status = StageTransfer.Status.ACCEPTED
            transfer.save()
            messages.success(request, f"{accepted_qty} dona qabul qilindi.")
            return redirect('order:casting_edit', pk=pk)

        # ── TRANSFER RAD ETISH ──
        if action == 'reject_transfer':
            transfer_id = request.POST.get('transfer_id')
            transfer = get_object_or_404(
                StageTransfer, pk=transfer_id, order=order,
                status=StageTransfer.Status.PENDING,
            )
            accept_note = request.POST.get('accept_note', '').strip()
            transfer.status = StageTransfer.Status.REJECTED
            transfer.accepted_by = request.user
            transfer.accept_note = accept_note
            transfer.accepted_at = timezone.now()
            transfer.save()
            messages.warning(request, "Transfer rad etildi.")
            return redirect('order:casting_edit', pk=pk)

        return redirect('order:casting_edit', pk=pk)
