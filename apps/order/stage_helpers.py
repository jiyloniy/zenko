"""Shared POST handler for all department stage views."""
from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from apps.order.models import Order, OrderStageLog, StageTransfer
from apps.users.models import User


def handle_stage_post(request, pk, order, stage, action, app_name, StageModel, current_stage_val, transfer_stage_val, dept_name):
    """Generic handler for add/edit/delete log and transfer actions."""

    if action == 'set_status':
        new_status = request.POST.get('status')
        allowed = {StageModel.Status.PENDING: StageModel.Status.IN_PROCESS, StageModel.Status.IN_PROCESS: StageModel.Status.COMPLETED}
        if new_status == allowed.get(stage.status):
            if new_status == StageModel.Status.IN_PROCESS:
                stage.started_at = stage.started_at or timezone.now()
            if new_status == StageModel.Status.COMPLETED:
                stage.finished_at = stage.finished_at or timezone.now()
            stage.status = new_status
            stage.save()
            messages.success(request, f"Status: {stage.get_status_display()}")
        else:
            messages.error(request, "Noto'g'ri status o'tishi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'add_log':
        if stage.status == StageModel.Status.COMPLETED:
            messages.error(request, "Bosqich yakunlangan.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        try:
            quantity = int(request.POST.get('quantity', 0))
            defect   = int(request.POST.get('defect_quantity', 0))
        except (ValueError, TypeError):
            messages.error(request, "Miqdor noto'g'ri.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        if quantity <= 0:
            messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        total_so_far = order.stage_logs.filter(stage=current_stage_val).aggregate(s=Sum('quantity'))['s'] or 0
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
            order=order, stage=current_stage_val,
            from_department='', to_department=dept_name,
            quantity=quantity, worker=worker,
            note=request.POST.get('note', '').strip(),
        )
        stage.defect_quantity = defect
        if stage.status == StageModel.Status.PENDING:
            stage.status = StageModel.Status.IN_PROCESS
            stage.started_at = stage.started_at or timezone.now()
        stage.save()
        messages.success(request, f"{quantity} dona log qo'shildi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'edit_log':
        if stage.status == StageModel.Status.COMPLETED:
            messages.error(request, "Bosqich yakunlangan.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        log = get_object_or_404(OrderStageLog, pk=request.POST.get('log_id'), order=order, stage=current_stage_val)
        try:
            quantity = int(request.POST.get('quantity', 0))
        except (ValueError, TypeError):
            messages.error(request, "Miqdor noto'g'ri.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        if quantity <= 0:
            messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        log.quantity = quantity
        log.note = request.POST.get('note', '').strip()
        worker_id = request.POST.get('worker_id') or None
        log.worker = User.objects.get(pk=worker_id) if worker_id else None
        log.save()
        messages.success(request, "Log yangilandi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'delete_log':
        if stage.status == StageModel.Status.COMPLETED:
            messages.error(request, "Bosqich yakunlangan.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        OrderStageLog.objects.filter(pk=request.POST.get('log_id'), order=order, stage=current_stage_val).delete()
        messages.success(request, "Log o'chirildi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'send_transfer':
        if stage.status != StageModel.Status.COMPLETED:
            messages.error(request, "Avval bosqichni yakunlang.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        to_stage = request.POST.get('to_stage', '')
        if to_stage not in dict(StageTransfer.Stage.choices):
            messages.error(request, "Noto'g'ri bo'lim.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        try:
            qty = int(request.POST.get('transfer_quantity', 0))
        except (ValueError, TypeError):
            qty = 0
        if qty <= 0:
            messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        transfer = StageTransfer.objects.create(
            order=order, from_stage=transfer_stage_val, to_stage=to_stage,
            sent_quantity=qty, sent_by=request.user,
            note=request.POST.get('transfer_note', '').strip(),
        )
        order.current_stage = to_stage
        order.save(update_fields=['current_stage'])
        messages.success(request, f"{qty} dona {transfer.get_to_stage_display()}ga yuborildi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'edit_transfer':
        transfer = get_object_or_404(
            StageTransfer, pk=request.POST.get('transfer_id'), order=order,
            from_stage=transfer_stage_val, status=StageTransfer.Status.PENDING, sent_by=request.user,
        )
        try:
            qty = int(request.POST.get('sent_quantity', 0))
        except (ValueError, TypeError):
            qty = 0
        if qty <= 0:
            messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
            return redirect(f'{app_name}:order_detail', pk=pk)
        transfer.sent_quantity = qty
        transfer.note = request.POST.get('transfer_note', '').strip()
        transfer.save()
        messages.success(request, "Transfer yangilandi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'delete_transfer':
        transfer = get_object_or_404(
            StageTransfer, pk=request.POST.get('transfer_id'), order=order,
            from_stage=transfer_stage_val, status=StageTransfer.Status.PENDING, sent_by=request.user,
        )
        order.current_stage = transfer_stage_val
        order.save(update_fields=['current_stage'])
        transfer.delete()
        messages.success(request, "Transfer bekor qilindi.")
        return redirect(f'{app_name}:order_detail', pk=pk)

    if action == 'accept_transfer':
        transfer = get_object_or_404(
            StageTransfer, pk=request.POST.get('transfer_id'),
            order=order, to_stage=transfer_stage_val, status=StageTransfer.Status.PENDING,
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
        return redirect(f'{app_name}:order_detail', pk=pk)

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
        return redirect(f'{app_name}:order_detail', pk=pk)

    return redirect(f'{app_name}:order_detail', pk=pk)
