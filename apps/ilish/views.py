import datetime
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.order.models import Order
from apps.users.models import User
from .forms import IlishLogForm, VishilkaForm
from .models import IlishJarayon, Vishilka,IlishJarayonLog


class AttachManagerRequiredMixin(LoginRequiredMixin):
    """CEO va ATTACHMANAGER rollari kirishi mumkin."""
    login_url = reverse_lazy('login')
    ALLOWED_ROLES = {'CEO', 'ATTACHMANAGER'}

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        user = request.user
        role_name = user.role.name if getattr(user, 'role', None) else None
        if not (user.is_superuser or role_name in self.ALLOWED_ROLES):
            messages.error(request, 'Sizda bu sahifaga kirish huquqi yo\'q.')
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


# ── Ilish jarayon listview ──

class IlishJarayonListView(AttachManagerRequiredMixin, View):
    def get(self, request):
        from apps.casting.models import QuyishJarayon
        tab = request.GET.get('tab', 'ilinmoqda')
        q   = request.GET.get('q', '').strip()

        # Quyish holati QUYILMOQDA yoki QUYIB_BOLINDI bo'lgan orderlar uchun
        # IlishJarayon avtomatik yaratish
        quyilgan_orders = Order.objects.filter(
            status__in=[Order.Status.IN_PROCESS, Order.Status.READY],
            quyish_jarayon__status__in=[
                QuyishJarayon.Status.QUYILMOQDA,
                QuyishJarayon.Status.QUYIB_BOLINDI,
            ],
        )
        for order in quyilgan_orders:
            IlishJarayon.objects.get_or_create(
                order=order,
                defaults={'created_by': request.user},
            )
        # READY statusli orderlar ham
        for order in Order.objects.filter(status=Order.Status.READY):
            IlishJarayon.objects.get_or_create(
                order=order,
                defaults={'created_by': request.user},
            )

        qs = IlishJarayon.objects.select_related(
            'order', 'order__brujka', 'updated_by', 'order__quyish_jarayon',
        )
        if q:
            qs = qs.filter(
                Q(order__name__icontains=q) |
                Q(order__order_number__icontains=q)
            )

        valid_tabs = {s.value for s in IlishJarayon.Status}
        if tab not in valid_tabs:
            tab = 'ilinmoqda'

        jarayonlar = qs.filter(status=tab)

        counts = {}
        for s in IlishJarayon.Status:
            counts[s.value] = qs.filter(status=s.value).count()

        hodimlar  = User.objects.all().order_by('name')
        vishilkalar = Vishilka.objects.filter(is_active=True).order_by('quantity', 'nomi')

        return render(request, 'ilish/jarayon_list.html', {
            'active_nav': 'jarayonlar',
            'tab':        tab,
            'q':          q,
            'jarayonlar': jarayonlar,
            'counts':     counts,
            'hodimlar':   hodimlar,
            'vishilkalar': vishilkalar,
            'today':      timezone.now().date().isoformat(),
        })


class IlishJarayonDetailView(AttachManagerRequiredMixin, View):
    def get(self, request, pk):
        jarayon = get_object_or_404(
            IlishJarayon.objects.select_related('order', 'order__brujka'),
            pk=pk,
        )
        loglar = jarayon.loglar.select_related('hodim', 'vishilka').order_by('-sana', '-created_at')

        loglar_list   = list(loglar)
        kun_loglar    = [l for l in loglar_list if l.smena == 'kun']
        tun_loglar    = [l for l in loglar_list if l.smena == 'tun']

        kun_par       = sum(l.ilingan_par for l in kun_loglar)
        tun_par       = sum(l.ilingan_par for l in tun_loglar)
        kun_broshka   = sum(l.ilingan_broshka for l in kun_loglar)
        tun_broshka   = sum(l.ilingan_broshka for l in tun_loglar)
        total_par     = kun_par + tun_par
        total_broshka = kun_broshka + tun_broshka

        # Progress: maqsad = order.quantity (broshka), 1 broshka = 1 dona
        target_broshka = jarayon.order.quantity
        qoldiq_broshka = max(0, target_broshka - total_broshka)
        progress_pct   = min(100, round(total_broshka / target_broshka * 100)) if target_broshka else 0

        form = IlishLogForm(initial={'sana': timezone.now().date()})

        return render(request, 'ilish/jarayon_detail.html', {
            'active_nav':      'jarayonlar',
            'jarayon':         jarayon,
            'loglar':          loglar_list,
            'form':            form,
            'total_par':       total_par,
            'total_broshka':   total_broshka,
            'kun_par':         kun_par,
            'tun_par':         tun_par,
            'kun_broshka':     kun_broshka,
            'tun_broshka':     tun_broshka,
            'kun_count':       len(kun_loglar),
            'tun_count':       len(tun_loglar),
            'target_broshka':  target_broshka,
            'qoldiq_broshka':  qoldiq_broshka,
            'progress_pct':    progress_pct,
        })


