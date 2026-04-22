from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.order.models import CastingStage, Order, OrderStageLog
from apps.order.forms import CastingForm


CASTING_ROLES = {'CASTINGMANAGER', 'CEO'}


class CastingRequiredMixin(LoginRequiredMixin):
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = getattr(request.user, 'role', None)
        role_name = role.name if role else ''
        if not (request.user.is_superuser or role_name in CASTING_ROLES):
            messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class CastingDashboardView(CastingRequiredMixin, View):
    def get(self, request):
        all_orders = Order.objects.filter(
            Q(current_stage='casting') | Q(casting__isnull=False)
        ).distinct()

        total = all_orders.count()
        pending = all_orders.filter(casting__status='pending').count()
        in_process = all_orders.filter(casting__status='in_process').count()
        completed = all_orders.filter(casting__status='completed').count()
        rejected = all_orders.filter(casting__status='rejected').count()

        # So'nggi faoliyat loglari
        recent_logs = OrderStageLog.objects.filter(
            stage=Order.CurrentStage.CASTING
        ).select_related('order', 'worker').order_by('-created_at')[:10]

        # Muddati o'tgan orderlar
        today = timezone.now().date()
        overdue = all_orders.filter(
            deadline__lt=today
        ).exclude(status__in=['delivered', 'cancelled']).count()

        return render(request, 'casting/dashboard.html', {
            'total': total,
            'pending': pending,
            'in_process': in_process,
            'completed': completed,
            'rejected': rejected,
            'overdue': overdue,
            'recent_logs': recent_logs,
            'active_nav': 'dashboard',
        })


class CastingOrderListView(CastingRequiredMixin, View):
    def get(self, request):
        qs = Order.objects.filter(
            Q(current_stage='casting') | Q(casting__isnull=False)
        ).distinct().select_related('casting').order_by('-created_at')

        # Filter
        status_filter = request.GET.get('status', '')
        q = request.GET.get('q', '')

        if status_filter:
            qs = qs.filter(casting__status=status_filter)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(order_number__icontains=q))

        casting_statuses = CastingStage.Status.choices

        return render(request, 'casting/order_list.html', {
            'orders': qs,
            'current_status': status_filter,
            'q': q,
            'casting_statuses': casting_statuses,
            'active_nav': 'orders',
        })


class CastingOrderDetailView(CastingRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage, _ = CastingStage.objects.get_or_create(
            order=order,
            defaults={'total_quantity': order.quantity}
        )
        logs = OrderStageLog.objects.filter(
            order=order, stage=Order.CurrentStage.CASTING
        ).select_related('worker', 'accepted_by').order_by('-created_at')

        return render(request, 'casting/order_detail.html', {
            'order': order,
            'stage': stage,
            'logs': logs,
            'active_nav': 'orders',
        })


class CastingStageUpdateView(CastingRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage, _ = CastingStage.objects.get_or_create(
            order=order,
            defaults={'total_quantity': order.quantity}
        )
        form = CastingForm(instance=stage)
        return render(request, 'casting/stage_update.html', {
            'form': form,
            'order': order,
            'stage': stage,
            'active_nav': 'orders',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(CastingStage, order=order)
        form = CastingForm(request.POST, instance=stage)
        if form.is_valid():
            saved = form.save()
            quantity = form.cleaned_data.get('total_quantity', 0)
            note = form.cleaned_data.get('note', '')
            OrderStageLog.objects.create(
                order=order,
                stage=Order.CurrentStage.CASTING,
                from_department='',
                to_department='Quyish',
                quantity=quantity,
                worker=request.user,
                note=note,
            )
            messages.success(request, 'Quyish bosqichi yangilandi.')
            return redirect('casting:order_detail', pk=pk)

        return render(request, 'casting/stage_update.html', {
            'form': form,
            'order': order,
            'stage': stage,
            'active_nav': 'orders',
        })


class CastingTransferView(CastingRequiredMixin, View):
    """Zakazni quyish bo'limidan keyingi bo'limga o'tkazish."""

    NEXT_STAGE_MAP = {
        'casting': ('montaj', 'Montaj bo\'limi'),
    }

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        stage = get_object_or_404(CastingStage, order=order)

        quantity = request.POST.get('quantity', stage.total_quantity)
        note = request.POST.get('note', '')
        next_stage_key = request.POST.get('next_stage', 'montaj')

        next_stage_labels = {
            'montaj': 'Montaj bo\'limi',
            'hanging': 'Ilish bo\'limi',
            'stone_setting': 'Tosh qadash bo\'limi',
            'packaging': 'Upakovka bo\'limi',
        }
        next_label = next_stage_labels.get(next_stage_key, 'Montaj bo\'limi')

        # Stageni completed ga o'tkazish
        stage.status = CastingStage.Status.COMPLETED
        stage.finished_at = timezone.now()
        stage.save()

        # Orderni keyingi bosqichga o'tkazish
        order.current_stage = next_stage_key
        if order.status == Order.Status.NEW:
            order.status = Order.Status.IN_PROCESS
        order.save()

        # Log yozish
        OrderStageLog.objects.create(
            order=order,
            stage=Order.CurrentStage.CASTING,
            from_department='Quyish bo\'limi',
            to_department=next_label,
            quantity=int(quantity),
            worker=request.user,
            note=note,
        )

        messages.success(request, f'Zakaz "{order.name}" {next_label}ga muvaffaqiyatli o\'tkazildi.')
        return redirect('casting:order_list')
