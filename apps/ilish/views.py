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
from .forms import IlishLogForm, VishilkaForm, QadoqlashLogForm
from .models import IlishJarayon, Vishilka, IlishJarayonLog, QadoqlashJarayon, QadoqlashLog


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

        # Quyib_bolindi yoki quyilmoqda statusli orderlar uchun IlishJarayon avtomatik yaratish
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


# ─────────────────────────────────────────────
# Upakovka (Qadoqlash) jarayonlari
# ─────────────────────────────────────────────
class UpakovkaListView(AttachManagerRequiredMixin, View):
    def get(self, request):
        today = timezone.now().date()
        tab = request.GET.get('tab', 'qabul_qilindi')
        q   = request.GET.get('q', '').strip()

        # ilib_bolindi statusli IlishJarayon lar uchun avtomatik QadoqlashJarayon yaratish
        # Model: QadoqlashJarayon.order = OneToOneField('order.Order')
        # Shuning uchun ilish_jarayon orqali emas, order orqali bog'laymiz
        ilinib_jarayonlar = IlishJarayon.objects.filter(
            status=IlishJarayon.Status.ILIB_BOLINDI
        )
        for ij in ilinib_jarayonlar:
            QadoqlashJarayon.objects.get_or_create(
                order=ij.order,
                defaults={'created_by': request.user},
            )

        qs = QadoqlashJarayon.objects.select_related(
            'order',
            'order__brujka',
            'updated_by',
        ).order_by('-order__deadline', '-updated_at')

        if q:
            qs = qs.filter(
                Q(order__name__icontains=q) |
                Q(order__order_number__icontains=q)
            )

        valid_tabs = {s.value for s in QadoqlashJarayon.Status}
        if tab not in valid_tabs:
            tab = QadoqlashJarayon.Status.QABUL_QILINDI.value

        jarayonlar = qs.filter(status=tab)
        counts     = {s.value: qs.filter(status=s.value).count() for s in QadoqlashJarayon.Status}

        # Bugungi kun/tun mini statistika
        # QadoqlashLog modelida: smena, par_soni, sana fieldlari mavjud
        bugungi_loglar = QadoqlashLog.objects.filter(sana=today)
        bugun_kun_par  = bugungi_loglar.filter(smena=QadoqlashLog.Smena.KUN).aggregate(
            total=models.Sum('par_soni')
        )['total'] or 0
        bugun_tun_par  = bugungi_loglar.filter(smena=QadoqlashLog.Smena.TUN).aggregate(
            total=models.Sum('par_soni')
        )['total'] or 0

        return render(request, 'ilish/upakovka_list.html', {
            'active_nav':    'upakovka',
            'tab':           tab,
            'q':             q,
            'jarayonlar':    jarayonlar,
            'counts':        counts,
            'bugun_kun_par': bugun_kun_par,
            'bugun_tun_par': bugun_tun_par,
            'today':         today.isoformat(),
        })


class UpakovkaSetStatusView(AttachManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon  = get_object_or_404(QadoqlashJarayon, pk=pk)
        status   = request.POST.get('status', '').strip()
        izoh     = request.POST.get('izoh', '').strip()
        next_tab = request.POST.get('next_tab', QadoqlashJarayon.Status.QABUL_QILINDI.value)

        valid = {s.value for s in QadoqlashJarayon.Status}
        if status in valid:
            jarayon.status     = status
            jarayon.izoh       = izoh
            jarayon.updated_by = request.user
            jarayon.save()
            messages.success(request, 'Upakovka holati yangilandi.')
        else:
            messages.error(request, "Noto'g'ri holat.")
        return redirect(f'{reverse_lazy("ilish:upakovka_list")}?tab={next_tab}')


class UpakovkaLogCreateView(AttachManagerRequiredMixin, View):
    def post(self, request, pk):
        jarayon = get_object_or_404(QadoqlashJarayon, pk=pk)
        form = QadoqlashLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.jarayon    = jarayon
            log.created_by = request.user
            log.save()

            # Agar jarayon hali qabul_qilindi bo'lsa — qadoqlanmoqda ga o'tkazamiz
            if jarayon.status == QadoqlashJarayon.Status.QABUL_QILINDI:
                jarayon.status     = QadoqlashJarayon.Status.QADOQLANMOQDA
                jarayon.updated_by = request.user
                jarayon.save()

            messages.success(request, f'{log.par_soni} par qadoqlash logi saqlandi.')
        else:
            messages.error(request, f'Xato: {form.errors}')

        return redirect('ilish:upakovka_detail', pk=pk)


class UpakovkaLogDeleteView(AttachManagerRequiredMixin, View):
    def post(self, request, log_pk):
        log = get_object_or_404(QadoqlashLog, pk=log_pk)
        jarayon_pk = log.jarayon_id  # ForeignKey → jarayon_id mavjud
        log.delete()
        messages.success(request, "Log o'chirildi.")
        return redirect('ilish:upakovka_detail', pk=jarayon_pk)


class UpakovkaLogUpdateView(AttachManagerRequiredMixin, View):
    def get(self, request, log_pk):
        log = get_object_or_404(
            QadoqlashLog.objects.select_related(
                'jarayon__order',          # QadoqlashJarayon → order
                'jarayon__order__brujka',
            ),
            pk=log_pk,
        )
        form = QadoqlashLogForm(instance=log)
        return render(request, 'ilish/upakovka_log_form.html', {
            'active_nav': 'upakovka',
            'form':       form,
            'log':        log,
            'jarayon':    log.jarayon,
        })

    def post(self, request, log_pk):
        log  = get_object_or_404(QadoqlashLog, pk=log_pk)
        form = QadoqlashLogForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, 'Log yangilandi.')
            return redirect('ilish:upakovka_detail', pk=log.jarayon_id)
        messages.error(request, f'Xato: {form.errors}')
        return render(request, 'ilish/upakovka_log_form.html', {
            'active_nav': 'upakovka',
            'form':       form,
            'log':        log,
            'jarayon':    log.jarayon,
        })