class IlishJarayonSetStatusView(AttachManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon  = get_object_or_404(IlishJarayon, pk=pk)
        status   = request.POST.get('status', '').strip()
        izoh     = request.POST.get('izoh', '').strip()
        next_tab = request.POST.get('next_tab', 'ilinmoqda')

        valid = {s.value for s in IlishJarayon.Status}
        if status in valid:
            jarayon.status     = status
            jarayon.izoh       = izoh
            jarayon.updated_by = request.user
            jarayon.save()
            messages.success(request, f'Holat: {jarayon.get_status_display()}')
        else:
            messages.error(request, 'Noto\'g\'ri holat.')

        return redirect(f'{reverse_lazy("ilish:jarayon_list")}?tab={next_tab}')


# ── Log create / delete ──

class IlishLogCreateView(AttachManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(IlishJarayon, pk=pk)
        form    = IlishLogForm(request.POST)
        if form.is_valid():
            log             = form.save(commit=False)
            log.jarayon     = jarayon
            log.created_by  = request.user
            log.save()

            # Agar holat hali QABUL_QILINDI bo'lsa, ILINMOQDA ga o'tkazish
            if jarayon.status == IlishJarayon.Status.QABUL_QILINDI:
                jarayon.status     = IlishJarayon.Status.ILINMOQDA
                jarayon.updated_by = request.user
                jarayon.save()

            messages.success(request, 'Log muvaffaqiyatli qo\'shildi.')
        else:
            messages.error(request, 'Xato: ' + str(form.errors))

        return redirect('ilish:jarayon_detail', pk=pk)


class IlishLogDeleteView(AttachManagerRequiredMixin, View):
    def post(self, request, pk, log_pk):
        log = get_object_or_404(IlishJarayonLog, pk=log_pk, jarayon_id=pk)
        log.delete()
        messages.success(request, 'Log o\'chirildi.')
        return redirect('ilish:jarayon_detail', pk=pk)


class BulkLogCreateView(AttachManagerRequiredMixin, View):
    """Bir necha hodim uchun bir vaqtda log kiritish."""
    def post(self, request, pk):
        jarayon       = get_object_or_404(IlishJarayon, pk=pk)
        sana_str      = request.POST.get('sana', timezone.now().date().isoformat())
        smena         = request.POST.get('smena', 'kun')
        vishilka_id   = request.POST.get('vishilka', '')
        izoh          = request.POST.get('izoh', '').strip()

        try:
            sana = datetime.date.fromisoformat(sana_str)
        except ValueError:
            sana = timezone.now().date()

        vishilka = None
        if vishilka_id:
            try:
                vishilka = Vishilka.objects.get(pk=vishilka_id, is_active=True)
            except Vishilka.DoesNotExist:
                pass

        hodim_ids   = request.POST.getlist('hodim_ids')
        vishilka_sonlar = request.POST.getlist('vishilka_sonlar')

        saved = 0
        for i, hodim_id in enumerate(hodim_ids):
            if not hodim_id:
                continue
            try:
                soni = int(vishilka_sonlar[i]) if i < len(vishilka_sonlar) else 1
            except (ValueError, TypeError):
                soni = 1
            if soni < 1:
                continue
            try:
                hodim = User.objects.get(pk=hodim_id)
            except User.DoesNotExist:
                continue
            IlishJarayonLog.objects.create(
                jarayon=jarayon,
                hodim=hodim,
                smena=smena,
                vishilka=vishilka,
                vishilka_soni=soni,
                sana=sana,
                izoh=izoh,
                created_by=request.user,
            )
            saved += 1

        if saved:
            if jarayon.status == IlishJarayon.Status.QABUL_QILINDI:
                jarayon.status     = IlishJarayon.Status.ILINMOQDA
                jarayon.updated_by = request.user
                jarayon.save()
            messages.success(request, f'{saved} ta hodim uchun log saqlandi.')
        else:
            messages.error(request, 'Hech qanday log saqlanmadi. Hodim va vishilka soni kiriting.')

        return redirect('ilish:jarayon_detail', pk=pk)


# ── Vishilkalar CRUD ──

class VishilkaListView(AttachManagerRequiredMixin, ListView):
    model               = Vishilka
    template_name       = 'ilish/vishilka_list.html'
    context_object_name = 'vishilkalar'

    def get_queryset(self):
        return Vishilka.objects.all()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'vishilkalar'
        ctx['counts'] = {
            'jami': Vishilka.objects.count(),
            'faol': Vishilka.objects.filter(is_active=True).count(),
        }
        return ctx


class VishilkaCreateView(AttachManagerRequiredMixin, CreateView):
    model         = Vishilka
    form_class    = VishilkaForm
    template_name = 'ilish/vishilka_form.html'
    success_url   = reverse_lazy('ilish:vishilka_list')

    def form_valid(self, form):
        messages.success(self.request, 'Vishilka qo\'shildi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'vishilkalar'
        ctx['title']      = 'Yangi vishilka'
        return ctx


class VishilkaUpdateView(AttachManagerRequiredMixin, UpdateView):
    model         = Vishilka
    form_class    = VishilkaForm
    template_name = 'ilish/vishilka_form.html'
    success_url   = reverse_lazy('ilish:vishilka_list')

    def form_valid(self, form):
        messages.success(self.request, 'Vishilka yangilandi.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_nav'] = 'vishilkalar'
        ctx['title']      = 'Vishilkani tahrirlash'
        return ctx


class VishilkaDeleteView(AttachManagerRequiredMixin, View):
    def post(self, request, pk):
        vishilka = get_object_or_404(Vishilka, pk=pk)
        vishilka.delete()
        messages.success(request, 'Vishilka o\'chirildi.')
        return redirect('ilish:vishilka_list')


# ── Statistika ──

class IlishStatsView(AttachManagerRequiredMixin, View):
    def get(self, request):
        today    = timezone.now().date()
        days     = int(request.GET.get('days', 14))
        date_from = today - datetime.timedelta(days=days - 1)

        loglar = IlishJarayonLog.objects.filter(
            sana__gte=date_from, sana__lte=today
        ).select_related('hodim', 'vishilka', 'jarayon__order')

        # Kun / tun breakdown
        kun_loglar = loglar.filter(smena='kun')
        tun_loglar = loglar.filter(smena='tun')

        def calc_totals(qs):
            total_par     = sum(l.ilingan_par for l in qs)
            total_broshka = sum(l.ilingan_broshka for l in qs)
            return total_par, total_broshka

        kun_par, kun_broshka = calc_totals(kun_loglar)
        tun_par, tun_broshka = calc_totals(tun_loglar)
        umumiy_par           = kun_par + tun_par
        umumiy_broshka       = kun_broshka + tun_broshka

        # Daily chart data
        date_range = [date_from + datetime.timedelta(days=i) for i in range(days)]
        chart_labels = [d.strftime('%d.%m') for d in date_range]

        kun_by_day = []
        tun_by_day = []
        for d in date_range:
            day_kun = [l for l in kun_loglar if l.sana == d]
            day_tun = [l for l in tun_loglar if l.sana == d]
            kun_by_day.append(sum(l.ilingan_broshka for l in day_kun))
            tun_by_day.append(sum(l.ilingan_broshka for l in day_tun))

        # Status counts
        status_counts = {}
        for s in IlishJarayon.Status:
            status_counts[s.value] = IlishJarayon.objects.filter(status=s.value).count()

        # Hodim bo'yicha statistika
        hodim_stats = []
        hodimlar = User.objects.filter(ilish_loglar__sana__gte=date_from).distinct()
        for hodim in hodimlar:
            h_logs      = loglar.filter(hodim=hodim)
            h_par       = sum(l.ilingan_par for l in h_logs)
            h_broshka   = sum(l.ilingan_broshka for l in h_logs)
            h_kun_par   = sum(l.ilingan_par for l in h_logs if l.smena == 'kun')
            h_tun_par   = sum(l.ilingan_par for l in h_logs if l.smena == 'tun')
            hodim_stats.append({
                'hodim':    hodim,
                'par':      h_par,
                'broshka':  h_broshka,
                'kun_par':  h_kun_par,
                'tun_par':  h_tun_par,
            })
        hodim_stats.sort(key=lambda x: x['broshka'], reverse=True)

        return render(request, 'ilish/stats.html', {
            'active_nav':    'stats',
            'days':          days,
            'date_from':     date_from,
            'today':         today,
            'kun_par':       kun_par,
            'kun_broshka':   kun_broshka,
            'tun_par':       tun_par,
            'tun_broshka':   tun_broshka,
            'umumiy_par':    umumiy_par,
            'umumiy_broshka': umumiy_broshka,
            'chart_labels':  chart_labels,
            'kun_by_day':    kun_by_day,
            'tun_by_day':    tun_by_day,
            'status_counts': status_counts,
            'hodim_stats':   hodim_stats,
        })
