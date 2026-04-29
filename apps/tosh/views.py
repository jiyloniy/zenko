import datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.order.models import Order
from apps.users.models import User
from .forms import ToshForm, ToshLogForm, KleyRasxodForm, ToshRasxodForm
from .models import (
    Tosh, ToshQadashJarayon, ToshQadashLog,
    KleyRasxod, ToshRasxod, QabulJarayon,
)


class ToshManagerRequiredMixin(LoginRequiredMixin):
    """CEO va TOSHMANAGER rollari kirishi mumkin."""
    login_url    = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'TOSHMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        user      = request.user
        role_name = user.role.name if getattr(user, 'role', None) else None
        if not (user.is_superuser or role_name in self.ALLOWED_ROLES):
            messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# ─────────────────────────────────────────────
# Tosh qadash jarayonlari
# ─────────────────────────────────────────────

class ToshJarayonListView(ToshManagerRequiredMixin, View):
    def get(self, request):
        from apps.casting.models import QuyishJarayon

        tab = request.GET.get('tab', 'qabul_qilindi')
        q   = request.GET.get('q', '').strip()

        # Quyilgan orderlar uchun avtomatik ToshQadashJarayon yaratish
        quyilgan_orders = Order.objects.filter(
            status__in=[Order.Status.IN_PROCESS, Order.Status.READY],
            quyish_jarayon__status__in=[
                QuyishJarayon.Status.QUYIB_BOLINDI,
            ],
        )
        for order in quyilgan_orders:
            ToshQadashJarayon.objects.get_or_create(
                order=order,
                defaults={'created_by': request.user},
            )
        for order in Order.objects.filter(status=Order.Status.READY):
            ToshQadashJarayon.objects.get_or_create(
                order=order,
                defaults={'created_by': request.user},
            )

        qs = ToshQadashJarayon.objects.select_related(
            'order', 'order__brujka', 'updated_by',
        ).order_by('-order__deadline', '-updated_at')

        if q:
            qs = qs.filter(
                Q(order__name__icontains=q) |
                Q(order__order_number__icontains=q)
            )

        valid_tabs = {s.value for s in ToshQadashJarayon.Status}
        if tab not in valid_tabs:
            tab = 'qabul_qilindi'

        jarayonlar = qs.filter(status=tab)

        counts = {s.value: qs.filter(status=s.value).count() for s in ToshQadashJarayon.Status}

        hodimlar = User.objects.all().order_by('name')
        toshlar  = Tosh.objects.filter(is_active=True).order_by('name')

        return render(request, 'tosh/jarayon_list.html', {
            'active_nav': 'jarayonlar',
            'tab':        tab,
            'q':          q,
            'jarayonlar': jarayonlar,
            'counts':     counts,
            'hodimlar':   hodimlar,
            'toshlar':    toshlar,
            'today':      timezone.now().date().isoformat(),
        })