class UpakovkaDetailView(AttachManagerRequiredMixin, View):
    def get(self, request, pk):
        jarayon = get_object_or_404(
            QadoqlashJarayon.objects.select_related(
                'order',
                'order__brujka',
                'created_by',
                'updated_by',
            ),
            pk=pk,
        )

        # QadoqlashLog: jarayon (FK), smena, par_soni, sana, created_by
        loglar      = (
            QadoqlashLog.objects
            .filter(jarayon=jarayon)
            .select_related('created_by')
            .order_by('-sana', '-created_at')
        )
        loglar_list = list(loglar)

        kun_loglar = [l for l in loglar_list if l.smena == QadoqlashLog.Smena.KUN]
        tun_loglar = [l for l in loglar_list if l.smena == QadoqlashLog.Smena.TUN]
        kun_par    = sum(l.par_soni for l in kun_loglar)
        tun_par    = sum(l.par_soni for l in tun_loglar)
        total_par  = kun_par + tun_par

        # order.quantity — Order modelidagi field
        target_par   = jarayon.order.quantity if jarayon.order else 0
        progress_pct = min(100, round(total_par / target_par * 100)) if target_par else 0
        qoldiq_par   = max(0, target_par - total_par)

        form = QadoqlashLogForm(initial={'sana': timezone.now().date()})

        return render(request, 'ilish/upakovka_detail.html', {
            'active_nav':   'upakovka',
            'jarayon':      jarayon,
            'loglar':       loglar_list,
            'kun_par':      kun_par,
            'tun_par':      tun_par,
            'total_par':    total_par,
            'target_par':   target_par,
            'progress_pct': progress_pct,
            'qoldiq_par':   qoldiq_par,
            'today':        timezone.now().date().isoformat(),
            'form':         form,
        })


class UpakovkaStatsView(AttachManagerRequiredMixin, View):
    def get(self, request):
        today     = timezone.now().date()
        days      = int(request.GET.get('days', 14))
        date_from = today - datetime.timedelta(days=days - 1)

        # QadoqlashLog → jarayon → order → brujka
        loglar = (
            QadoqlashLog.objects
            .filter(sana__gte=date_from, sana__lte=today)
            .select_related('jarayon__order__brujka')
        )
        all_loglar = list(loglar)

        # aggregate DB-da hisoblash (samaraliroq)
        agg = QadoqlashLog.objects.filter(
            sana__gte=date_from, sana__lte=today
        ).aggregate(
            kun_par=models.Sum('par_soni', filter=Q(smena=QadoqlashLog.Smena.KUN)),
            tun_par=models.Sum('par_soni', filter=Q(smena=QadoqlashLog.Smena.TUN)),
        )
        kun_par    = agg['kun_par'] or 0
        tun_par    = agg['tun_par'] or 0
        umumiy_par = kun_par + tun_par

        date_range   = [date_from + datetime.timedelta(days=i) for i in range(days)]
        chart_labels = [d.strftime('%d.%m') for d in date_range]
        kun_by_day   = [
            sum(l.par_soni for l in all_loglar if l.sana == d and l.smena == QadoqlashLog.Smena.KUN)
            for d in date_range
        ]
        tun_by_day   = [
            sum(l.par_soni for l in all_loglar if l.sana == d and l.smena == QadoqlashLog.Smena.TUN)
            for d in date_range
        ]

        status_counts = {
            s.value: QadoqlashJarayon.objects.filter(status=s.value).count()
            for s in QadoqlashJarayon.Status
        }

        daily_totals = [k + t for k, t in zip(kun_by_day, tun_by_day)]
        max_day_val  = max(daily_totals) if daily_totals else 0
        max_day_idx  = daily_totals.index(max_day_val) if max_day_val else 0
        max_day_lbl  = chart_labels[max_day_idx] if chart_labels else '—'

        # Brujka bo'yicha breakdown — order.brujka orqali
        brujka_stats: dict = {}
        for l in all_loglar:
            if l.jarayon.order:
                brujka = l.jarayon.order.brujka
                key    = brujka.name if brujka else 'Brujkasiz'
            else:
                key = 'Brujkasiz'
            brujka_stats[key] = brujka_stats.get(key, 0) + l.par_soni
        brujka_stats = sorted(brujka_stats.items(), key=lambda x: x[1], reverse=True)

        # Bugungi ma'lumot
        bugun_loglar = [l for l in all_loglar if l.sana == today]
        bugun_kun    = sum(l.par_soni for l in bugun_loglar if l.smena == QadoqlashLog.Smena.KUN)
        bugun_tun    = sum(l.par_soni for l in bugun_loglar if l.smena == QadoqlashLog.Smena.TUN)

        return render(request, 'ilish/upakovka_stats.html', {
            'active_nav':    'upakovka_stats',
            'days':          days,
            'date_from':     date_from,
            'today':         today,
            'kun_par':       kun_par,
            'tun_par':       tun_par,
            'umumiy_par':    umumiy_par,
            'bugun_kun':     bugun_kun,
            'bugun_tun':     bugun_tun,
            'chart_labels':  chart_labels,
            'kun_by_day':    kun_by_day,
            'tun_by_day':    tun_by_day,
            'status_counts': status_counts,
            'max_day_val':   max_day_val,
            'max_day_lbl':   max_day_lbl,
            'brujka_stats':  brujka_stats,
        })