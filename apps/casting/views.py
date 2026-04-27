import datetime

from django.contrib import messages
from django.db.models import OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.casting.forms import StanokForm, QuyishRasxodForm, OrderForm
from apps.casting.models import (
    AdditionalHomLog, AdditionalOrder, AdditionalTayorLog,
    HomMahsulotLog, RasxodLog, Stanok, TayorMahsulotLog, Zamak, QuyishRasxod,
    QuyishJarayon, QuyishJarayonLog,
)
from apps.order.models import Order, Brujka
from apps.order.views.mixins import CastingManagerRequiredMixin


# ── Orders ────────────────────────────────────────────────────────────────────

class CastingOrderListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        q          = request.GET.get('q', '').strip()
        status_tab = request.GET.get('tab', 'accepted')  # 'accepted' | 'in_process'
        if status_tab not in ('accepted', 'in_process'):
            status_tab = 'accepted'

        # "Yangi" tab = accepted, "Ishlab chiqarilmoqda" = in_process
        base_qs = Order.objects.select_related('brujka', 'created_by', 'quyish_jarayon').filter(
            status__in=[Order.Status.ACCEPTED, Order.Status.IN_PROCESS]
        )
        if q:
            base_qs = base_qs.filter(name__icontains=q)

        hom_sub = HomMahsulotLog.objects.filter(
            order=OuterRef('pk')
        ).values('order').annotate(s=Sum('miqdor')).values('s')

        tayor_sub = TayorMahsulotLog.objects.filter(
            order=OuterRef('pk')
        ).values('order').annotate(s=Sum('miqdor')).values('s')

        orders = base_qs.filter(status=status_tab).annotate(
            hom_sum=Coalesce(Subquery(hom_sub), 0),
            tayor_sum=Coalesce(Subquery(tayor_sub), 0),
        ).order_by('-created_at')

        today = timezone.localdate()
        all_ip = Order.objects.filter(status=Order.Status.IN_PROCESS)
        buyurtma_jami = all_ip.aggregate(j=Sum('quantity'))['j'] or 0

        hom_bugun   = HomMahsulotLog.objects.filter(sana=today).aggregate(j=Sum('miqdor'))['j'] or 0
        tayor_bugun = TayorMahsulotLog.objects.filter(sana=today).aggregate(j=Sum('miqdor'))['j'] or 0
        tayor_jami  = TayorMahsulotLog.objects.filter(
            order__status=Order.Status.IN_PROCESS
        ).aggregate(j=Sum('miqdor'))['j'] or 0
        hom_jami    = HomMahsulotLog.objects.filter(
            order__status=Order.Status.IN_PROCESS
        ).aggregate(j=Sum('miqdor'))['j'] or 0

        accepted_count = Order.objects.filter(status=Order.Status.ACCEPTED).count()
        ip_count       = Order.objects.filter(status=Order.Status.IN_PROCESS).count()

        return render(request, 'casting/order_list.html', {
            'orders':         orders,
            'q':              q,
            'tab':            status_tab,
            'accepted_count': accepted_count,
            'ip_count':       ip_count,
            'active_nav':     'orders',
            'status_filter':  status_tab,
            'today':          today,
            'stats': {
                'hom_bugun':     hom_bugun,
                'tayor_bugun':   tayor_bugun,
                'hom_jami':      hom_jami,
                'tayor_jami':    tayor_jami,
                'buyurtma_jami': buyurtma_jami,
                'order_count':   all_ip.count(),
                'tayor_pct':     round(tayor_jami / buyurtma_jami * 100) if buyurtma_jami else 0,
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
        order = get_object_or_404(
            Order.objects.select_related('brujka', 'quyish_jarayon'), pk=pk
        )
        quyish = getattr(order, 'quyish_jarayon', None)
        return render(request, 'casting/order_log.html', {
            'order':   order,
            'quyish':  quyish,
            'active_nav':    'orders',
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


# ── Order status o'zgartirish ─────────────────────────────────────────────────

class OrderSetStatusView(CastingManagerRequiredMixin, View):
    """Casting manager: accepted → in_process, in_process → ready."""
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get('status', '')
        allowed = {Order.Status.IN_PROCESS, Order.Status.ACCEPTED, Order.Status.READY}
        if new_status in allowed:
            order.status = new_status
            order.save(update_fields=['status', 'updated_at'])
            # in_process ga o'tganda QuyishJarayon avtomatik yaratiladi
            if new_status == Order.Status.IN_PROCESS:
                QuyishJarayon.objects.get_or_create(
                    order=order,
                    defaults={
                        'status':     QuyishJarayon.Status.QUYILMOQDA,
                        'created_by': request.user,
                    },
                )
            labels = {
                Order.Status.IN_PROCESS: 'Ishlab chiqarilmoqda',
                Order.Status.READY:      "Tayyor",
            }
            messages.success(request, f'"{order.name}" — {labels.get(new_status, new_status)}')
        return redirect('casting:order_list')


# ── Rasxod ────────────────────────────────────────────────────────────────────

class RasxodListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        q        = request.GET.get('q', '').strip()
        stanok_f = request.GET.get('stanok', '').strip()
        zamak_f  = request.GET.get('zamak', '').strip()
        today    = timezone.localdate()

        try:
            date_from = datetime.date.fromisoformat(request.GET.get('from', ''))
        except ValueError:
            date_from = today - datetime.timedelta(days=29)
        try:
            date_to = datetime.date.fromisoformat(request.GET.get('to', ''))
        except ValueError:
            date_to = today

        qs = RasxodLog.objects.select_related('stanok', 'zamak', 'created_by')
        if stanok_f:
            qs = qs.filter(stanok_id=stanok_f)
        if zamak_f:
            qs = qs.filter(zamak_id=zamak_f)
        if q:
            qs = qs.filter(izoh__icontains=q)
        qs = qs.filter(sana__range=(date_from, date_to)).order_by('-sana', '-created_at')

        # Statistika
        from django.db.models import Count
        stanok_stats = list(
            qs.values('stanok__name').annotate(j=Sum('miqdor')).order_by('-j')[:6]
        )
        zamak_stats = list(
            qs.values('zamak__name', 'zamak__unit').annotate(j=Sum('miqdor')).order_by('-j')[:6]
        )
        jami = qs.aggregate(j=Sum('miqdor'))['j'] or 0

        return render(request, 'casting/rasxod_list.html', {
            'rasxodlar':   qs,
            'stanoklar':   Stanok.objects.filter(status=Stanok.Status.ACTIVE),
            'zamaklar':    Zamak.objects.filter(is_active=True),
            'stanok_f':    stanok_f,
            'zamak_f':     zamak_f,
            'q':           q,
            'date_from':   date_from,
            'date_to':     date_to,
            'today':       today,
            'stanok_stats': stanok_stats,
            'zamak_stats':  zamak_stats,
            'jami':         jami,
            'active_nav':  'rasxod',
        })


class RasxodCreateView(CastingManagerRequiredMixin, View):
    def post(self, request):
        stanok_id = request.POST.get('stanok', '').strip()
        zamak_id  = request.POST.get('zamak', '').strip()
        try:
            miqdor = float(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('casting:rasxod_list')
        try:
            sana = datetime.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        stanok = get_object_or_404(Stanok, pk=stanok_id) if stanok_id else None
        zamak  = get_object_or_404(Zamak, pk=zamak_id) if zamak_id else None
        if not stanok or not zamak:
            messages.error(request, 'Stanok va zamak majburiy.')
            return redirect('casting:rasxod_list')
        from decimal import Decimal
        RasxodLog.objects.create(
            stanok=stanok, zamak=zamak, miqdor=Decimal(str(miqdor)),
            sana=sana, izoh=request.POST.get('izoh', '').strip(),
            created_by=request.user,
        )
        messages.success(request, f'{miqdor} {zamak.unit} rasxod yozildi.')
        return redirect('casting:rasxod_list')


class RasxodDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        log = get_object_or_404(RasxodLog, pk=pk)
        log.delete()
        messages.success(request, 'Rasxod o\'chirildi.')
        return redirect('casting:rasxod_list')


# ── Zamak CRUD ────────────────────────────────────────────────────────────────

class ZamakListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        return render(request, 'casting/zamak_list.html', {
            'zamaklar': Zamak.objects.all(),
            'active_nav': 'rasxod',
        })


class ZamakCreateView(CastingManagerRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name', '').strip()
        unit = request.POST.get('unit', 'kg').strip()
        if not name:
            messages.error(request, 'Nomi majburiy.')
            return redirect('casting:zamak_list')
        Zamak.objects.create(name=name, unit=unit)
        messages.success(request, f'"{name}" zamak qo\'shildi.')
        return redirect('casting:zamak_list')


class ZamakDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        z = get_object_or_404(Zamak, pk=pk)
        z.delete()
        messages.success(request, 'Zamak o\'chirildi.')
        return redirect('casting:zamak_list')


# ── Additional Orders ─────────────────────────────────────────────────────────

class AdditionalOrderListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        status_f = request.GET.get('status', '')
        qs = AdditionalOrder.objects.select_related('created_by').annotate(
            hom_sum=Sum('hom_loglar__miqdor')
        )
        if status_f:
            qs = qs.filter(status=status_f)
        qs = qs.order_by('-created_at')
        counts = {s: AdditionalOrder.objects.filter(status=s).count() for s, _ in AdditionalOrder.Status.choices}
        statuses_with_counts = [(v, l, counts.get(v, 0)) for v, l in AdditionalOrder.Status.choices]
        return render(request, 'casting/additional_order_list.html', {
            'orders': qs, 'counts': counts, 'status_f': status_f,
            'statuses': AdditionalOrder.Status.choices,
            'statuses_with_counts': statuses_with_counts,
            'active_nav': 'additional',
        })


class AdditionalOrderCreateView(CastingManagerRequiredMixin, View):
    def get(self, request):
        return render(request, 'casting/additional_order_form.html', {
            'title': 'Yangi qo\'shimcha buyurtma',
            'active_nav': 'additional',
            'today': timezone.localdate(),
        })

    def post(self, request):
        name  = request.POST.get('name', '').strip()
        note  = request.POST.get('note', '').strip()
        errors = {}
        try:
            qty = int(request.POST.get('quantity', 0))
            assert qty > 0
        except (ValueError, AssertionError):
            errors['quantity'] = 'Miqdor musbat son bo\'lishi kerak.'
        try:
            deadline = datetime.date.fromisoformat(request.POST.get('deadline', ''))
        except ValueError:
            errors['deadline'] = 'Sana noto\'g\'ri.'
            deadline = None
        if not name:
            errors['name'] = 'Nomi majburiy.'
        if errors:
            return render(request, 'casting/additional_order_form.html', {
                'title': 'Yangi qo\'shimcha buyurtma', 'errors': errors,
                'data': request.POST, 'active_nav': 'additional',
                'today': timezone.localdate(),
            })
        order = AdditionalOrder.objects.create(
            name=name, quantity=qty, deadline=deadline,
            note=note, created_by=request.user,
        )
        messages.success(request, f'"{order.name}" qo\'shimcha buyurtma yaratildi.')
        return redirect('casting:additional_order_detail', pk=order.pk)


class AdditionalOrderDetailView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        hom_loglar   = order.hom_loglar.select_related('stanok', 'created_by').order_by('-sana', '-created_at')
        tayor_loglar = order.tayor_loglar.select_related('created_by').order_by('-sana', '-created_at')
        hom_jami     = hom_loglar.aggregate(j=Sum('miqdor'))['j'] or 0
        tayor_jami   = tayor_loglar.aggregate(j=Sum('miqdor'))['j'] or 0
        return render(request, 'casting/additional_order_detail.html', {
            'order': order,
            'hom_loglar': hom_loglar,
            'tayor_loglar': tayor_loglar,
            'hom_jami': hom_jami,
            'tayor_jami': tayor_jami,
            'stanoklar': Stanok.objects.filter(status=Stanok.Status.ACTIVE),
            'today': timezone.localdate(),
            'active_nav': 'additional',
        })


class AdditionalOrderUpdateView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        new_status = request.POST.get('status', order.status)
        if new_status in dict(AdditionalOrder.Status.choices):
            order.status = new_status
        name = request.POST.get('name', order.name).strip()
        if name:
            order.name = name
        try:
            qty = int(request.POST.get('quantity', order.quantity))
            if qty > 0:
                order.quantity = qty
        except ValueError:
            pass
        try:
            order.deadline = datetime.date.fromisoformat(request.POST.get('deadline', ''))
        except ValueError:
            pass
        order.note = request.POST.get('note', order.note).strip()
        order.save()
        messages.success(request, 'Yangilandi.')
        return redirect('casting:additional_order_detail', pk=pk)


class AdditionalOrderDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        order.delete()
        messages.success(request, 'O\'chirildi.')
        return redirect('casting:additional_order_list')


class AdditionalHomLogCreateView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        if order.status == AdditionalOrder.Status.NEW:
            messages.error(request, 'Yangi buyurtmaga log yozib bo\'lmaydi. Avval ishlab chiqarishga o\'tkazing.')
            return redirect('casting:additional_order_detail', pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('casting:additional_order_detail', pk=pk)
        try:
            sana = datetime.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        stanok_id = request.POST.get('stanok', '').strip()
        stanok = Stanok.objects.filter(pk=stanok_id).first() if stanok_id else None
        AdditionalHomLog.objects.create(
            add_order=order, stanok=stanok, miqdor=miqdor, sana=sana,
            izoh=request.POST.get('izoh', '').strip(), created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona hom mahsulot qo\'shildi.')
        return redirect('casting:additional_order_detail', pk=pk)


class AdditionalHomLogDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(AdditionalHomLog, pk=log_pk, add_order_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('casting:additional_order_detail', pk=pk)


class AdditionalTayorLogCreateView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        if order.status == AdditionalOrder.Status.NEW:
            messages.error(request, 'Yangi buyurtmaga log yozib bo\'lmaydi.')
            return redirect('casting:additional_order_detail', pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor > 0
        except (ValueError, AssertionError):
            messages.error(request, 'Miqdor musbat son bo\'lishi kerak.')
            return redirect('casting:additional_order_detail', pk=pk)
        try:
            sana = datetime.date.fromisoformat(request.POST.get('sana', ''))
        except ValueError:
            sana = timezone.localdate()
        AdditionalTayorLog.objects.create(
            add_order=order, miqdor=miqdor, sana=sana,
            izoh=request.POST.get('izoh', '').strip(),
            created_by=request.user,
        )
        messages.success(request, f'{miqdor} dona tayor mahsulot qo\'shildi.')
        return redirect('casting:additional_order_detail', pk=pk)


class AdditionalTayorLogDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(AdditionalTayorLog, pk=log_pk, add_order_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('casting:additional_order_detail', pk=pk)


class AdditionalOrderSetStatusView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        order = get_object_or_404(AdditionalOrder, pk=pk)
        new_status = request.POST.get('status', '')
        if new_status in dict(AdditionalOrder.Status.choices):
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f'Holat yangilandi: {order.get_status_display()}')
        return redirect('casting:additional_order_detail', pk=pk)


# ── Quyish Rasxod CRUD ────────────────────────────────────────────────────────

class QuyishRasxodListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        rasxodlar   = QuyishRasxod.objects.select_related('created_by').all()
        jami_miqdor = rasxodlar.aggregate(j=Sum('miqdor'))['j'] or 0
        return render(request, 'casting/quyish_rasxod_list.html', {
            'rasxodlar':   rasxodlar,
            'jami_miqdor': jami_miqdor,
            'active_nav':  'quyish_rasxod',
            'today':       timezone.localdate(),
        })


class QuyishRasxodCreateView(CastingManagerRequiredMixin, View):
    def get(self, request):
        form = QuyishRasxodForm()
        return render(request, 'casting/quyish_rasxod_form.html', {
            'form': form,
            'active_nav': 'quyish_rasxod',
            'today': timezone.localdate(),
        })

    def post(self, request):
        form = QuyishRasxodForm(request.POST)
        if form.is_valid():
            rasxod = form.save(commit=False)
            rasxod.created_by = request.user
            rasxod.save()
            messages.success(request, 'Rasxod qo\'shildi.')
            return redirect('casting:quyish_rasxod_list')
        return render(request, 'casting/quyish_rasxod_form.html', {
            'form': form,
            'active_nav': 'quyish_rasxod',
            'today': timezone.localdate(),
        })


class QuyishRasxodUpdateView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        rasxod = get_object_or_404(QuyishRasxod, pk=pk)
        form = QuyishRasxodForm(instance=rasxod)
        return render(request, 'casting/quyish_rasxod_form.html', {
            'rasxod': rasxod,
            'form': form,
            'active_nav': 'quyish_rasxod',
            'today': timezone.localdate(),
        })

    def post(self, request, pk):
        rasxod = get_object_or_404(QuyishRasxod, pk=pk)
        form = QuyishRasxodForm(request.POST, instance=rasxod)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rasxod yangilandi.')
            return redirect('casting:quyish_rasxod_list')
        return render(request, 'casting/quyish_rasxod_form.html', {
            'rasxod': rasxod,
            'form': form,
            'active_nav': 'quyish_rasxod',
            'today': timezone.localdate(),
        })


class QuyishRasxodDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(QuyishRasxod, pk=pk).delete()
        messages.success(request, 'Rasxod o\'chirildi.')
        return redirect('casting:quyish_rasxod_list')


# ── Order Manage (Casting Manager) ───────────────────────────────────────────

class OrderManageListView(CastingManagerRequiredMixin, View):
    """Barcha buyurtmalar ro'yxati — casting manager boshqaruvi."""

    def get(self, request):
        q        = request.GET.get('q', '').strip()
        status_f = request.GET.get('status', '')
        prio_f   = request.GET.get('priority', '')

        qs = Order.objects.select_related('brujka', 'created_by').all()
        if q:
            qs = qs.filter(name__icontains=q)
        if status_f:
            qs = qs.filter(status=status_f)
        if prio_f:
            qs = qs.filter(priority=prio_f)

        counts = {s: Order.objects.filter(status=s).count() for s, _ in Order.Status.choices}
        return render(request, 'casting/order_manage_list.html', {
            'orders':    qs.order_by('-created_at'),
            'q':         q,
            'status_f':  status_f,
            'prio_f':    prio_f,
            'counts':    counts,
            'statuses':  Order.Status.choices,
            'priorities': Order.Priority.choices,
            'active_nav': 'order_manage',
        })


class OrderCreateView(CastingManagerRequiredMixin, View):
    """Yangi buyurtma yaratish — status avtomatik 'accepted' bo'ladi."""

    def get(self, request):
        form = OrderForm()
        return render(request, 'casting/order_form.html', {
            'form':      form,
            'title':     'Yangi buyurtma',
            'active_nav': 'order_manage',
        })

    def post(self, request):
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            order = form.save(commit=False)
            order.status     = Order.Status.ACCEPTED
            order.created_by = request.user
            order.save()
            messages.success(request, f'"{order.name}" buyurtmasi yaratildi — Qabul qilindi.')
            return redirect('casting:order_manage_list')
        return render(request, 'casting/order_form.html', {
            'form':      form,
            'title':     'Yangi buyurtma',
            'active_nav': 'order_manage',
        })


class OrderUpdateView(CastingManagerRequiredMixin, View):
    """Buyurtmani tahrirlash — har qanday orderni, lekin status faqat o'zinikida."""

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form  = OrderForm(instance=order)
        return render(request, 'casting/order_form.html', {
            'form':      form,
            'order':     order,
            'title':     f'{order.name} — tahrirlash',
            'active_nav': 'order_manage',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form  = OrderForm(request.POST, request.FILES, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{order.name}" yangilandi.')
            return redirect('casting:order_manage_list')
        return render(request, 'casting/order_form.html', {
            'form':      form,
            'order':     order,
            'title':     f'{order.name} — tahrirlash',
            'active_nav': 'order_manage',
        })


class OrderDeleteView(CastingManagerRequiredMixin, View):
    """Buyurtmani o'chirish — faqat o'zi yaratgan buyurtmani."""

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        return render(request, 'casting/order_confirm_delete.html', {
            'order':     order,
            'active_nav': 'order_manage',
        })

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        name  = order.name
        order.delete()
        messages.success(request, f'"{name}" buyurtmasi o\'chirildi.')
        return redirect('casting:order_manage_list')


class OrderSetStatusView2(CastingManagerRequiredMixin, View):
    """Status o'zgartirish — faqat o'zi yaratgan orderlar."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, created_by=request.user)
        new_status = request.POST.get('status', '')
        allowed    = [s for s, _ in Order.Status.choices]
        if new_status in allowed:
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f'Holat: {order.get_status_display()}')
        else:
            messages.error(request, 'Noto\'g\'ri holat.')
        next_url = request.POST.get('next', '')
        if next_url:
            return redirect(next_url)
        return redirect('casting:order_manage_list')


# ── Brujkalar ─────────────────────────────────────────────────────────────────

class BrujkaListView(CastingManagerRequiredMixin, View):
    def get(self, request):
        q  = request.GET.get('q', '').strip()
        ct = request.GET.get('coating', '')
        qs = Brujka.objects.all()
        if q:
            qs = qs.filter(name__icontains=q)
        if ct:
            qs = qs.filter(coating_type=ct)
        counts = {
            'total':    Brujka.objects.count(),
            'active':   Brujka.objects.filter(is_active=True).count(),
            'inactive': Brujka.objects.filter(is_active=False).count(),
        }
        return render(request, 'casting/brujka_list.html', {
            'brujkalar':   qs.order_by('name'),
            'q':           q,
            'ct':          ct,
            'counts':      counts,
            'coating_choices': Brujka.CoatingType.choices,
            'active_nav':  'brujkalar',
        })


class BrujkaDetailView(CastingManagerRequiredMixin, View):
    def get(self, request, pk):
        brujka = get_object_or_404(Brujka, pk=pk)
        orders = Order.objects.filter(brujka=brujka).select_related('created_by').order_by('-created_at')[:30]
        return render(request, 'casting/brujka_detail.html', {
            'brujka':         brujka,
            'orders':         orders,
            'order_statuses': Order.Status.choices,
            'active_nav':     'brujkalar',
        })


class BrujkaSearchAPIView(CastingManagerRequiredMixin, View):
    """AJAX brujka qidiruv — order form uchun."""

    def get(self, request):
        q  = request.GET.get('q', '').strip()
        qs = Brujka.objects.filter(is_active=True)
        if q:
            qs = qs.filter(name__icontains=q)
        data = [
            {
                'id':      b.pk,
                'name':    b.name,
                'color':   b.color,
                'coating': b.get_coating_type_display(),
                'image':   b.image.url if b.image else '',
            }
            for b in qs.order_by('name')[:25]
        ]
        return JsonResponse({'results': data})


# ── Quyish Jarayon ────────────────────────────────────────────────────────────

class QuyishJarayonListView(CastingManagerRequiredMixin, View):
    """Quyish masteri uchun — barcha in_process orderlar quyish holati bilan."""

    def get(self, request):
        tab = request.GET.get('tab', 'quyilmoqda')
        q   = request.GET.get('q', '').strip()
        if tab not in ('quyilmoqda', 'quyib_bolindi', 'quyilmadi'):
            tab = 'quyilmoqda'

        # in_process bo'lgan orderlarda QuyishJarayon avtomatik yaratiladi
        in_process = Order.objects.filter(status=Order.Status.IN_PROCESS)
        for order in in_process:
            QuyishJarayon.objects.get_or_create(
                order=order,
                defaults={'created_by': request.user},
            )

        qs = QuyishJarayon.objects.select_related(
            'order', 'order__brujka', 'updated_by'
        ).filter(order__status=Order.Status.IN_PROCESS, status=tab)

        if q:
            qs = qs.filter(order__name__icontains=q)

        counts = {
            s: QuyishJarayon.objects.filter(
                order__status=Order.Status.IN_PROCESS, status=s
            ).count()
            for s, _ in QuyishJarayon.Status.choices
        }

        return render(request, 'casting/quyish_jarayon_list.html', {
            'jarayonlar': qs,
            'tab':        tab,
            'q':          q,
            'counts':     counts,
            'active_nav': 'quyish_jarayon',
        })


class QuyishJarayonSetStatusView(CastingManagerRequiredMixin, View):
    """Quyish holati: quyilmoqda / quyib_bolindi / quyilmadi."""

    def post(self, request, pk):
        jarayon    = get_object_or_404(QuyishJarayon, pk=pk)
        new_status = request.POST.get('status', '')
        izoh       = request.POST.get('izoh', '').strip()
        next_tab   = request.POST.get('next_tab', 'quyilmoqda')

        allowed = {s for s, _ in QuyishJarayon.Status.choices}
        if new_status in allowed:
            jarayon.status     = new_status
            jarayon.izoh       = izoh
            jarayon.updated_by = request.user
            jarayon.save(update_fields=['status', 'izoh', 'updated_by', 'updated_at'])
            messages.success(request, f'Holat: {jarayon.get_status_display()}')
        else:
            messages.error(request, "Noto'g'ri holat.")

        from django.urls import reverse
        return redirect(f"{reverse('casting:quyish_jarayon_list')}?tab={next_tab}&q={request.POST.get('q', '')}")


class QuyishJarayonDetailView(CastingManagerRequiredMixin, View):
    """Quyish jarayoni detail — loglar ro'yxati va log qo'shish."""

    def get(self, request, pk):
        jarayon = get_object_or_404(
            QuyishJarayon.objects.select_related('order', 'order__brujka', 'created_by', 'updated_by'),
            pk=pk,
        )
        loglar     = jarayon.loglar.select_related('created_by').order_by('-created_at')
        jami_miqdor = loglar.aggregate(j=Sum('miqdor'))['j'] or 0
        return render(request, 'casting/quyish_jarayon_detail.html', {
            'jarayon':    jarayon,
            'loglar':     loglar,
            'jami_miqdor': jami_miqdor,
            'today':      timezone.localdate(),
            'active_nav': 'quyish_jarayon',
        })


class QuyishJarayonLogCreateView(CastingManagerRequiredMixin, View):
    """Log yozish: miqdor + ixtiyoriy natija (tugatildi / bekor qilindi)."""

    def post(self, request, pk):
        jarayon = get_object_or_404(QuyishJarayon, pk=pk)
        try:
            miqdor = int(request.POST.get('miqdor', 0))
            assert miqdor >= 0
        except (ValueError, AssertionError):
            messages.error(request, "Miqdor 0 yoki undan katta son bo'lishi kerak.")
            return redirect('casting:quyish_jarayon_detail', pk=pk)

        natija = request.POST.get('natija', '').strip() or None
        izoh   = request.POST.get('izoh', '').strip()

        allowed_natija = {n for n, _ in QuyishJarayonLog.Natija.choices}
        if natija and natija not in allowed_natija:
            natija = None

        QuyishJarayonLog.objects.create(
            jarayon=jarayon,
            miqdor=miqdor,
            natija=natija,
            izoh=izoh,
            created_by=request.user,
        )

        # Natijaga qarab jarayon statusini yangilash
        if natija == QuyishJarayonLog.Natija.TUGATILDI:
            jarayon.status     = QuyishJarayon.Status.QUYIB_BOLINDI
            jarayon.updated_by = request.user
            jarayon.save(update_fields=['status', 'updated_by', 'updated_at'])
            messages.success(request, f'{miqdor} dona quyildi — Tugatildi ✓')
        elif natija == QuyishJarayonLog.Natija.BEKOR_QILINDI:
            jarayon.status     = QuyishJarayon.Status.QUYILMADI
            jarayon.updated_by = request.user
            jarayon.save(update_fields=['status', 'updated_by', 'updated_at'])
            messages.success(request, f'Jarayon bekor qilindi.')
        else:
            messages.success(request, f'{miqdor} dona log yozildi.')

        return redirect('casting:quyish_jarayon_detail', pk=pk)


class QuyishJarayonLogDeleteView(CastingManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(QuyishJarayonLog, pk=log_pk, jarayon_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('casting:quyish_jarayon_detail', pk=pk)
