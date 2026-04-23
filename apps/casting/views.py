from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import CastingStage, Order, OrderStageLog, Stanok, StanokLog, StageTransfer
from apps.users.models import User


CASTING_ROLES = {'CASTINGMANAGER', 'CEO'}


class CastingRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = getattr(request.user, 'role', None)
        role_name = role.name if role else ''
        if not (request.user.is_superuser or role_name in CASTING_ROLES):
            messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


def _casting_stats(order):
    # Yarim tayyor (StanokLog) statistikasi
    stanok_agg    = order.stanok_logs.aggregate(total=Sum('quantity'), defect=Sum('defect'))
    stanok_total  = stanok_agg['total'] or 0
    stanok_defect = stanok_agg['defect'] or 0
    stanok_good   = max(stanok_total - stanok_defect, 0)

    # Tayyor mahsulot (OrderStageLog casting) statistikasi — defect maydoni yo'q
    log_total = order.stage_logs.filter(stage=Order.CurrentStage.CASTING).aggregate(s=Sum('quantity'))['s'] or 0

    total_done = stanok_total + log_total

    return {
        'total_entered': total_done,
        # yarim tayyor
        'stanok_total':  stanok_total,
        'stanok_defect': stanok_defect,
        'stanok_good':   stanok_good,
        # tayyor (casting logs — defectsiz hisoblanadi)
        'log_total': log_total,
        # umumiy
        'defect':    stanok_defect,
        'good':      log_total + stanok_good,
        'remaining': max(order.quantity - log_total, 0),
    }


class CastingDashboardView(CastingRequiredMixin, View):
    def get(self, request):
        all_orders = Order.objects.filter(
            Q(current_stage='casting') | Q(casting__isnull=False)
        ).distinct()

        today = timezone.now().date()
        pending_transfers = StageTransfer.objects.filter(
            to_stage=StageTransfer.Stage.CASTING,
            status=StageTransfer.Status.PENDING,
        ).select_related('order', 'sent_by').order_by('-sent_at')

        recent_logs = OrderStageLog.objects.filter(
            stage=Order.CurrentStage.CASTING
        ).select_related('order', 'worker').order_by('-created_at')[:10]

        return render(request, 'casting/dashboard.html', {
            'total':      all_orders.count(),
            'pending':    all_orders.filter(casting__status='pending').count(),
            'in_process': all_orders.filter(casting__status='in_process').count(),
            'completed':  all_orders.filter(casting__status='completed').count(),
            'overdue':    all_orders.filter(deadline__lt=today).exclude(
                              status__in=['delivered', 'cancelled']).count(),
            'pending_transfers': pending_transfers,
            'recent_logs': recent_logs,
            'active_nav': 'dashboard',
        })


class CastingOrderListView(CastingRequiredMixin, View):
    def get(self, request):
        qs = Order.objects.filter(
            Q(current_stage='casting') | Q(casting__isnull=False)
        ).distinct().select_related('casting').order_by('-created_at')

        status_filter = request.GET.get('status', '')
        q = request.GET.get('q', '')
        if status_filter:
            qs = qs.filter(casting__status=status_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q))

        return render(request, 'casting/order_list.html', {
            'orders': qs,
            'current_status': status_filter,
            'q': q,
            'casting_statuses': CastingStage.Status.choices,
            'active_nav': 'orders',
        })