class ToshJarayonDetailView(ToshManagerRequiredMixin, View):
    def get(self, request, pk):
        jarayon = get_object_or_404(
            ToshQadashJarayon.objects.select_related('order', 'order__brujka'),
            pk=pk,
        )
        loglar       = jarayon.loglar.select_related('hodim', 'tosh').order_by('-sana', '-created_at')
        kley_rasxod  = jarayon.kley_rasxodlar.all().order_by('-sana', '-created_at')
        tosh_rasxod  = jarayon.tosh_rasxodlar.select_related('tosh').order_by('-sana', '-created_at')

        loglar_list = list(loglar)
        kun_loglar  = [l for l in loglar_list if l.smena == 'kun']
        tun_loglar  = [l for l in loglar_list if l.smena == 'tun']

        kun_par   = sum(l.par_soni for l in kun_loglar)
        tun_par   = sum(l.par_soni for l in tun_loglar)
        total_par = kun_par + tun_par

        target_par   = jarayon.order.quantity
        qoldiq_par   = max(0, target_par - total_par)
        progress_pct = min(100, round(total_par / target_par * 100)) if target_par else 0

        # Kley totals
        kley_list    = list(kley_rasxod)
        kun_kley     = sum(float(k.kley_gramm) for k in kley_list if k.smena == 'kun')
        tun_kley     = sum(float(k.kley_gramm) for k in kley_list if k.smena == 'tun')
        total_kley   = kun_kley + tun_kley

        # Tosh rasxod totals
        tr_list      = list(tosh_rasxod)
        kun_tr       = sum(float(t.tosh_gramm) for t in tr_list if t.smena == 'kun')
        tun_tr       = sum(float(t.tosh_gramm) for t in tr_list if t.smena == 'tun')
        total_tr     = kun_tr + tun_tr

        hodimlar = User.objects.all().order_by('name')
        toshlar  = Tosh.objects.filter(is_active=True).order_by('name')

        try:
            qabul = jarayon.qabul_jarayon
        except QabulJarayon.DoesNotExist:
            qabul = None

        return render(request, 'tosh/jarayon_detail.html', {
            'active_nav':   'jarayonlar',
            'jarayon':      jarayon,
            'loglar':       loglar_list,
            'kun_loglar':   kun_loglar,
            'tun_loglar':   tun_loglar,
            'kun_par':      kun_par,
            'tun_par':      tun_par,
            'total_par':    total_par,
            'target_par':   target_par,
            'qoldiq_par':   qoldiq_par,
            'progress_pct': progress_pct,
            'kley_rasxod':  kley_list,
            'kun_kley':     kun_kley,
            'tun_kley':     tun_kley,
            'total_kley':   total_kley,
            'tosh_rasxod':  tr_list,
            'kun_tr':       kun_tr,
            'tun_tr':       tun_tr,
            'total_tr':     total_tr,
            'hodimlar':     hodimlar,
            'toshlar':      toshlar,
            'qabul':        qabul,
            'today':        timezone.now().date().isoformat(),
        })


