import datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.order.models import Order
from .forms import SepishLogForm, KraskaForm
from .models import SepishJarayon, SepishJarayonLog, Kraska


class SprayManagerRequiredMixin(LoginRequiredMixin):
    """CEO va SPRAYMANAGER rollari kirishi mumkin."""
    login_url = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'SPRAYMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        role = request.user.role.name if getattr(request.user, 'role', None) else None
        if not (request.user.is_superuser or role in self.ALLOWED_ROLES):
            messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# ── Jarayon list ──

class SepishJarayonListView(SprayManagerRequiredMixin, View):
    def get(self, request):
        tab = request.GET.get('tab', 'qabul_qilindi')
        q   = request.GET.get('q', '').strip()

        # Quyish QUYILMOQDA yoki QUYIB_BOLINDI bo'lgan orderlar uchun avtomatik yaratish
        try:
            from apps.casting.models import QuyishJarayon
            quyish_orders = Order.objects.filter(
                quyish_jarayon__status__in=[
                    QuyishJarayon.Status.QUYILMOQDA,
                    QuyishJarayon.Status.QUYIB_BOLINDI,
                ]
            )
            for order in quyish_orders:
                SepishJarayon.objects.get_or_create(
                    order=order, defaults={'created_by': request.user}
                )
        except Exception:
            pass

        # IN_PROCESS va READY statusli barcha orderlar
        for order in Order.objects.filter(status__in=[Order.Status.IN_PROCESS, Order.Status.READY]):
            SepishJarayon.objects.get_or_create(
                order=order, defaults={'created_by': request.user}
            )
        # ACCEPTED ham
        for order in Order.objects.filter(status=Order.Status.ACCEPTED):
            SepishJarayon.objects.get_or_create(
                order=order, defaults={'created_by': request.user}
            )

        qs = SepishJarayon.objects.select_related(
            'order', 'order__brujka', 'updated_by',
            'order__quyish_jarayon',
        )
        if q:
            qs = qs.filter(
                Q(order__name__icontains=q) | Q(order__order_number__icontains=q)
            )

        valid_tabs = {s.value for s in SepishJarayon.Status}
        if tab not in valid_tabs:
            tab = 'qabul_qilindi'

        jarayonlar = qs.filter(status=tab)
        counts     = {s.value: qs.filter(status=s.value).count() for s in SepishJarayon.Status}
        kraskalar  = Kraska.objects.filter(is_active=True)

        return render(request, 'sepish/jarayon_list.html', {
            'active_nav': 'jarayonlar',
            'tab':        tab,
            'q':          q,
            'jarayonlar': jarayonlar,
            'counts':     counts,
            'kraskalar':  kraskalar,
            'today':      timezone.now().date().isoformat(),
        })


# ── Jarayon detail ──

class SepishJarayonDetailView(SprayManagerRequiredMixin, View):
    def get(self, request, pk):
        jarayon = get_object_or_404(
            SepishJarayon.objects.select_related('order', 'order__brujka'), pk=pk
        )
        loglar = jarayon.loglar.select_related(
            'kraska', 'created_by', 'updated_by'
        ).order_by('-sana', '-created_at')

        loglar_list  = list(loglar)
        kun_loglar   = [l for l in loglar_list if l.smena == 'kun']
        tun_loglar   = [l for l in loglar_list if l.smena == 'tun']

        kun_par      = sum(l.par_soni for l in kun_loglar)
        tun_par      = sum(l.par_soni for l in tun_loglar)
        kun_gramm    = sum(l.kraska_gramm for l in kun_loglar)
        tun_gramm    = sum(l.kraska_gramm for l in tun_loglar)
        total_par    = kun_par + tun_par
        total_gramm  = kun_gramm + tun_gramm

        target_par   = jarayon.order.quantity
        qoldiq_par   = max(0, target_par - total_par)
        progress_pct = min(100, round(total_par / target_par * 100)) if target_par else 0

        # Kraska sarfi — har bir kraska bo'yicha
        kraska_sarfi = {}
        for log in loglar_list:
            if log.kraska:
                k = log.kraska
                if k.pk not in kraska_sarfi:
                    kraska_sarfi[k.pk] = {'kraska': k, 'gramm': 0, 'par': 0}
                kraska_sarfi[k.pk]['gramm'] += log.kraska_gramm
                kraska_sarfi[k.pk]['par']   += log.par_soni

        form = SepishLogForm(initial={'sana': timezone.now().date()})

        return render(request, 'sepish/jarayon_detail.html', {
            'active_nav':    'jarayonlar',
            'jarayon':       jarayon,
            'loglar':        loglar_list,
            'form':          form,
            'total_par':     total_par,
            'total_gramm':   total_gramm,
            'kun_par':       kun_par,
            'tun_par':       tun_par,
            'kun_gramm':     kun_gramm,
            'tun_gramm':     tun_gramm,
            'kun_count':     len(kun_loglar),
            'tun_count':     len(tun_loglar),
            'target_par':    target_par,
            'qoldiq_par':    qoldiq_par,
            'progress_pct':  progress_pct,
            'kraska_sarfi':  list(kraska_sarfi.values()),
        })


