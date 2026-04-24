import datetime

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.casting.forms import StanokForm
from apps.casting.models import HomMahsulotLog, Stanok, TayorMahsulotLog
from apps.order.models import Order
from apps.order.views.mixins import CastingManagerRequiredMixin


# ── Orders ────────────────────────────────────────────────────────────────────

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
            'accepted':   Order.objects.filter(status='accepted').count(),
            'in_process': Order.objects.filter(status='in_process').count(),
            'ready':      Order.objects.filter(status='ready').count(),
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
        order = get_object_or_404(Order.objects.select_related('brujka', 'created_by'), pk=pk)
        return render(request, 'casting/order_detail.html', {
            'order': order,
            'active_nav': 'orders',
        })


# ── Stanoklar ─────────────────────────────────────────────────────────────────

class StanokListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        status_f = request.GET.get('status', '')
        qs = Stanok.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        if status_f:
            qs = qs.filter(status=status_f)
        counts = {
            'total':    Stanok.objects.count(),
            'active':   Stanok.objects.filter(status=Stanok.Status.ACTIVE).count(),
            'repair':   Stanok.objects.filter(status=Stanok.Status.REPAIR).count(),
            'inactive': Stanok.objects.filter(status=Stanok.Status.INACTIVE).count(),
        }
        return render(request, 'casting/stanok_list.html', {
            'stanoklar': qs,
            'q': q,
            'status_f': status_f,
            'counts': counts,
            'statuses': Stanok.Status.choices,
            'active_nav': 'stanoklar',
        })


class StanokCreateView(CastingManagerRequiredMixin, View):
    def get(self, request):
        form = StanokForm()
        return render(request, 'casting/stanok_form.html', {
            'title': 'Yangi stanok',
            'form': form,
            'active_nav': 'stanoklar',
        })

    def post(self, request):
        form = StanokForm(request.POST)
        if form.is_valid():
            stanok = form.save()
            messages.success(request, f'"{stanok.name}" stanogi qo\'shildi.')
            return redirect('casting:stanok_list')
        
        return render(request, 'casting/stanok_form.html', {
            'title': 'Yangi stanok',
            'form': form,
            'active_nav': 'stanoklar',
        })


class StanokUpdateView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        form = StanokForm(instance=stanok)
        return render(request, 'casting/stanok_form.html', {
            'title': f'{stanok.name} — tahrirlash',
            'form': form,
            'active_nav': 'stanoklar',
        })

    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        form = StanokForm(request.POST, instance=stanok)
        if form.is_valid():
            stanok = form.save()
            messages.success(request, f'"{stanok.name}" yangilandi.')
            return redirect('casting:stanok_list')
        
        return render(request, 'casting/stanok_form.html', {
            'title': f'{stanok.name} — tahrirlash',
            'form': form,
            'active_nav': 'stanoklar',
        })


class StanokDeleteView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        return render(request, 'casting/stanok_confirm_delete.html', {
            'object': stanok, 'active_nav': 'stanoklar',
        })

    def post(self, request, pk):
        stanok = get_object_or_404(Stanok, pk=pk)
        name = stanok.name
        stanok.delete()
        messages.success(request, f'"{name}" o\'chirildi.')
        return redirect('casting:stanok_list')


# ── Loglar ────────────────────────────────────────────────────────────────────

def _log_ctx(order):
    """Order uchun umumiy log konteksti."""
    hom_loglar  = order.hom_loglar.select_related('stanok', 'created_by').order_by('-sana', '-created_at')
    tayor_loglar = order.tayor_loglar.select_related('created_by').order_by('-sana', '-created_at')
    hom_jami   = hom_loglar.aggregate(j=Sum('miqdor'))['j'] or 0
    tayor_jami = tayor_loglar.aggregate(j=Sum('miqdor'))['j'] or 0
    return {
        'hom_loglar':   hom_loglar,
        'tayor_loglar': tayor_loglar,
        'hom_jami':     hom_jami,
        'tayor_jami':   tayor_jami,
        'stanoklar':    Stanok.objects.filter(status=Stanok.Status.ACTIVE),
        'today':        timezone.localdate(),
    }


class OrderLogView(CastingManagerRequiredMixin, View):
    """Buyurtma uchun hom va tayor mahsulot loglari."""

    def get(self, request, pk):
        order = get_object_or_404(Order.objects.select_related('brujka'), pk=pk)
        return render(request, 'casting/order_log.html', {
            'order': order,
            'active_nav': 'orders',
            'status_filter': order.status,
            **_log_ctx(order),
        })


class HomLogCreateView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('casting:order_log', pk=pk)

        sana_str = request.POST.get('sana', '').strip()
        try:
            sana = datetime.date.fromisoformat(sana_str)
        except ValueError:
            sana = timezone.localdate()

        stanok_id = request.POST.get('stanok', '').strip()
        stanok = None
        if stanok_id:
            stanok = Stanok.objects.filter(pk=stanok_id).first()

        HomMahsulotLog.objects.create(
            order=order, stanok=stanok, miqdor=miqdor,
            sana=sana, izoh=request.POST.get('izoh', '').strip(),
            created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona hom mahsulot qo\'shildi.')
        return redirect('casting:order_log', pk=pk)


class HomLogDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(HomMahsulotLog, pk=log_pk, order_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('casting:order_log', pk=pk)


class TayorLogCreateView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('casting:order_log', pk=pk)

        sana_str = request.POST.get('sana', '').strip()
        try:
            sana = datetime.date.fromisoformat(sana_str)
        except ValueError:
            sana = timezone.localdate()

        TayorMahsulotLog.objects.create(
            order=order, miqdor=miqdor, sana=sana,
            izoh=request.POST.get('izoh', '').strip(),
            created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona tayor mahsulot qo\'shildi.')
        return redirect('casting:order_log', pk=pk)


class TayorLogDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(TayorMahsulotLog, pk=log_pk, order_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('casting:order_log', pk=pk)
