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
        q = request.GET.get('q', '').strip()
        base_qs = Order.objects.select_related('brujka', 'created_by').filter(
            status=Order.Status.IN_PROCESS
        )
        if q:
            base_qs = base_qs.filter(name__icontains=q)

        # Har bir order uchun hom/tayor summalarini annotate qilamiz
        orders = base_qs.annotate(
            hom_sum=Sum('hom_loglar__miqdor'),
            tayor_sum=Sum('tayor_loglar__miqdor'),
        ).order_by('-created_at')

        today = timezone.localdate()
        # Barcha in_process orderlar (filter qilinmagan, statistika uchun)
        all_ip = Order.objects.filter(status=Order.Status.IN_PROCESS)
        buyurtma_jami = all_ip.aggregate(j=Sum('quantity'))['j'] or 0

        # Bugungi loglar (barcha orderlar bo'yicha)
        hom_bugun   = HomMahsulotLog.objects.filter(sana=today).aggregate(j=Sum('miqdor'))['j'] or 0
        tayor_bugun = TayorMahsulotLog.objects.filter(sana=today).aggregate(j=Sum('miqdor'))['j'] or 0
        # Jami tayor (in_process orderlarga tegishli)
        tayor_jami  = TayorMahsulotLog.objects.filter(
            order__status=Order.Status.IN_PROCESS
        ).aggregate(j=Sum('miqdor'))['j'] or 0
        hom_jami    = HomMahsulotLog.objects.filter(
            order__status=Order.Status.IN_PROCESS
        ).aggregate(j=Sum('miqdor'))['j'] or 0

        return render(request, 'casting/order_list.html', {
            'orders': orders,
            'q': q,
            'active_nav': 'orders',
            'status_filter': 'in_process',
            'today': today,
            'stats': {
                'hom_bugun':      hom_bugun,
                'tayor_bugun':    tayor_bugun,
                'hom_jami':       hom_jami,
                'tayor_jami':     tayor_jami,
                'buyurtma_jami':  buyurtma_jami,
                'order_count':    all_ip.count(),
                'tayor_pct':      round(tayor_jami / buyurtma_jami * 100) if buyurtma_jami else 0,
            },
        })


class CastingStatsView(CastingManagerRequiredMixin, View):
    def get(self, request):
        today = timezone.localdate()

        # Sana oralig'i
        try:
            date_from = datetime.date.fromisoformat(request.GET.get('from', ''))
        except ValueError:
            date_from = today - datetime.timedelta(days=13)
        try:
            date_to = datetime.date.fromisoformat(request.GET.get('to', ''))
        except ValueError:
            date_to = today
        if date_from > date_to:
            date_from = date_to - datetime.timedelta(days=13)

        days = []
        d = date_from
        while d <= date_to:
            days.append(d)
            d += datetime.timedelta(days=1)

        hom_by_day = {
            r['sana']: r['j']
            for r in HomMahsulotLog.objects.filter(sana__in=days)
                .values('sana').annotate(j=Sum('miqdor'))
        }
        tayor_by_day = {
            r['sana']: r['j']
            for r in TayorMahsulotLog.objects.filter(sana__in=days)
                .values('sana').annotate(j=Sum('miqdor'))
        }

        chart_labels = [d.strftime('%d.%m') for d in days]
        chart_hom    = [hom_by_day.get(d, 0) for d in days]
        chart_tayor  = [tayor_by_day.get(d, 0) for d in days]

        stanok_stats = list(
            HomMahsulotLog.objects.filter(sana__range=(date_from, date_to))
                .values('stanok__name').annotate(j=Sum('miqdor')).order_by('-j')[:8]
        )

        ndays     = len(days) or 1
        hom_davr  = sum(chart_hom)
        tayor_davr = sum(chart_tayor)
        avg_hom   = round(hom_davr  / ndays, 1)
        avg_tayor = round(tayor_davr / ndays, 1)
        hom_bugun   = hom_by_day.get(today, 0)
        tayor_bugun = tayor_by_day.get(today, 0)

        in_process    = Order.objects.filter(status=Order.Status.IN_PROCESS)
        order_count   = in_process.count()
        buyurtma_jami = in_process.aggregate(j=Sum('quantity'))['j'] or 0
        tayor_jami_ip = TayorMahsulotLog.objects.filter(
            order__status=Order.Status.IN_PROCESS
        ).aggregate(j=Sum('miqdor'))['j'] or 0
        hom_jami_ip   = HomMahsulotLog.objects.filter(
            order__status=Order.Status.IN_PROCESS
        ).aggregate(j=Sum('miqdor'))['j'] or 0
        tayor_pct = round(tayor_jami_ip / buyurtma_jami * 100) if buyurtma_jami else 0

        order_progress = list(
            in_process.annotate(
                t_sum=Sum('tayor_loglar__miqdor'),
                h_sum=Sum('hom_loglar__miqdor'),
            ).values('id', 'name', 'quantity', 't_sum', 'h_sum', 'deadline')
            .order_by('deadline')
        )

        return render(request, 'casting/stats.html', {
            'active_nav': 'stats',
            'today': today,
            'date_from': date_from,
            'date_to': date_to,
            'hom_bugun': hom_bugun,
            'tayor_bugun': tayor_bugun,
            'hom_davr': hom_davr,
            'tayor_davr': tayor_davr,
            'avg_hom': avg_hom,
            'avg_tayor': avg_tayor,
            'order_count': order_count,
            'buyurtma_jami': buyurtma_jami,
            'tayor_jami_ip': tayor_jami_ip,
            'hom_jami_ip': hom_jami_ip,
            'tayor_pct': tayor_pct,
            'stanok_stats': stanok_stats,
            'chart_labels': chart_labels,
            'chart_hom': chart_hom,
            'chart_tayor': chart_tayor,
            'order_progress': order_progress,
        })


class CastingOrderDetailView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(Order.objects.select_related('brujka', 'created_by'), pk=pk)

        hom_loglar   = order.hom_loglar.select_related('stanok', 'created_by').order_by('-sana', '-created_at')
        tayor_loglar = order.tayor_loglar.select_related('created_by').order_by('-sana', '-created_at')
        hom_jami     = hom_loglar.aggregate(j=Sum('miqdor'))['j'] or 0
        tayor_jami   = tayor_loglar.aggregate(j=Sum('miqdor'))['j'] or 0

        # Kunlik loglar (so'nggi 7 kun)
        today = timezone.localdate()
        days  = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
        hom_by_day   = {r['sana']: r['j'] for r in hom_loglar.filter(sana__in=days).values('sana').annotate(j=Sum('miqdor'))}
        tayor_by_day = {r['sana']: r['j'] for r in tayor_loglar.filter(sana__in=days).values('sana').annotate(j=Sum('miqdor'))}

        return render(request, 'casting/order_detail.html', {
            'order': order,
            'active_nav': 'orders',
            'status_filter': order.status,
            'hom_loglar':   hom_loglar,
            'tayor_loglar': tayor_loglar,
            'hom_jami':     hom_jami,
            'tayor_jami':   tayor_jami,
            'today':        today,
            'chart_labels': [d.strftime('%d.%m') for d in days],
            'chart_hom':    [hom_by_day.get(d, 0)   for d in days],
            'chart_tayor':  [tayor_by_day.get(d, 0)  for d in days],
            'stanoklar':    Stanok.objects.filter(status=Stanok.Status.ACTIVE),
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