# ── Status o'zgartirish ──

class SepishJarayonSetStatusView(SprayManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon  = get_object_or_404(SepishJarayon, pk=pk)
        status   = request.POST.get('status', '').strip()
        izoh     = request.POST.get('izoh', '').strip()
        next_tab = request.POST.get('next_tab', 'qabul_qilindi')

        valid = {s.value for s in SepishJarayon.Status}
        if status in valid:
            jarayon.status     = status
            jarayon.izoh       = izoh
            jarayon.updated_by = request.user
            jarayon.save()
            messages.success(request, f'Holat: {jarayon.get_status_display()}')
        else:
            messages.error(request, "Noto'g'ri holat.")

        return redirect(f'{reverse_lazy("sepish:jarayon_list")}?tab={next_tab}')


# ── Log create ──

class SepishLogCreateView(SprayManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(SepishJarayon, pk=pk)
        form    = SepishLogForm(request.POST)
        if form.is_valid():
            log            = form.save(commit=False)
            log.jarayon    = jarayon
            log.created_by = request.user
            log.updated_by = request.user
            log.save()

            if jarayon.status == SepishJarayon.Status.QABUL_QILINDI:
                jarayon.status     = SepishJarayon.Status.SEPILMOQDA
                jarayon.updated_by = request.user
                jarayon.save()

            messages.success(request, "Log muvaffaqiyatli qo'shildi.")
        else:
            messages.error(request, 'Xato: ' + str(form.errors))
        return redirect('sepish:jarayon_detail', pk=pk)


# ── Log update — faqat o'ziniki ──

class SepishLogUpdateView(SprayManagerRequiredMixin, View):
    def get(self, request, pk, log_pk):
        jarayon = get_object_or_404(SepishJarayon, pk=pk)
        log     = get_object_or_404(SepishJarayonLog, pk=log_pk, jarayon=jarayon)

        # Faqat o'zi yaratgan logni tahrirlaydi (superuser ham barchani)
        if not request.user.is_superuser and log.created_by != request.user:
            messages.error(request, "Siz faqat o'z loginzni tahrirlashingiz mumkin.")
            return redirect('sepish:jarayon_detail', pk=pk)

        form = SepishLogForm(instance=log)
        return render(request, 'sepish/log_form.html', {
            'active_nav': 'jarayonlar',
            'jarayon':    jarayon,
            'log':        log,
            'form':       form,
        })

    def post(self, request, pk, log_pk):
        jarayon = get_object_or_404(SepishJarayon, pk=pk)
        log     = get_object_or_404(SepishJarayonLog, pk=log_pk, jarayon=jarayon)

        if not request.user.is_superuser and log.created_by != request.user:
            messages.error(request, "Siz faqat o'z loginzni tahrirlashingiz mumkin.")
            return redirect('sepish:jarayon_detail', pk=pk)

        form = SepishLogForm(request.POST, instance=log)
        if form.is_valid():
            updated       = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(request, 'Log yangilandi.')
            return redirect('sepish:jarayon_detail', pk=pk)

        return render(request, 'sepish/log_form.html', {
            'active_nav': 'jarayonlar',
            'jarayon':    jarayon,
            'log':        log,
            'form':       form,
        })


# ── Log delete ──

class SepishLogDeleteView(SprayManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(SepishJarayonLog, pk=log_pk, jarayon_id=pk)
        if not request.user.is_superuser and log.created_by != request.user:
            messages.error(request, "Siz faqat o'z loginzni o'chirishingiz mumkin.")
            return redirect('sepish:jarayon_detail', pk=pk)
        log.delete()
        messages.success(request, "Log o'chirildi.")
        return redirect('sepish:jarayon_detail', pk=pk)


# ── Tezkor log (modal, list sahifasidan) ──

class SepishQuickLogView(SprayManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(SepishJarayon, pk=pk)
        form    = SepishLogForm(request.POST)
        if form.is_valid():
            log            = form.save(commit=False)
            log.jarayon    = jarayon
            log.created_by = request.user
            log.updated_by = request.user
            log.save()
            if jarayon.status == SepishJarayon.Status.QABUL_QILINDI:
                jarayon.status     = SepishJarayon.Status.SEPILMOQDA
                jarayon.updated_by = request.user
                jarayon.save()
            messages.success(request, "Log saqlandi.")
        else:
            messages.error(request, 'Xato: ' + str(form.errors))
        next_tab = request.POST.get('next_tab', 'sepilmoqda')
        return redirect(f'{reverse_lazy("sepish:jarayon_list")}?tab={next_tab}')


# ── Kraskalar CRUD ──

class KraskaListView(SprayManagerRequiredMixin, ListView):
    model               = Kraska
    template_name       = 'sepish/kraska_list.html'
    context_object_name = 'kraskalar'

    def get_queryset(self):
        return Kraska.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'kraskalar'
        ctx['counts'] = {
            'jami': Kraska.objects.count(),
            'faol': Kraska.objects.filter(is_active=True).count(),
        }
        return ctx


class KraskaCreateView(SprayManagerRequiredMixin, CreateView):
    model         = Kraska
    form_class    = KraskaForm
    template_name = 'sepish/kraska_form.html'
    success_url   = reverse_lazy('sepish:kraska_list')

    def form_valid(self, form):
        messages.success(self.request, "Kraska qo'shildi.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'kraskalar'
        ctx['title']      = 'Yangi kraska'
        return ctx


class KraskaUpdateView(SprayManagerRequiredMixin, UpdateView):
    model         = Kraska
    form_class    = KraskaForm
    template_name = 'sepish/kraska_form.html'
    success_url   = reverse_lazy('sepish:kraska_list')

    def form_valid(self, form):
        messages.success(self.request, 'Kraska yangilandi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'kraskalar'
        ctx['title']      = 'Kraskani tahrirlash'
        return ctx


class KraskaDeleteView(SprayManagerRequiredMixin, View):
    def post(self, request, pk):
        kraska = get_object_or_404(Kraska, pk=pk)
        kraska.delete()
        messages.success(request, "Kraska o'chirildi.")
        return redirect('sepish:kraska_list')


# ── Statistika ──

class SepishStatsView(SprayManagerRequiredMixin, View):
    def get(self, request):
        today     = timezone.now().date()
        days      = int(request.GET.get('days', 14))
        date_from = today - datetime.timedelta(days=days - 1)

        loglar = SepishJarayonLog.objects.filter(
            sana__gte=date_from, sana__lte=today
        ).select_related('kraska', 'created_by', 'jarayon__order')

        kun_loglar = list(loglar.filter(smena='kun'))
        tun_loglar = list(loglar.filter(smena='tun'))
        all_loglar = kun_loglar + tun_loglar

        kun_par   = sum(l.par_soni for l in kun_loglar)
        tun_par   = sum(l.par_soni for l in tun_loglar)
        kun_gramm = sum(l.kraska_gramm for l in kun_loglar)
        tun_gramm = sum(l.kraska_gramm for l in tun_loglar)
        umumiy_par   = kun_par + tun_par
        umumiy_gramm = kun_gramm + tun_gramm

        date_range   = [date_from + datetime.timedelta(days=i) for i in range(days)]
        chart_labels = [d.strftime('%d.%m') for d in date_range]
        kun_by_day   = [sum(l.par_soni for l in kun_loglar if l.sana == d) for d in date_range]
        tun_by_day   = [sum(l.par_soni for l in tun_loglar if l.sana == d) for d in date_range]

        status_counts = {s.value: SepishJarayon.objects.filter(status=s.value).count()
                         for s in SepishJarayon.Status}

        # Kraska sarfi ro'yxati
        kraska_sarfi = {}
        for log in all_loglar:
            if log.kraska:
                k = log.kraska
                if k.pk not in kraska_sarfi:
                    kraska_sarfi[k.pk] = {'kraska': k, 'gramm': 0, 'par': 0}
                kraska_sarfi[k.pk]['gramm'] += log.kraska_gramm
                kraska_sarfi[k.pk]['par']   += log.par_soni
        kraska_sarfi = sorted(kraska_sarfi.values(), key=lambda x: x['gramm'], reverse=True)

        # Order statistikasi
        order_stats = []
        jarayonlar = SepishJarayon.objects.filter(
            loglar__sana__gte=date_from
        ).distinct().select_related('order', 'order__brujka')
        for j in jarayonlar:
            j_logs = [l for l in all_loglar if l.jarayon_id == j.pk]
            order_stats.append({
                'jarayon': j,
                'par':     sum(l.par_soni for l in j_logs),
                'gramm':   sum(l.kraska_gramm for l in j_logs),
            })
        order_stats.sort(key=lambda x: x['par'], reverse=True)

        return render(request, 'sepish/stats.html', {
            'active_nav':    'stats',
            'days':          days,
            'date_from':     date_from,
            'today':         today,
            'kun_par':       kun_par,
            'tun_par':       tun_par,
            'kun_gramm':     kun_gramm,
            'tun_gramm':     tun_gramm,
            'umumiy_par':    umumiy_par,
            'umumiy_gramm':  umumiy_gramm,
            'chart_labels':  chart_labels,
            'kun_by_day':    kun_by_day,
            'tun_by_day':    tun_by_day,
            'status_counts': status_counts,
            'kraska_sarfi':  kraska_sarfi,
            'order_stats':   order_stats,
        })
