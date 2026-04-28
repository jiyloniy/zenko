import datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.order.models import Order
from .forms import BoyashLogForm, BoyashVishilkaForm
from .models import BoyashJarayon, BoyashJarayonLog, BoyashVishilka


class BoyashManagerRequiredMixin(LoginRequiredMixin):
    """CEO va BOYASHMANAGER rollari kirishi mumkin."""
    login_url = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'BOYASHMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        user = request.user
        role_name = user.role.name if getattr(user, 'role', None) else None
        if not (user.is_superuser or role_name in self.ALLOWED_ROLES):
            messages.error(request, "Sizda bu sahifaga kirish huquqi yo'q.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# ── Jarayon list ──

class BoyashJarayonListView(BoyashManagerRequiredMixin, View):
    def get(self, request):
        tab = request.GET.get('tab', 'qabul_qilindi')
        q   = request.GET.get('q', '').strip()

        # Ilish jarayoni ILINMOQDA yoki ILIB_BOLINDI bo'lgan orderlar uchun BoyashJarayon yaratish
        try:
            from apps.ilish.models import IlishJarayon
            ilish_orders = Order.objects.filter(
                ilish_jarayon__status__in=[
                    IlishJarayon.Status.ILINMOQDA,
                    IlishJarayon.Status.ILIB_BOLINDI,
                ]
            )
            for order in ilish_orders:
                BoyashJarayon.objects.get_or_create(order=order, defaults={'created_by': request.user})
        except Exception:
            pass

        # Ilish jarayoni bo'lmagan barcha active orderlar uchun ham yaratish
        active_orders = Order.objects.filter(
            status__in=[Order.Status.IN_PROCESS, Order.Status.READY]
        ).exclude(boyash_jarayon__isnull=False)
        for order in active_orders:
            BoyashJarayon.objects.get_or_create(order=order, defaults={'created_by': request.user})

        # Ilish jarayoni yo'q, lekin accepted statusli orderlar ham
        accepted_orders = Order.objects.filter(status=Order.Status.ACCEPTED)
        for order in accepted_orders:
            BoyashJarayon.objects.get_or_create(order=order, defaults={'created_by': request.user})

        qs = BoyashJarayon.objects.select_related('order', 'order__brujka', 'updated_by')
        if q:
            qs = qs.filter(Q(order__name__icontains=q) | Q(order__order_number__icontains=q))

        valid_tabs = {s.value for s in BoyashJarayon.Status}
        if tab not in valid_tabs:
            tab = 'boyalmoqda'

        jarayonlar = qs.filter(status=tab)
        counts = {s.value: qs.filter(status=s.value).count() for s in BoyashJarayon.Status}

        vishilkalar = BoyashVishilka.objects.filter(is_active=True).order_by('quantity', 'nomi')

        return render(request, 'boyash/jarayon_list.html', {
            'active_nav':  'jarayonlar',
            'tab':         tab,
            'q':           q,
            'jarayonlar':  jarayonlar,
            'counts':      counts,
            'vishilkalar': vishilkalar,
            'today':       timezone.now().date().isoformat(),
        })


# ── Jarayon detail ──

class BoyashJarayonDetailView(BoyashManagerRequiredMixin, View):
    def get(self, request, pk):
        jarayon = get_object_or_404(
            BoyashJarayon.objects.select_related('order', 'order__brujka'), pk=pk
        )
        loglar = jarayon.loglar.select_related('vishilka', 'created_by').order_by('-sana', '-created_at')

        loglar_list  = list(loglar)
        kun_loglar   = [l for l in loglar_list if l.smena == 'kun']
        tun_loglar   = [l for l in loglar_list if l.smena == 'tun']

        kun_vishilka  = sum(l.vishilka_soni for l in kun_loglar)
        tun_vishilka  = sum(l.vishilka_soni for l in tun_loglar)
        kun_par       = sum(l.boyalgan_par for l in kun_loglar)
        tun_par       = sum(l.boyalgan_par for l in tun_loglar)
        total_vishilka = kun_vishilka + tun_vishilka
        total_par      = kun_par + tun_par

        target_par   = jarayon.order.quantity
        qoldiq_par   = max(0, target_par - total_par)
        progress_pct = min(100, round(total_par / target_par * 100)) if target_par else 0

        form = BoyashLogForm(initial={'sana': timezone.now().date()})

        return render(request, 'boyash/jarayon_detail.html', {
            'active_nav':     'jarayonlar',
            'jarayon':        jarayon,
            'loglar':         loglar_list,
            'form':           form,
            'total_vishilka': total_vishilka,
            'total_par':      total_par,
            'kun_vishilka':   kun_vishilka,
            'tun_vishilka':   tun_vishilka,
            'kun_par':        kun_par,
            'tun_par':        tun_par,
            'kun_count':      len(kun_loglar),
            'tun_count':      len(tun_loglar),
            'target_par':     target_par,
            'qoldiq_par':     qoldiq_par,
            'progress_pct':   progress_pct,
        })


# ── Status o'zgartirish ──

class BoyashJarayonSetStatusView(BoyashManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon  = get_object_or_404(BoyashJarayon, pk=pk)
        status   = request.POST.get('status', '').strip()
        izoh     = request.POST.get('izoh', '').strip()
        next_tab = request.POST.get('next_tab', 'boyalmoqda')

        valid = {s.value for s in BoyashJarayon.Status}
        if status in valid:
            jarayon.status     = status
            jarayon.izoh       = izoh
            jarayon.updated_by = request.user
            jarayon.save()
            messages.success(request, f'Holat: {jarayon.get_status_display()}')
        else:
            messages.error(request, "Noto'g'ri holat.")

        return redirect(f'{reverse_lazy("boyash:jarayon_list")}?tab={next_tab}')


# ── Log create / delete ──

class BoyashLogCreateView(BoyashManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(BoyashJarayon, pk=pk)
        form    = BoyashLogForm(request.POST)
        if form.is_valid():
            log            = form.save(commit=False)
            log.jarayon    = jarayon
            log.created_by = request.user
            log.save()

            if jarayon.status == BoyashJarayon.Status.QABUL_QILINDI:
                jarayon.status     = BoyashJarayon.Status.BOYALMOQDA
                jarayon.updated_by = request.user
                jarayon.save()

            messages.success(request, "Log muvaffaqiyatli qo'shildi.")
        else:
            messages.error(request, 'Xato: ' + str(form.errors))

        return redirect('boyash:jarayon_detail', pk=pk)


class BoyashLogDeleteView(BoyashManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(BoyashJarayonLog, pk=log_pk, jarayon_id=pk)
        log.delete()
        messages.success(request, "Log o'chirildi.")
        return redirect('boyash:jarayon_detail', pk=pk)


# ── Vishilkalar CRUD ──

class BoyashVishilkaListView(BoyashManagerRequiredMixin, ListView):
    model               = BoyashVishilka
    template_name       = 'boyash/vishilka_list.html'
    context_object_name = 'vishilkalar'

    def get_queryset(self):
        return BoyashVishilka.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'vishilkalar'
        ctx['counts'] = {
            'jami': BoyashVishilka.objects.count(),
            'faol': BoyashVishilka.objects.filter(is_active=True).count(),
        }
        return ctx


class BoyashVishilkaCreateView(BoyashManagerRequiredMixin, CreateView):
    model         = BoyashVishilka
    form_class    = BoyashVishilkaForm
    template_name = 'boyash/vishilka_form.html'
    success_url   = reverse_lazy('boyash:vishilka_list')

    def form_valid(self, form):
        messages.success(self.request, "Vishilka qo'shildi.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'vishilkalar'
        ctx['title']      = 'Yangi vishilka'
        return ctx


class BoyashVishilkaUpdateView(BoyashManagerRequiredMixin, UpdateView):
    model         = BoyashVishilka
    form_class    = BoyashVishilkaForm
    template_name = 'boyash/vishilka_form.html'
    success_url   = reverse_lazy('boyash:vishilka_list')

    def form_valid(self, form):
        messages.success(self.request, 'Vishilka yangilandi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'vishilkalar'
        ctx['title']      = 'Vishilkani tahrirlash'
        return ctx


class BoyashVishilkaDeleteView(BoyashManagerRequiredMixin, View):
    def post(self, request, pk):
        vishilka = get_object_or_404(BoyashVishilka, pk=pk)
        vishilka.delete()
        messages.success(request, "Vishilka o'chirildi.")
        return redirect('boyash:vishilka_list')


# ── Statistika ──

class BoyashStatsView(BoyashManagerRequiredMixin, View):
    def get(self, request):
        today     = timezone.now().date()
        days      = int(request.GET.get('days', 14))
        date_from = today - datetime.timedelta(days=days - 1)

        loglar = BoyashJarayonLog.objects.filter(
            sana__gte=date_from, sana__lte=today
        ).select_related('created_by', 'vishilka', 'jarayon__order')

        kun_loglar = loglar.filter(smena='kun')
        tun_loglar = loglar.filter(smena='tun')

        kun_vishilka = sum(l.vishilka_soni for l in kun_loglar)
        tun_vishilka = sum(l.vishilka_soni for l in tun_loglar)
        kun_par      = sum(l.boyalgan_par for l in kun_loglar)
        tun_par      = sum(l.boyalgan_par for l in tun_loglar)
        umumiy_vishilka = kun_vishilka + tun_vishilka
        umumiy_par      = kun_par + tun_par

        date_range   = [date_from + datetime.timedelta(days=i) for i in range(days)]
        chart_labels = [d.strftime('%d.%m') for d in date_range]
        kun_by_day   = [sum(l.boyalgan_par for l in kun_loglar if l.sana == d) for d in date_range]
        tun_by_day   = [sum(l.boyalgan_par for l in tun_loglar if l.sana == d) for d in date_range]

        status_counts = {s.value: BoyashJarayon.objects.filter(status=s.value).count() for s in BoyashJarayon.Status}

        order_stats = []
        jarayonlar = BoyashJarayon.objects.filter(
            loglar__sana__gte=date_from
        ).distinct().select_related('order', 'order__brujka')
        for j in jarayonlar:
            j_logs = loglar.filter(jarayon=j)
            order_stats.append({
                'jarayon': j,
                'vishilka': sum(l.vishilka_soni for l in j_logs),
                'par':      sum(l.boyalgan_par for l in j_logs),
            })
        order_stats.sort(key=lambda x: x['par'], reverse=True)

        return render(request, 'boyash/stats.html', {
            'active_nav':      'stats',
            'days':            days,
            'date_from':       date_from,
            'today':           today,
            'kun_vishilka':    kun_vishilka,
            'tun_vishilka':    tun_vishilka,
            'kun_par':         kun_par,
            'tun_par':         tun_par,
            'umumiy_vishilka': umumiy_vishilka,
            'umumiy_par':      umumiy_par,
            'chart_labels':    chart_labels,
            'kun_by_day':      kun_by_day,
            'tun_by_day':      tun_by_day,
            'status_counts':   status_counts,
            'order_stats':     order_stats,
        })