class CastingOrderDetailView(CastingRequiredMixin, View):
    template_name = 'casting/order_detail.html'

    def _ctx(self, pk):
        order = get_object_or_404(
            Order.objects.select_related('created_by', 'casting'), pk=pk,
        )
        stage, _ = CastingStage.objects.get_or_create(
            order=order, defaults={'total_quantity': order.quantity},
        )
        logs = order.stage_logs.filter(
            stage=Order.CurrentStage.CASTING,
        ).select_related('worker').order_by('-created_at')

        stanok_logs = order.stanok_logs.select_related('stanok', 'worker').order_by('-created_at')

        transfers = order.transfers.filter(
            from_stage=StageTransfer.Stage.CASTING,
        ).select_related('sent_by', 'accepted_by').order_by('-sent_at')

        incoming = order.transfers.filter(
            to_stage=StageTransfer.Stage.CASTING,
            status=StageTransfer.Status.PENDING,
        ).select_related('sent_by').order_by('-sent_at')

        stats = _casting_stats(order)

        return {
            'order': order,
            'stage': stage,
            'logs': logs,
            'stanok_logs': stanok_logs,
            'transfers': transfers,
            'incoming': incoming,
            'workers': User.objects.filter(is_active=True).order_by('name'),
            'stanoklar': Stanok.objects.filter(is_active=True).order_by('name'),
            'stats': stats,
            'active_nav': 'orders',
            'next_stages': [
                (StageTransfer.Stage.ATTACH,   "Ilish bo'limi"),
                (StageTransfer.Stage.SPRAY,    "Sepish bo'limi"),
                (StageTransfer.Stage.PACKAGING, "Upakovka bo'limi"),
                (StageTransfer.Stage.STONE,    "Tosh qadash bo'limi"),
                (StageTransfer.Stage.MONTAJ,   "Montaj bo'limi"),
            ],
        }

    def get(self, request, pk):
        return render(request, self.template_name, self._ctx(pk))

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(CastingStage, order=order)
        action = request.POST.get('action')

        # STATUS
        if action == 'set_status':
            new_status = request.POST.get('status')
            allowed = {
                CastingStage.Status.PENDING:    CastingStage.Status.IN_PROCESS,
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
            return redirect('casting:order_detail', pk=pk)

        # YARIM TAYYOR LOG (StanokLog)
        if action == 'add_stanok_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('casting:order_detail', pk=pk)
            try:
                quantity = int(request.POST.get('quantity', 0))
                defect   = int(request.POST.get('defect', 0))
            except (ValueError, TypeError):
                messages.error(request, "Miqdor noto'g'ri.")
                return redirect('casting:order_detail', pk=pk)
            if quantity <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('casting:order_detail', pk=pk)

            stanok_id = request.POST.get('stanok_id') or None
            stanok = None
            if stanok_id:
                try:
                    stanok = Stanok.objects.get(pk=stanok_id)
                except Stanok.DoesNotExist:
                    pass

            worker_id = request.POST.get('worker_id') or None
            worker = None
            if worker_id:
                try:
                    worker = User.objects.get(pk=worker_id)
                except User.DoesNotExist:
                    pass

            side = request.POST.get('side', 'single')
            if side not in ('top', 'bottom', 'single'):
                side = 'single'

            StanokLog.objects.create(
                order=order,
                stanok=stanok,
                worker=worker,
                quantity=quantity,
                defect=defect,
                side=side,
                note=request.POST.get('note', '').strip(),
            )
            if stage.status == CastingStage.Status.PENDING:
                stage.status = CastingStage.Status.IN_PROCESS
                stage.started_at = stage.started_at or timezone.now()
                stage.save()
            messages.success(request, f"{quantity} dona yarim tayyor log qo'shildi.")
            return redirect('casting:order_detail', pk=pk)

        # TAYYOR MAHSULOT LOG (OrderStageLog)
        if action == 'add_casting_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('casting:order_detail', pk=pk)
            try:
                quantity = int(request.POST.get('quantity', 0))
            except (ValueError, TypeError):
                messages.error(request, "Miqdor noto'g'ri.")
                return redirect('casting:order_detail', pk=pk)
            if quantity <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('casting:order_detail', pk=pk)

            log_so_far = order.stage_logs.filter(stage=Order.CurrentStage.CASTING).aggregate(s=Sum('quantity'))['s'] or 0
            if log_so_far + quantity > order.quantity:
                messages.warning(
                    request,
                    f"Ogohlantirish: Tayyor mahsulot ({log_so_far + quantity}) "
                    f"buyurtma miqdoridan ({order.quantity}) oshib ketadi! Log baribir qo'shildi."
                )

            worker_id = request.POST.get('worker_id') or None
            worker = None
            if worker_id:
                try:
                    worker = User.objects.get(pk=worker_id)
                except User.DoesNotExist:
                    pass

            OrderStageLog.objects.create(
                order=order,
                stage=Order.CurrentStage.CASTING,
                from_department='',
                to_department="Quyish bo'limi",
                quantity=quantity,
                worker=worker,
                note=request.POST.get('note', '').strip(),
            )
            if stage.status == CastingStage.Status.PENDING:
                stage.status = CastingStage.Status.IN_PROCESS
                stage.started_at = stage.started_at or timezone.now()
                stage.save()
            messages.success(request, f"{quantity} dona tayyor mahsulot log qo'shildi.")
            return redirect('casting:order_detail', pk=pk)

        # LOG O'ZGARTIRISH
        if action == 'edit_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('casting:order_detail', pk=pk)
            log = get_object_or_404(
                OrderStageLog,
                pk=request.POST.get('log_id'),
                order=order,
                stage=Order.CurrentStage.CASTING,
            )
            try:
                quantity = int(request.POST.get('quantity', 0))
            except (ValueError, TypeError):
                messages.error(request, "Miqdor noto'g'ri.")
                return redirect('casting:order_detail', pk=pk)
            if quantity <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('casting:order_detail', pk=pk)

            other_total = (
                order.stage_logs.filter(stage=Order.CurrentStage.CASTING)
                .exclude(pk=log.pk)
                .aggregate(s=Sum('quantity'))['s'] or 0
            )
            if other_total + quantity > order.quantity:
                messages.warning(
                    request,
                    f"Ogohlantirish: Jami ({other_total + quantity}) buyurtma miqdoridan ({order.quantity}) oshib ketadi!"
                )

            log.quantity = quantity
            log.note = request.POST.get('note', '').strip()
            worker_id = request.POST.get('worker_id') or None
            if worker_id:
                try:
                    log.worker = User.objects.get(pk=worker_id)
                except User.DoesNotExist:
                    log.worker = None
            else:
                log.worker = None
            stanok_id = request.POST.get('stanok_id') or None
            if stanok_id:
                try:
                    log.stanok = Stanok.objects.get(pk=stanok_id)
                except Stanok.DoesNotExist:
                    log.stanok = None
            else:
                log.stanok = None
            log.save()
            messages.success(request, "Log yangilandi.")
            return redirect('casting:order_detail', pk=pk)

        # LOG O'CHIRISH
        if action == 'delete_log':
            if stage.status == CastingStage.Status.COMPLETED:
                messages.error(request, "Bosqich yakunlangan.")
                return redirect('casting:order_detail', pk=pk)
            OrderStageLog.objects.filter(
                pk=request.POST.get('log_id'),
                order=order,
                stage=Order.CurrentStage.CASTING,
            ).delete()
            messages.success(request, "Log o'chirildi.")
            return redirect('casting:order_detail', pk=pk)

        # TRANSFER YUBORISH
        if action == 'send_transfer':
            if stage.status != CastingStage.Status.COMPLETED:
                messages.error(request, "Avval bosqichni yakunlang.")
                return redirect('casting:order_detail', pk=pk)
            to_stage = request.POST.get('to_stage', '')
            if to_stage not in dict(StageTransfer.Stage.choices):
                messages.error(request, "Noto'g'ri bo'lim.")
                return redirect('casting:order_detail', pk=pk)
            try:
                qty = int(request.POST.get('transfer_quantity', 0))
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('casting:order_detail', pk=pk)
            transfer = StageTransfer.objects.create(
                order=order,
                from_stage=StageTransfer.Stage.CASTING,
                to_stage=to_stage,
                sent_quantity=qty,
                sent_by=request.user,
                note=request.POST.get('transfer_note', '').strip(),
            )
            order.current_stage = to_stage
            order.save(update_fields=['current_stage'])
            messages.success(request, f"{qty} dona {transfer.get_to_stage_display()}ga yuborildi.")
            return redirect('casting:order_detail', pk=pk)

        # TRANSFER O'ZGARTIRISH (faqat PENDING bo'lsa)
        if action == 'edit_transfer':
            transfer = get_object_or_404(
                StageTransfer,
                pk=request.POST.get('transfer_id'),
                order=order,
                from_stage=StageTransfer.Stage.CASTING,
                status=StageTransfer.Status.PENDING,
                sent_by=request.user,
            )
            try:
                qty = int(request.POST.get('sent_quantity', 0))
            except (ValueError, TypeError):
                qty = 0
            if qty <= 0:
                messages.error(request, "Miqdor 0 dan katta bo'lishi kerak.")
                return redirect('casting:order_detail', pk=pk)
            transfer.sent_quantity = qty
            transfer.note = request.POST.get('transfer_note', '').strip()
            transfer.save()
            messages.success(request, "Transfer yangilandi.")
            return redirect('casting:order_detail', pk=pk)

        # TRANSFER O'CHIRISH (faqat PENDING bo'lsa)
        if action == 'delete_transfer':
            transfer = get_object_or_404(
                StageTransfer,
                pk=request.POST.get('transfer_id'),
                order=order,
                from_stage=StageTransfer.Stage.CASTING,
                status=StageTransfer.Status.PENDING,
                sent_by=request.user,
            )
            # Orderning current_stage-ini qaytarish
            order.current_stage = StageTransfer.Stage.CASTING
            order.save(update_fields=['current_stage'])
            transfer.delete()
            messages.success(request, "Transfer bekor qilindi.")
            return redirect('casting:order_detail', pk=pk)

        # TRANSFER QABUL QILISH
        if action == 'accept_transfer':
            transfer = get_object_or_404(
                StageTransfer, pk=request.POST.get('transfer_id'),
                order=order, to_stage=StageTransfer.Stage.CASTING,
                status=StageTransfer.Status.PENDING,
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
            transfer.status      = StageTransfer.Status.ACCEPTED
            transfer.save()
            messages.success(request, f"{accepted_qty} dona qabul qilindi.")
            return redirect('casting:order_detail', pk=pk)

        # TRANSFER RAD ETISH
        if action == 'reject_transfer':
            transfer = get_object_or_404(
                StageTransfer, pk=request.POST.get('transfer_id'),
                order=order, status=StageTransfer.Status.PENDING,
            )
            transfer.status      = StageTransfer.Status.REJECTED
            transfer.accepted_by = request.user
            transfer.accept_note = request.POST.get('accept_note', '').strip()
            transfer.accepted_at = timezone.now()
            transfer.save()
            messages.warning(request, "Transfer rad etildi.")
            return redirect('casting:order_detail', pk=pk)

        return redirect('casting:order_detail', pk=pk)


# ──────────────────────────────────────────────
#  STANOK CRUD
# ──────────────────────────────────────────────

class StanokListView(CastingRequiredMixin, View):
    template_name = 'casting/stanok_list.html'

    def get(self, request):
        stanoklar = Stanok.objects.all()
        return render(request, self.template_name, {
            'stanoklar': stanoklar,
            'active_nav': 'stanoklar',
        })


class StanokCreateView(CastingRequiredMixin, View):
    template_name = 'casting/stanok_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'title': 'Yangi stanok',
            'active_nav': 'stanoklar',
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        model = request.POST.get('model', '').strip()
        note = request.POST.get('note', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        if not name:
            messages.error(request, "Stanok nomi kiritilishi shart.")
            return render(request, self.template_name, {
                'title': 'Yangi stanok',
                'active_nav': 'stanoklar',
                'data': request.POST,
            })
        if Stanok.objects.filter(name=name).exists():
            messages.error(request, "Bu nomli stanok allaqachon mavjud.")
            return render(request, self.template_name, {
                'title': 'Yangi stanok',
                'active_nav': 'stanoklar',
                'data': request.POST,
            })
        Stanok.objects.create(name=name, model=model, note=note, is_active=is_active)
        messages.success(request, f'"{name}" stanoki qo\'shildi.')
        return redirect('casting:stanok_list')


class StanokUpdateView(CastingRequiredMixin, View):
    template_name = 'casting/stanok_form.html'

    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        return render(request, self.template_name, {
            'title': f'{stanok.name} — tahrirlash',
            'stanok': stanok,
            'active_nav': 'stanoklar',
        })

    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        name = request.POST.get('name', '').strip()
        model = request.POST.get('model', '').strip()
        note = request.POST.get('note', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        if not name:
            messages.error(request, "Stanok nomi kiritilishi shart.")
            return render(request, self.template_name, {
                'title': f'{stanok.name} — tahrirlash',
                'stanok': stanok,
                'active_nav': 'stanoklar',
                'data': request.POST,
            })
        if Stanok.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, "Bu nomli stanok allaqachon mavjud.")
            return render(request, self.template_name, {
                'title': f'{stanok.name} — tahrirlash',
                'stanok': stanok,
                'active_nav': 'stanoklar',
                'data': request.POST,
            })
        stanok.name = name
        stanok.model = model
        stanok.note = note
        stanok.is_active = is_active
        stanok.save()
        messages.success(request, f'"{name}" yangilandi.')
        return redirect('casting:stanok_list')


class StanokDeleteView(CastingRequiredMixin, View):
    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        name = stanok.name
        stanok.delete()
        messages.success(request, f'"{name}" o\'chirildi.')
        return redirect('casting:stanok_list')


# ──────────────────────────────────────────────
#  STANOK LOG LIST
# ──────────────────────────────────────────────

class StanokLogListView(CastingRequiredMixin, View):
    template_name = 'casting/stanok_log_list.html'

    def get(self, request):
        logs = StanokLog.objects.select_related('order', 'stanok', 'worker').order_by('-created_at')
        stanok_id = request.GET.get('stanok')
        order_q = request.GET.get('q', '').strip()
        if stanok_id:
            logs = logs.filter(stanok_id=stanok_id)
        if order_q:
            logs = logs.filter(order__name__icontains=order_q)
        stanoklar = Stanok.objects.all()
        return render(request, self.template_name, {
            'logs': logs[:200],
            'stanoklar': stanoklar,
            'active_nav': 'stanok_logs',
            'selected_stanok': stanok_id or '',
            'q': order_q,
        })