class ToshJarayonSetStatusView(ToshManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon  = get_object_or_404(ToshQadashJarayon, pk=pk)
        status   = request.POST.get('status', '').strip()
        izoh     = request.POST.get('izoh', '').strip()
        next_tab = request.POST.get('next_tab', 'qabul_qilindi')

        valid = {s.value for s in ToshQadashJarayon.Status}
        if status in valid:
            jarayon.status     = status
            jarayon.izoh       = izoh
            jarayon.updated_by = request.user
            jarayon.save()

            # Tosh qadaldi bo'lsa, QabulJarayon yaratish
            if status == ToshQadashJarayon.Status.TOSH_QADALDI:
                QabulJarayon.objects.get_or_create(
                    tosh_jarayon=jarayon,
                    defaults={'updated_by': request.user},
                )
            messages.success(request, f'Holat: {jarayon.get_status_display()}')
        else:
            messages.error(request, 'Noto\'g\'ri holat.')

        return redirect(f'{reverse_lazy("tosh:jarayon_list")}?tab={next_tab}')


# ─────────────────────────────────────────────
# Log CRUD
# ─────────────────────────────────────────────

class ToshLogCreateView(ToshManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(ToshQadashJarayon, pk=pk)
        form    = ToshLogForm(request.POST)
        if form.is_valid():
            log            = form.save(commit=False)
            log.jarayon    = jarayon
            log.created_by = request.user
            log.save()

            if jarayon.status == ToshQadashJarayon.Status.QABUL_QILINDI:
                jarayon.status     = ToshQadashJarayon.Status.TOSH_QADALMOQDA
                jarayon.updated_by = request.user
                jarayon.save()

            messages.success(request, 'Log muvaffaqiyatli qo\'shildi.')
        else:
            messages.error(request, 'Xato: ' + str(form.errors))

        return redirect('tosh:jarayon_detail', pk=pk)


class ToshLogDeleteView(ToshManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(ToshQadashLog, pk=log_pk, jarayon_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('tosh:jarayon_detail', pk=pk)


class ToshBulkLogCreateView(ToshManagerRequiredMixin, View):
    """Bir necha hodim uchun bir vaqtda log kiritish."""
    def post(self, request, pk):
        jarayon   = get_object_or_404(ToshQadashJarayon, pk=pk)
        sana_str  = request.POST.get('sana', timezone.now().date().isoformat())
        smena     = request.POST.get('smena', 'kun')
        tosh_id   = request.POST.get('tosh', '')
        izoh      = request.POST.get('izoh', '').strip()

        try:
            sana = datetime.date.fromisoformat(sana_str)
        except ValueError:
            sana = timezone.now().date()

        tosh_obj = None
        if tosh_id:
            try:
                tosh_obj = Tosh.objects.get(pk=tosh_id, is_active=True)
            except Tosh.DoesNotExist:
                pass

        hodim_ids  = request.POST.getlist('hodim_ids')
        par_sonlar = request.POST.getlist('par_sonlar')

        saved = 0
        for i, hodim_id in enumerate(hodim_ids):
            if not hodim_id:
                continue
            try:
                par = int(par_sonlar[i]) if i < len(par_sonlar) else 1
            except (ValueError, TypeError):
                par = 1
            if par < 1:
                continue
            try:
                hodim = User.objects.get(pk=hodim_id)
            except User.DoesNotExist:
                continue
            ToshQadashLog.objects.create(
                jarayon=jarayon,
                hodim=hodim,
                smena=smena,
                tosh=tosh_obj,
                par_soni=par,
                sana=sana,
                izoh=izoh,
                created_by=request.user,
            )
            saved += 1

        if saved:
            if jarayon.status == ToshQadashJarayon.Status.QABUL_QILINDI:
                jarayon.status     = ToshQadashJarayon.Status.TOSH_QADALMOQDA
                jarayon.updated_by = request.user
                jarayon.save()
            messages.success(request, f'{saved} ta hodim uchun log saqlandi.')
        else:
            messages.error(request, 'Hech qanday log saqlanmadi.')

        return redirect('tosh:jarayon_detail', pk=pk)


# ─────────────────────────────────────────────
# Kley rasxod
# ─────────────────────────────────────────────

class KleyRasxodCreateView(ToshManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(ToshQadashJarayon, pk=pk)
        form    = KleyRasxodForm(request.POST)
        if form.is_valid():
            obj            = form.save(commit=False)
            obj.jarayon    = jarayon
            obj.created_by = request.user
            obj.save()
            messages.success(request, 'Kley rasxodi qo\'shildi.')
        else:
            messages.error(request, 'Xato: ' + str(form.errors))
        return redirect('tosh:jarayon_detail', pk=pk)


class KleyRasxodDeleteView(ToshManagerRequiredMixin, View):
    def post(self, request, pk, r_pk):
        obj = get_object_or_404(KleyRasxod, pk=r_pk, jarayon_id=pk)
        obj.delete()
        messages.success(request, 'Kley rasxodi o\'chirildi.')
        return redirect('tosh:jarayon_detail', pk=pk)


# ─────────────────────────────────────────────
# Tosh rasxod
# ─────────────────────────────────────────────

class ToshRasxodCreateView(ToshManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(ToshQadashJarayon, pk=pk)
        form    = ToshRasxodForm(request.POST)
        if form.is_valid():
            obj            = form.save(commit=False)
            obj.jarayon    = jarayon
            obj.created_by = request.user
            obj.save()
            messages.success(request, 'Tosh rasxodi qo\'shildi.')
        else:
            messages.error(request, 'Xato: ' + str(form.errors))
        return redirect('tosh:jarayon_detail', pk=pk)


class ToshRasxodDeleteView(ToshManagerRequiredMixin, View):
    def post(self, request, pk, r_pk):
        obj = get_object_or_404(ToshRasxod, pk=r_pk, jarayon_id=pk)
        obj.delete()
        messages.success(request, 'Tosh rasxodi o\'chirildi.')
        return redirect('tosh:jarayon_detail', pk=pk)


# ─────────────────────────────────────────────
# Qabul jarayoni
# ─────────────────────────────────────────────

class QabulJarayonListView(ToshManagerRequiredMixin, View):
    def get(self, request):
        tab = request.GET.get('tab', 'ilinmoqda')
        q   = request.GET.get('q', '').strip()

        # Tosh qadaldi bo'lganlarga avtomatik QabulJarayon yaratish
        for tj in ToshQadashJarayon.objects.filter(status=ToshQadashJarayon.Status.TOSH_QADALDI):
            QabulJarayon.objects.get_or_create(
                tosh_jarayon=tj,
                defaults={'updated_by': request.user},
            )

        qs = QabulJarayon.objects.select_related(
            'tosh_jarayon__order', 'tosh_jarayon__order__brujka', 'updated_by',
        ).order_by('-tosh_jarayon__order__deadline', '-updated_at')

        if q:
            qs = qs.filter(
                Q(tosh_jarayon__order__name__icontains=q) |
                Q(tosh_jarayon__order__order_number__icontains=q)
            )

        valid_tabs = {s.value for s in QabulJarayon.Status}
        if tab not in valid_tabs:
            tab = 'ilinmoqda'

        jarayonlar = qs.filter(status=tab)
        counts     = {s.value: qs.filter(status=s.value).count() for s in QabulJarayon.Status}

        return render(request, 'tosh/qabul_list.html', {
            'active_nav': 'qabul',
            'tab':        tab,
            'q':          q,
            'jarayonlar': jarayonlar,
            'counts':     counts,
            'today':      timezone.now().date().isoformat(),
        })


class QabulJarayonSetStatusView(ToshManagerRequiredMixin, View):
    def post(self, request, pk):
        qabul    = get_object_or_404(QabulJarayon, pk=pk)
        status   = request.POST.get('status', '').strip()
        izoh     = request.POST.get('izoh', '').strip()
        next_tab = request.POST.get('next_tab', 'ilinmoqda')

        valid = {s.value for s in QabulJarayon.Status}
        if status in valid:
            qabul.status     = status
            qabul.izoh       = izoh
            qabul.updated_by = request.user
            qabul.save()
            messages.success(request, f'Holat: {qabul.get_status_display()}')
        else:
            messages.error(request, 'Noto\'g\'ri holat.')

        return redirect(f'{reverse_lazy("tosh:qabul_list")}?tab={next_tab}')


# ─────────────────────────────────────────────
# Toshlar ro'yhati CRUD
# ─────────────────────────────────────────────

class ToshListView(ToshManagerRequiredMixin, ListView):
    model               = Tosh
    template_name       = 'tosh/tosh_list.html'
    context_object_name = 'toshlar'

    def get_queryset(self):
        return Tosh.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'toshlar'
        ctx['counts']     = {
            'jami': Tosh.objects.count(),
            'faol': Tosh.objects.filter(is_active=True).count(),
        }
        return ctx


class ToshCreateView(ToshManagerRequiredMixin, View):
    def get(self, request):
        return render(request, 'tosh/tosh_form.html', {
            'active_nav': 'toshlar',
            'form':       ToshForm(),
            'title':      'Yangi tosh qo\'shish',
        })

    def post(self, request):
        form = ToshForm(request.POST)
        if form.is_valid():
            obj            = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, 'Tosh muvaffaqiyatli qo\'shildi.')
            return redirect('tosh:tosh_list')
        return render(request, 'tosh/tosh_form.html', {
            'active_nav': 'toshlar',
            'form':       form,
            'title':      'Yangi tosh qo\'shish',
        })


class ToshUpdateView(ToshManagerRequiredMixin, View):
    def get(self, request, pk):
        obj = get_object_or_404(Tosh, pk=pk)
        return render(request, 'tosh/tosh_form.html', {
            'active_nav': 'toshlar',
            'form':       ToshForm(instance=obj),
            'title':      'Toshni tahrirlash',
            'obj':        obj,
        })

    def post(self, request, pk):
        obj  = get_object_or_404(Tosh, pk=pk)
        form = ToshForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tosh yangilandi.')
            return redirect('tosh:tosh_list')
        return render(request, 'tosh/tosh_form.html', {
            'active_nav': 'toshlar',
            'form':       form,
            'title':      'Toshni tahrirlash',
            'obj':        obj,
        })


class ToshDeleteView(ToshManagerRequiredMixin, View):
    def post(self, request, pk):
        obj = get_object_or_404(Tosh, pk=pk)
        obj.delete()
        messages.success(request, 'Tosh o\'chirildi.')
        return redirect('tosh:tosh_list')


# ─────────────────────────────────────────────
# Statistika
# ─────────────────────────────────────────────

class ToshStatsView(ToshManagerRequiredMixin, View):
    def get(self, request):
        today     = timezone.now().date()
        days      = int(request.GET.get('days', 14))
        date_from = today - datetime.timedelta(days=days - 1)

        loglar = ToshQadashLog.objects.filter(
            sana__gte=date_from, sana__lte=today
        ).select_related('hodim', 'tosh', 'jarayon__order')

        kley_loglar = KleyRasxod.objects.filter(
            sana__gte=date_from, sana__lte=today
        )
        tosh_rasxod_loglar = ToshRasxod.objects.filter(
            sana__gte=date_from, sana__lte=today
        ).select_related('tosh')

        kun_loglar = loglar.filter(smena='kun')
        tun_loglar = loglar.filter(smena='tun')

        kun_par    = sum(l.par_soni for l in kun_loglar)
        tun_par    = sum(l.par_soni for l in tun_loglar)
        umumiy_par = kun_par + tun_par

        # Kley totals
        kun_kley   = float(kley_loglar.filter(smena='kun').aggregate(s=Sum('kley_gramm'))['s'] or 0)
        tun_kley   = float(kley_loglar.filter(smena='tun').aggregate(s=Sum('kley_gramm'))['s'] or 0)
        total_kley = kun_kley + tun_kley

        # Tosh rasxod totals
        kun_tr     = float(tosh_rasxod_loglar.filter(smena='kun').aggregate(s=Sum('tosh_gramm'))['s'] or 0)
        tun_tr     = float(tosh_rasxod_loglar.filter(smena='tun').aggregate(s=Sum('tosh_gramm'))['s'] or 0)
        total_tr   = kun_tr + tun_tr

        # Daily chart
        date_range   = [date_from + datetime.timedelta(days=i) for i in range(days)]
        chart_labels = [d.strftime('%d.%m') for d in date_range]

        kun_by_day  = []
        tun_by_day  = []
        kley_by_day = []

        all_loglar_list     = list(loglar)
        all_kley_list       = list(kley_loglar)

        for d in date_range:
            day_kun = [l for l in all_loglar_list if l.sana == d and l.smena == 'kun']
            day_tun = [l for l in all_loglar_list if l.sana == d and l.smena == 'tun']
            day_kley = [k for k in all_kley_list if k.sana == d]
            kun_by_day.append(sum(l.par_soni for l in day_kun))
            tun_by_day.append(sum(l.par_soni for l in day_tun))
            kley_by_day.append(sum(float(k.kley_gramm) for k in day_kley))

        # Status counts
        status_counts = {s.value: ToshQadashJarayon.objects.filter(status=s.value).count()
                         for s in ToshQadashJarayon.Status}
        qabul_counts  = {s.value: QabulJarayon.objects.filter(status=s.value).count()
                         for s in QabulJarayon.Status}

        # Hodim statistikasi
        hodim_stats = []
        hodimlar = User.objects.filter(tosh_loglar__sana__gte=date_from).distinct()
        for hodim in hodimlar:
            h_logs    = [l for l in all_loglar_list if l.hodim_id == hodim.pk]
            h_par     = sum(l.par_soni for l in h_logs)
            h_kun     = sum(l.par_soni for l in h_logs if l.smena == 'kun')
            h_tun     = sum(l.par_soni for l in h_logs if l.smena == 'tun')
            hodim_stats.append({
                'hodim': hodim,
                'par':   h_par,
                'kun':   h_kun,
                'tun':   h_tun,
            })
        hodim_stats.sort(key=lambda x: x['par'], reverse=True)

        return render(request, 'tosh/stats.html', {
            'active_nav':    'stats',
            'days':          days,
            'date_from':     date_from,
            'today':         today,
            'kun_par':       kun_par,
            'tun_par':       tun_par,
            'umumiy_par':    umumiy_par,
            'kun_kley':      kun_kley,
            'tun_kley':      tun_kley,
            'total_kley':    total_kley,
            'kun_tr':        kun_tr,
            'tun_tr':        tun_tr,
            'total_tr':      total_tr,
            'chart_labels':  chart_labels,
            'kun_by_day':    kun_by_day,
            'tun_by_day':    tun_by_day,
            'kley_by_day':   kley_by_day,
            'status_counts': status_counts,
            'qabul_counts':  qabul_counts,
            'hodim_stats':   hodim_stats,
        })
